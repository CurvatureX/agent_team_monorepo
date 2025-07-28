"""
API Gateway - Simplified with Frontend Auth
"""

import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import init_supabase
from app.models import HealthResponse
from app.api import session, chat, workflow, mcp
from app.services.grpc_client import workflow_client

# Configure structlog for JSON logging with line numbers
structlog.configure(
    processors=[
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configure stdlib logging
logging.basicConfig(
    format="%(message)s",
    level=getattr(logging, getattr(settings, 'LOG_LEVEL', 'INFO').upper(), logging.INFO),
)

logger = structlog.get_logger("api-gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - replaces deprecated on_event"""
    # Startup
    try:
        logger.info("🚀 Starting API Gateway with Frontend Auth...")
        
        # Initialize Supabase connection
        init_supabase()
        logger.info("✅ Supabase client initialized")
        
        # Initialize gRPC client connection
        await workflow_client.connect()
        logger.info("✅ gRPC client connected")
        
        logger.info("🚀 API Gateway started successfully!")
        logger.info("📖 API Documentation: http://localhost:8000/docs")
        logger.info("🏥 Health Check: http://localhost:8000/health")
        logger.info("🔐 Auth: Frontend handles authentication, backend verifies JWT tokens")
        
    except Exception as e:
        logger.exception("❌ Failed to start API Gateway", error=str(e))
        raise
    
    yield
    
    # Shutdown
    try:
        # Close gRPC connections
        await workflow_client.close()
        
        logger.info("👋 API Gateway stopped")
        
    except Exception as e:
        logger.exception("⚠️  Error during shutdown", error=str(e))


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
app.include_router(mcp.router, prefix="/api/v1/mcp", tags=["mcp"])


# Basic health check
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
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
    
    logger.info("📨 Processing request", method=method, path=path)
    
    # Skip authentication for public endpoints
    public_paths = [
        "/health", "/", "/docs", "/openapi.json", "/redoc", "/docs-json", "/api/v1/mcp"
    ]
    
    if path in public_paths:
        logger.info("🌐 Public endpoint, skipping auth", path=path)
        return await call_next(request)
    
    # Extract and validate authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("🚫 Missing or invalid Authorization header", path=path)
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Missing or invalid authorization header. Use: Authorization: Bearer <token>"
            }
        )
    
    token = auth_header.replace("Bearer ", "")
    logger.info("🔐 Verifying JWT token", path=path, token_length=len(token))
    
    try:
        # Verify token with Supabase
        user_data = await verify_supabase_token(token)
        if not user_data:
            logger.warning("🚫 Invalid or expired token", path=path)
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
        
        logger.info("✅ Auth successful", path=path, user_email=user_data.get('email', 'unknown'))
        
        response = await call_next(request)
        logger.info("📤 Response sent", method=method, path=path, status_code=response.status_code)
        return response
        
    except Exception as e:
        logger.exception("❌ Authentication error", path=path, error=str(e))
        
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
    
    logger.exception("💥 Unhandled exception", method=method, path=path, exception_type=type(exc).__name__, error=str(exc))
    
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