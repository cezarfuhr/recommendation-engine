"""
Recommendation Engine - Main FastAPI Application

A comprehensive recommendation system supporting:
- Collaborative Filtering (user-based and item-based)
- Content-Based Filtering
- Hybrid Approach
- Real-time Updates with Redis
- A/B Testing Framework
"""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .api import api_router
from .utils.database import init_db
from .services.realtime import RealtimeUpdateService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""

    # Startup
    print("🚀 Starting Recommendation Engine...")

    # Initialize database
    print("📊 Initializing database...")
    init_db()

    # Check Redis connection
    print("🔄 Checking Redis connection...")
    realtime_service = RealtimeUpdateService()
    if realtime_service.health_check():
        print("✅ Redis connection successful")
    else:
        print("⚠️  Redis connection failed - real-time features may not work")

    print("✅ Recommendation Engine started successfully!")

    yield

    # Shutdown
    print("👋 Shutting down Recommendation Engine...")


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

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


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

    return {
        "status": "healthy" if redis_healthy else "degraded",
        "redis": "connected" if redis_healthy else "disconnected",
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
