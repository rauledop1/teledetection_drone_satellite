import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

# Add shared modules to path
sys.path.append('/app/shared')

from config import APIGatewaySettings
from utils import setup_logging, ServiceError
from middleware import AuthMiddleware, LoggingMiddleware, MetricsMiddleware


# Setup logging
logger = setup_logging("api-gateway")

# Settings
settings = APIGatewaySettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting API Gateway")
    
    # Initialize HTTP client
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    
    yield
    
    # Cleanup
    await app.state.http_client.aclose()
    logger.info("API Gateway shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Teledetection Drone Satellite Platform",
    description="API Gateway for drone and satellite image processing platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(AuthMiddleware)


# Service routing configuration
SERVICE_ROUTES = {
    "/api/v1/auth": settings.auth_service_url,
    "/api/v1/files": settings.file_service_url,
    "/api/v1/webodm": settings.webodm_service_url,
    "/api/v1/gee": settings.gee_service_url,
    "/api/v1/processing": settings.processing_service_url,
    "/api/v1/analysis": settings.analysis_service_url,
    "/api/v1/visualization": settings.visualization_service_url,
}


async def proxy_request(
    request: Request,
    target_url: str,
    path: str
) -> JSONResponse:
    """Proxy request to target service"""
    try:
        # Prepare request data
        method = request.method
        headers = dict(request.headers)
        
        # Remove host header to avoid conflicts
        headers.pop("host", None)
        
        # Get request body if present
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Make request to target service
        async with app.state.http_client as client:
            response = await client.request(
                method=method,
                url=f"{target_url}{path}",
                headers=headers,
                content=body,
                params=request.query_params
            )
        
        # Return response
        return JSONResponse(
            content=response.json() if response.content else {},
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    
    except httpx.TimeoutException:
        logger.error(f"Timeout when proxying to {target_url}{path}")
        raise HTTPException(status_code=504, detail="Service timeout")
    
    except httpx.ConnectError:
        logger.error(f"Connection error when proxying to {target_url}{path}")
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    except Exception as e:
        logger.error(f"Error proxying request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Teledetection Drone Satellite Platform API Gateway",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": await check_services_health()
    }


async def check_services_health() -> Dict[str, str]:
    """Check health of all services"""
    services_health = {}
    
    for route, service_url in SERVICE_ROUTES.items():
        try:
            async with app.state.http_client as client:
                response = await client.get(
                    f"{service_url}/health",
                    timeout=5.0
                )
                services_health[route] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services_health[route] = "unhealthy"
    
    return services_health


@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def api_proxy(request: Request, path: str):
    """Proxy API requests to appropriate services"""
    request_path = f"/api/v1/{path}"
    
    # Find matching service route
    target_service = None
    service_path = None
    
    for route_prefix, service_url in SERVICE_ROUTES.items():
        if request_path.startswith(route_prefix):
            target_service = service_url
            service_path = request_path[len(route_prefix):]
            break
    
    if not target_service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return await proxy_request(request, target_service, service_path)


# Error handlers
@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    """Handle service errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )