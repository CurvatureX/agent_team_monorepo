import { NextRequest, NextResponse } from 'next/server';

// Use environment variable for backend URL
const BACKEND_URL = process.env.BACKEND_API_URL || 'https://api.starmates.ai/api';

// Configure timeouts and retry settings
const FETCH_TIMEOUT_MS = 30000; // 30 seconds
const RETRY_ATTEMPTS = 2; // Retry transient failures
const RETRY_DELAY_MS = 500; // Wait 500ms between retries

// Helper function to create fetch with timeout
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = FETCH_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      // Add keepalive for connection reuse
      keepalive: true,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

// Helper function to check if error is retryable
function isRetryableError(error: unknown): boolean {
  const errorStr = String(error);
  return (
    errorStr.includes('ECONNREFUSED') ||
    errorStr.includes('ETIMEDOUT') ||
    errorStr.includes('ECONNRESET') ||
    errorStr.includes('fetch failed') ||
    errorStr.includes('aborted')
  );
}

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  const path = resolvedParams.path.join('/');
  const url = `${BACKEND_URL}/${path}${request.nextUrl.search}`;

  console.log(`[Proxy] ${request.method} ${url}`);

  try {
    const headers = new Headers();

    // Forward important headers (check both cases)
    const authHeader = request.headers.get('authorization') || request.headers.get('Authorization');

    if (authHeader) {
      // Ensure proper capitalization for backend
      headers.set('Authorization', authHeader);
    }
    headers.set('Content-Type', 'application/json');
    headers.set('Accept', 'application/json');

    // Get request body if present
    let body: string | undefined = undefined;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      try {
        body = await request.text();
      } catch {
        // No body
      }
    }

    // Retry logic for transient failures
    let lastError: unknown = null;
    let response: Response | null = null;

    for (let attempt = 0; attempt <= RETRY_ATTEMPTS; attempt++) {
      try {
        response = await fetchWithTimeout(url, {
          method: request.method,
          headers,
          body,
          // Important: don't follow redirects automatically
          redirect: 'manual',
        });

        // Success - break out of retry loop
        lastError = null;
        break;
      } catch (error) {
        lastError = error;

        // Don't retry if this is the last attempt
        if (attempt >= RETRY_ATTEMPTS) {
          break;
        }

        // Only retry transient network errors
        if (isRetryableError(error)) {
          console.warn(`[Proxy] Attempt ${attempt + 1}/${RETRY_ATTEMPTS + 1} failed: ${error}. Retrying...`);
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS * (attempt + 1)));
        } else {
          // Non-retryable error, fail immediately
          break;
        }
      }
    }

    // If all retries failed, throw the last error
    if (!response || lastError) {
      throw new Error(`Backend request failed after ${RETRY_ATTEMPTS + 1} attempts: ${lastError}`);
    }

    console.log('Backend response status:', response.status);

    // Log error details for authentication failures
    if (response.status === 401 || response.status === 403) {
      const errorText = await response.text();
      console.error('Authentication error from backend:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText.substring(0, 200),
        sentAuth: headers.get('Authorization') ? 'Yes' : 'No'
      });
      return NextResponse.json(
        JSON.parse(errorText),
        { status: response.status }
      );
    }

    // Handle redirects on the server side
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get('location');
      console.log('Backend redirect to:', location);

      if (location) {
        // If it's redirecting to the full backend URL, follow it server-side
        if (location.startsWith('http')) {
          // Keep HTTP for localhost, only force HTTPS for production
          const secureLocation = location.includes('localhost')
            ? location
            : location.replace(/^http:\/\//, 'https://');
          console.log('Following redirect to:', secureLocation);
          console.log('Redirect auth present:', headers.get('Authorization') ? 'Yes' : 'No');

          const redirectResponse = await fetchWithTimeout(secureLocation, {
            method: request.method,
            headers,
            body,
          });

          const data = await redirectResponse.text();
          const contentType = redirectResponse.headers.get('content-type');

          if (contentType?.includes('application/json')) {
            return NextResponse.json(JSON.parse(data), {
              status: redirectResponse.status
            });
          }

          return new NextResponse(data, {
            status: redirectResponse.status,
            headers: {
              'Content-Type': contentType || 'text/plain',
            }
          });
        }
      }
    }

    // Handle normal response
    const contentType = response.headers.get('content-type');

    // For JSON responses, parse and return
    if (contentType?.includes('application/json')) {
      const data = await response.text();
      const jsonResponse = NextResponse.json(JSON.parse(data), {
        status: response.status
      });

      // Add cache headers for GET requests
      if (request.method === 'GET' && response.status === 200) {
        jsonResponse.headers.set('Cache-Control', 'public, max-age=60, stale-while-revalidate=30');
      }

      return jsonResponse;
    }

    // For non-JSON, stream the response (faster for large responses)
    if (response.body) {
      return new NextResponse(response.body, {
        status: response.status,
        headers: {
          'Content-Type': contentType || 'text/plain',
        }
      });
    }

    // Fallback for responses without body
    const data = await response.text();

    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': contentType || 'text/plain',
      }
    });

  } catch (error) {
    // Enhanced error logging with more context
    const errorDetails = {
      message: String(error),
      type: error instanceof Error ? error.constructor.name : typeof error,
      url,
      method: request.method,
      backendUrl: BACKEND_URL,
      timestamp: new Date().toISOString(),
    };

    console.error('[Proxy] Request failed:', errorDetails);

    // Check if error is due to timeout
    const isTimeout = String(error).includes('aborted') || String(error).includes('timeout');
    const isConnectionRefused = String(error).includes('ECONNREFUSED');

    let userMessage = 'Failed to fetch from backend';
    let statusCode = 500;

    if (isTimeout) {
      userMessage = 'Backend request timed out. The server may be under heavy load.';
      statusCode = 504; // Gateway Timeout
    } else if (isConnectionRefused) {
      userMessage = 'Backend service unavailable. Please try again in a moment.';
      statusCode = 503; // Service Unavailable
    }

    return NextResponse.json(
      {
        error: userMessage,
        details: String(error),
        timestamp: errorDetails.timestamp,
      },
      { status: statusCode }
    );
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handler(request, context);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handler(request, context);
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handler(request, context);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handler(request, context);
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handler(request, context);
}

export async function OPTIONS(_request: NextRequest, _context: { params: Promise<{ path: string[] }> }) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
