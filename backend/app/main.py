"""
Recommendation Engine - Main FastAPI Application

A comprehensive recommendation system supporting:
- Collaborative Filtering (user-based and item-based)
- Content-Based Filtering
- Hybrid Approach
- Real-time Updates with Redis
- A/B Testing Framework
- JWT Authentication
- Rate Limiting
- Structured Logging
- Prometheus Metrics
- Background Jobs with Celery
- Feature Store
- Business Rules Engine
"""

from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .api import api_router
from .api.auth import router as auth_router
from .utils.database import init_db
from .services.realtime import RealtimeUpdateService
from .utils.logging import setup_logging, get_logger, configure_uvicorn_logging
from .utils.metrics import setup_metrics
from .utils.rate_limit import limiter

# Setup structured logging
setup_logging(log_level="INFO")
configure_uvicorn_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""

    # Startup
    logger.info("Starting Recommendation Engine", version=settings.VERSION)

    # Initialize database
    logger.info("Initializing database")
    init_db()

    # Check Redis connection
    logger.info("Checking Redis connection")
    realtime_service = RealtimeUpdateService()
    if realtime_service.health_check():
        logger.info("Redis connection successful")
    else:
        logger.warning("Redis connection failed - real-time features may not work")

    logger.info("Recommendation Engine started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Recommendation Engine")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    # Recommendation Engine API

    A production-ready recommendation system with multiple algorithms and real-time capabilities.

    ## Features

    🤝 **Collaborative Filtering**
    - User-based collaborative filtering
    - Item-based collaborative filtering
    - Hybrid approach combining both

    📄 **Content-Based Filtering**
    - TF-IDF vectorization of item features
    - Cosine similarity for item matching
    - Category-based recommendations

    🧠 **Hybrid Recommendations**
    - Weighted combination of algorithms
    - Rank-based fusion
    - Cascade approach

    🔥 **Real-time Updates**
    - Redis caching for fast responses
    - Real-time interaction tracking
    - Trending items detection

    📊 **A/B Testing**
    - Compare algorithm performance
    - Deterministic user assignment
    - Real-time statistics

    🔒 **Security**
    - JWT Authentication
    - Rate Limiting
    - Role-based access control

    📈 **Observability**
    - Structured logging (JSON)
    - Prometheus metrics
    - Health checks

    ⚙️ **Advanced Features**
    - Background jobs with Celery
    - Feature Store for consistent features
    - Business Rules Engine

    ## Algorithms

    - `collaborative`: Uses user-item interaction patterns to find similar users and items
    - `content_based`: Analyzes item features to recommend similar items
    - `hybrid`: Combines multiple approaches for best results (recommended)

    ## Quick Start

    1. Create users and items
    2. Record user interactions
    3. Get personalized recommendations
    4. Optionally set up A/B tests to compare algorithms
    """,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "Authentication endpoints (login, register, token refresh)"},
        {"name": "users", "description": "User management operations"},
        {"name": "items", "description": "Item management operations"},
        {"name": "interactions", "description": "User-item interaction tracking"},
        {"name": "recommendations", "description": "Recommendation generation and retrieval"},
        {"name": "ab-tests", "description": "A/B testing framework for algorithms"},
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup Prometheus metrics
setup_metrics(app)

# Include routers
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(api_router, prefix=settings.API_V1_STR)


# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    logger.info(
        "Request received",
        method=request.method,
        url=str(request.url),
        client=request.client.host if request.client else None
    )

    response = await call_next(request)

    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code
    )

    return response


@app.get("/", tags=["root"])
def root():
    """Root endpoint"""
    return {
        "message": "Recommendation Engine API",
        "version": settings.VERSION,
        "docs": "/docs",
        "status": "operational"
    }


@app.get("/health", tags=["root"], status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint"""

    # Check Redis
    realtime_service = RealtimeUpdateService()
    redis_healthy = realtime_service.health_check()

    # Check database (basic check)
    from .utils.database import SessionLocal
    db_healthy = True
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        db_healthy = False

    overall_healthy = redis_healthy and db_healthy

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "redis": "connected" if redis_healthy else "disconnected",
        "database": "connected" if db_healthy else "disconnected",
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
