import { NextRequest, NextResponse } from 'next/server';

// Backend URL configuration with fallback
const BACKEND_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'https://api.starmates.ai/api';

// Allowed origins for CORS (including localhost for development)
const ALLOWED_ORIGINS = [
  'http://localhost:3000',
  'http://localhost:5554',
  'http://localhost:5555',
  'https://your-production-domain.com' // Add your production domain here
];

// Headers to exclude from forwarding to backend
const EXCLUDED_HEADERS = [
  'host',
  'connection',
  'upgrade',
  'sec-websocket-key',
  'sec-websocket-version',
  'sec-websocket-extensions',
];

// Helper function to get CORS headers
function getCorsHeaders(origin: string | null): Record<string, string> {
  const corsHeaders: Record<string, string> = {
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin, Cache-Control, Pragma',
    'Access-Control-Max-Age': '86400', // 24 hours
  };

  if (origin && (ALLOWED_ORIGINS.includes(origin) || origin.startsWith('http://localhost'))) {
    corsHeaders['Access-Control-Allow-Origin'] = origin;
    corsHeaders['Access-Control-Allow-Credentials'] = 'true';
  }

  return corsHeaders;
}

// Handle OPTIONS requests for CORS preflight
export async function OPTIONS(request: NextRequest) {
  const origin = request.headers.get('origin');
  const corsHeaders = getCorsHeaders(origin);

  return new NextResponse(null, {
    status: 200,
    headers: corsHeaders,
  });
}

// Generic handler for all HTTP methods
async function proxyHandler(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  try {
    const resolvedParams = await params;
    const path = resolvedParams.path.join('/');

    // Ensure the backend URL ends with /api and path doesn't have duplicate slashes
    let cleanBackendUrl = BACKEND_URL;
    if (!cleanBackendUrl.endsWith('/api')) {
      cleanBackendUrl = cleanBackendUrl.replace(/\/+$/, '') + '/api';
    }

    const url = `${cleanBackendUrl}/${path}${request.nextUrl.search}`;

    console.log(`[API Proxy] ${request.method} ${path} -> ${url}`);
    console.log(`[API Proxy] Clean backend URL: ${cleanBackendUrl}`);
    console.log(`[API Proxy] Original backend URL: ${BACKEND_URL}`);

    // Prepare headers for backend request
    const headers = new Headers();

    // Copy relevant headers from the original request
    request.headers.forEach((value, key) => {
      if (!EXCLUDED_HEADERS.includes(key.toLowerCase())) {
        headers.set(key, value);
      }
    });

    // Ensure we have the correct content type for JSON requests
    if (!headers.get('content-type') && request.method !== 'GET') {
      headers.set('Content-Type', 'application/json');
    }

    // Debug: Check if Authorization header is present
    const authHeader = headers.get('authorization');
    console.log(`[API Proxy] Authorization header present: ${!!authHeader}`);
    if (authHeader) {
      console.log(`[API Proxy] Authorization header: ${authHeader.substring(0, 20)}...`);

      // Try to decode JWT token for debugging
      if (authHeader.startsWith('Bearer ')) {
        const token = authHeader.substring(7);
        try {
          // Decode JWT token (just the payload, not verifying signature)
          const parts = token.split('.');
          if (parts.length === 3) {
            // Convert base64url to base64 by replacing URL-safe characters
            let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
            // Add padding if needed
            while (base64.length % 4) {
              base64 += '=';
            }
            const payload = JSON.parse(atob(base64));
            console.log(`[API Proxy] JWT payload:`, {
              sub: payload.sub,
              email: payload.email,
              aud: payload.aud,
              iss: payload.iss,
              exp: payload.exp,
              iat: payload.iat,
              role: payload.role
            });
          }
        } catch (e) {
          console.log(`[API Proxy] Failed to decode JWT:`, e instanceof Error ? e.message : e);
        }
      }
    }

    // Prepare request body
    let body = null;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      try {
        body = await request.text();
      } catch (error) {
        console.warn('[API Proxy] Failed to read request body:', error);
      }
    }

    // Make the backend request with manual redirect handling to preserve Authorization header
    const response = await fetch(url, {
      method: request.method,
      headers,
      body,
      redirect: 'manual', // Handle redirects manually to preserve headers
    });

    // Handle redirects manually to preserve Authorization header
    if (response.status === 307 || response.status === 308) {
      let redirectUrl = response.headers.get('location');
      if (redirectUrl) {
        // Ensure redirect URL uses HTTPS if the original URL was HTTPS
        if (url.startsWith('https://') && redirectUrl.startsWith('http://')) {
          redirectUrl = redirectUrl.replace('http://', 'https://');
          console.log(`[API Proxy] Corrected redirect URL protocol to HTTPS: ${redirectUrl}`);
        }

        console.log(`[API Proxy] Handling ${response.status} redirect to: ${redirectUrl}`);
        // Make a new request to the redirect URL with the same headers
        const redirectResponse = await fetch(redirectUrl, {
          method: request.method,
          headers, // Preserve all original headers including Authorization
          body,
        });

        console.log(`[API Proxy] Redirect response status: ${redirectResponse.status}`);
        console.log(`[API Proxy] Redirect response URL: ${redirectResponse.url}`);

        // Prepare response headers for redirect response
        const redirectResponseHeaders = new Headers();

        // Copy response headers from backend
        redirectResponse.headers.forEach((value, key) => {
          // Skip CORS headers as we'll set our own
          if (!key.toLowerCase().startsWith('access-control-')) {
            redirectResponseHeaders.set(key, value);
          }
        });

        // Add CORS headers
        const origin = request.headers.get('origin');
        const corsHeaders = getCorsHeaders(origin);
        Object.entries(corsHeaders).forEach(([key, value]) => {
          redirectResponseHeaders.set(key, value);
        });

        // Get response body
        const redirectResponseBody = await redirectResponse.arrayBuffer();

        console.log(`[API Proxy] Redirect Response: ${redirectResponse.status} ${redirectResponse.statusText}`);

        return new NextResponse(redirectResponseBody, {
          status: redirectResponse.status,
          statusText: redirectResponse.statusText,
          headers: redirectResponseHeaders,
        });
      }
    }

    console.log(`[API Proxy] Backend response status: ${response.status}`);
    console.log(`[API Proxy] Backend response URL: ${response.url}`);

    // Prepare response headers
    const responseHeaders = new Headers();

    // Copy response headers from backend
    response.headers.forEach((value, key) => {
      // Skip CORS headers as we'll set our own
      if (!key.toLowerCase().startsWith('access-control-')) {
        responseHeaders.set(key, value);
      }
    });

    // Add CORS headers
    const origin = request.headers.get('origin');
    const corsHeaders = getCorsHeaders(origin);
    Object.entries(corsHeaders).forEach(([key, value]) => {
      responseHeaders.set(key, value);
    });

    // Get response body
    const responseBody = await response.arrayBuffer();

    // Log response status
    console.log(`[API Proxy] Response: ${response.status} ${response.statusText}`);

    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });

  } catch (error) {
    console.error('[API Proxy] Error:', error);

    const origin = request.headers.get('origin');
    const corsHeaders = getCorsHeaders(origin);

    return new NextResponse(
      JSON.stringify({
        error: 'Proxy request failed',
        message: error instanceof Error ? error.message : 'Unknown error'
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders,
        },
      }
    );
  }
}

// Export handlers for all HTTP methods
export const GET = proxyHandler;
export const POST = proxyHandler;
export const PUT = proxyHandler;
export const DELETE = proxyHandler;
export const PATCH = proxyHandler;
