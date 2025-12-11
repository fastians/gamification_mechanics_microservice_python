"""
API Gateway - Central Entry Point for Microservices
Routes requests to appropriate backend services
"""

import logging
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 30.0

app = FastAPI(
    title="API Gateway",
    description="Central API Gateway for Gamification Microservices",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs - using Docker service names
SERVICES = {
    "auth": "http://auth_service:8001",
    "quest_catalog": "http://quest_catalog_service:8002",
    "quest_processing": "http://quest_processing_service:8003",
}


# Health Check
@app.get("/health", tags=["Health"])
async def health_check():
    """Gateway health check endpoint"""
    service_health = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health")
                service_health[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "code": response.status_code
                }
            except Exception as e:
                service_health[service_name] = {
                    "status": "unreachable",
                    "error": str(e)
                }

    all_healthy = all(
        s.get("status") == "healthy"
        for s in service_health.values()
    )

    return {
        "gateway": "healthy",
        "services": service_health,
        "overall_status": "healthy" if all_healthy else "degraded"
    }


# Main Middleware for Routing
@app.middleware("http")
async def proxy_requests(request: Request, call_next):
    """
    Main routing middleware
    - Routes requests to appropriate microservices
    - Handles CORS preflight requests
    - Provides error handling and logging
    """
    path = request.url.path
    method = request.method.lower()

    logger.info(f"Incoming request: {method.upper()} {path}")

    # Skip middleware for gateway's own health endpoint
    if path == "/health":
        return await call_next(request)

    # Handle CORS preflight requests
    if method == "options":
        return Response(
            status_code=status.HTTP_200_OK,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
            },
            content=""
        )

    # Route determination
    target_url = None

    # Auth Service routes
    if path.startswith(("/signup", "/login", "/users", "/add-diamonds", "/add-gold")):
        target_url = SERVICES["auth"] + path

    # Quest Catalog Service routes
    elif path.startswith(("/quests", "/rewards")):
        target_url = SERVICES["quest_catalog"] + path

    # Quest Processing Service routes
    elif path.startswith((
        "/assign-quest",
        "/user-quests",
        "/complete-quest",
        "/track-sign-in",
        "/claim-quest"
    )):
        target_url = SERVICES["quest_processing"] + path

    # Unknown route
    else:
        logger.warning(f"Unknown route: {method.upper()} {path}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Route not found: {path}"}
        )

    logger.info(f"Proxying to: {target_url}")

    # Forward request to target service
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            # Prepare request body if exists
            body = await request.body() if method in ["post", "put", "patch"] else None

            # Forward request
            if method == "get":
                resp = await client.get(
                    target_url,
                    params=request.query_params,
                    headers=dict(request.headers)
                )
            elif method == "post":
                resp = await client.post(
                    target_url,
                    content=body,
                    headers=dict(request.headers)
                )
            elif method == "put":
                resp = await client.put(
                    target_url,
                    content=body,
                    headers=dict(request.headers)
                )
            elif method == "delete":
                resp = await client.delete(
                    target_url,
                    headers=dict(request.headers)
                )
            elif method == "patch":
                resp = await client.patch(
                    target_url,
                    content=body,
                    headers=dict(request.headers)
                )
            else:
                logger.warning(f"Unsupported HTTP method: {method.upper()}")
                return JSONResponse(
                    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                    content={"detail": f"Method {method.upper()} not allowed"}
                )

            logger.info(f"Response from {target_url}: {resp.status_code}")

            # Return proxied response
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers)
            )

        except httpx.TimeoutException:
            logger.error(f"Request timeout for {target_url}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={"detail": "Request to backend service timed out"}
            )

        except httpx.ConnectError:
            logger.error(f"Connection error to {target_url}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Backend service unavailable"}
            )

        except httpx.RequestError as e:
            logger.error(f"Request error to {target_url}: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": "Error communicating with backend service"}
            )

        except Exception as e:
            logger.error(f"Unexpected error proxying request: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal gateway error"}
            )


# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Log gateway startup"""
    logger.info("=" * 60)
    logger.info("API Gateway starting...")
    logger.info(f"Configured backend services:")
    for name, url in SERVICES.items():
        logger.info(f"  - {name}: {url}")
    logger.info("API Gateway ready")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Log gateway shutdown"""
    logger.info("API Gateway shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
