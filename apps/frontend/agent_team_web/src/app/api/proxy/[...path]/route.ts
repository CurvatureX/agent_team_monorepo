import { NextRequest, NextResponse } from 'next/server';

// Use environment variable for backend URL
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://agent-prod-alb-352817645.us-east-1.elb.amazonaws.com/api';

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  const path = resolvedParams.path.join('/');
  const url = `${BACKEND_URL}/${path}${request.nextUrl.search}`;
  
  console.log('Proxying request to:', url);
  
  try {
    const headers = new Headers();
    
    // Forward important headers
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
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
    
    const response = await fetch(url, {
      method: request.method,
      headers,
      body,
      // Important: don't follow redirects automatically
      redirect: 'manual',
    });
    
    console.log('Backend response status:', response.status);
    
    // Handle redirects on the server side
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get('location');
      console.log('Backend redirect to:', location);
      
      if (location) {
        // If it's redirecting to the full backend URL, follow it server-side
        if (location.startsWith('http')) {
          const redirectResponse = await fetch(location, {
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
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from backend', details: String(error) },
      { status: 500 }
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