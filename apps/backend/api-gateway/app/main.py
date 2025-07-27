"""
API Gateway - Simplified with Frontend Auth
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import init_supabase
from app.models import HealthResponse
from app.api import session, chat, workflow
from app.services.grpc_client import workflow_client
from app.utils import log_info, log_warning, log_error, log_exception


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - replaces deprecated on_event"""
    # Startup
    try:
        log_info("🚀 Starting API Gateway with Frontend Auth...")
        
        # Initialize Supabase connection
        init_supabase()
        log_info("✅ Supabase client initialized")
        
        # Initialize gRPC client connection
        await workflow_client.connect()
        log_info("✅ gRPC client connected")
        
        log_info("🚀 API Gateway started successfully!")
        log_info(f"📖 API Documentation: http://localhost:8000/docs")
        log_info(f"🏥 Health Check: http://localhost:8000/health")
        log_info(f"🔐 Auth: Frontend handles authentication, backend verifies JWT tokens")
        
    except Exception as e:
        log_exception(f"❌ Failed to start API Gateway: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        # Close gRPC connections
        await workflow_client.close()
        
        log_info("👋 API Gateway stopped")
        
    except Exception as e:
        log_exception(f"⚠️  Error during shutdown: {e}")


# FastAPI application with lifespan
app = FastAPI(
    title="API Gateway",
    description="Workflow Agent Team API Gateway - Frontend Auth with JWT Verification",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers - Frontend handles auth, backend verifies tokens
app.include_router(session.router, prefix="/api/v1", tags=["session"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["workflow"])


# Basic health check
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    log_info("Health check requested")
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.get("/")
async def root():
    """Root endpoint"""
    log_info("Root endpoint accessed")
    return {
        "message": "API Gateway for Workflow Agent Team",
        "version": "1.0.0",
        "auth_model": "Frontend authentication with JWT verification",
        "features": [
            "JWT Token Verification",
            "Session Management with Actions", 
            "Chat API with SSE Streaming",
            "Integrated Workflow Generation in Chat"
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "sessions": "/api/v1/session",
            "chat": "/api/v1/chat/stream"
        }
    }


# JWT authentication middleware for Supabase tokens
@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    """
    JWT authentication middleware - verifies Supabase tokens from frontend
    """
    from app.services.auth_service import verify_supabase_token
    
    path = request.url.path
    method = request.method
    
    log_info(f"📨 {method} {path} - Processing request")
    
    # Skip authentication for public endpoints
    public_paths = [
        "/health", "/", "/docs", "/openapi.json", "/redoc", "/docs-json"
    ]
    
    if path in public_paths:
        log_info(f"🌐 {path} - Public endpoint, skipping auth")
        return await call_next(request)
    
    # Extract and validate authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        log_warning(f"🚫 {path} - Missing or invalid Authorization header")
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Missing or invalid authorization header. Use: Authorization: Bearer <token>"
            }
        )
    
    token = auth_header.replace("Bearer ", "")
    log_info(f"🔐 {path} - Verifying JWT token (length: {len(token)})")
    
    try:
        # Verify token with Supabase
        user_data = await verify_supabase_token(token)
        if not user_data:
            log_warning(f"🚫 {path} - Invalid or expired token")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized", 
                    "message": "Invalid or expired token"
                }
            )
        
        # Add user data and access token to request state
        request.state.user = user_data
        request.state.user_id = user_data.get("sub")
        request.state.access_token = token  # Store for RLS operations
        
        log_info(f"✅ {path} - Auth successful for user {user_data.get('email', 'unknown')}")
        
        response = await call_next(request)
        log_info(f"📤 {method} {path} - Response: {response.status_code}")
        return response
        
    except Exception as e:
        log_exception(f"❌ {path} - Authentication error: {str(e)}")
        
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Authentication failed"
            }
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc):
    """Global exception handler with enhanced logging"""
    path = request.url.path
    method = request.method
    
    log_exception(f"💥 {method} {path} - Unhandled exception: {type(exc).__name__}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "Internal server error occurred",
            "path": path
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )