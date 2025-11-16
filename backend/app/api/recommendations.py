"""Recommendation API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationItemResponse,
    AlgorithmType
)
from ..models import User, Item
from ..utils.database import get_db
from ..services.collaborative_filtering import CollaborativeFilteringService
from ..services.content_based import ContentBasedService
from ..services.hybrid import HybridRecommendationService
from ..services.realtime import RealtimeUpdateService
from ..services.ab_testing import ABTestingService

router = APIRouter()


@router.post("/", response_model=RecommendationResponse)
def get_recommendations(
    request: RecommendationRequest,
    use_cache: bool = Query(True, description="Use cached recommendations if available"),
    db: Session = Depends(get_db)
):
    """
    Get personalized recommendations for a user

    Supports multiple algorithms:
    - collaborative: Collaborative filtering (user-based + item-based)
    - content_based: Content-based filtering using item features
    - hybrid: Hybrid approach combining both methods
    """

    # Verify user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check cache first
    realtime_service = RealtimeUpdateService()
    if use_cache:
        cached_recs = realtime_service.get_cached_recommendations(
            request.user_id,
            request.algorithm.value
        )
        if cached_recs:
            return RecommendationResponse(
                user_id=request.user_id,
                algorithm=request.algorithm.value,
                recommendations=cached_recs,
                generated_at=datetime.utcnow()
            )

    # Generate recommendations based on algorithm
    if request.algorithm == AlgorithmType.COLLABORATIVE:
        service = CollaborativeFilteringService(db)
        rec_tuples = service.get_recommendations(
            request.user_id,
            request.top_n,
            method="hybrid",
            exclude_interacted=request.exclude_interacted
        )

    elif request.algorithm == AlgorithmType.CONTENT_BASED:
        service = ContentBasedService(db)
        rec_tuples = service.get_recommendations(
            request.user_id,
            request.top_n,
            exclude_interacted=request.exclude_interacted
        )

    else:  # HYBRID
        service = HybridRecommendationService(db)
        rec_tuples = service.get_recommendations(
            request.user_id,
            request.top_n,
            exclude_interacted=request.exclude_interacted,
            method="weighted"
        )

    # Convert to response format
    recommendations = []
    for rank, (item_id, score) in enumerate(rec_tuples, 1):
        item = db.query(Item).filter(Item.id == item_id).first()
        if item:
            recommendations.append(
                RecommendationItemResponse(
                    item_id=item.id,
                    title=item.title,
                    description=item.description,
                    category=item.category,
                    score=score,
                    rank=rank
                )
            )

    response_data = [rec.model_dump() for rec in recommendations]

    # Cache the results
    realtime_service.cache_recommendations(
        request.user_id,
        request.algorithm.value,
        response_data
    )

    return RecommendationResponse(
        user_id=request.user_id,
        algorithm=request.algorithm.value,
        recommendations=recommendations,
        generated_at=datetime.utcnow()
    )


@router.get("/user/{user_id}", response_model=RecommendationResponse)
def get_user_recommendations(
    user_id: int,
    top_n: int = Query(10, ge=1, le=100),
    algorithm: AlgorithmType = AlgorithmType.HYBRID,
    use_ab_test: Optional[str] = Query(None, description="A/B test name to use"),
    db: Session = Depends(get_db)
):
    """
    Get recommendations for a user (GET endpoint for convenience)

    Optionally use an A/B test to determine which algorithm to use.
    """

    # If A/B test is specified, use it to determine algorithm
    if use_ab_test:
        ab_service = ABTestingService(db)
        ab_algorithm = ab_service.get_algorithm_for_user(use_ab_test, user_id)

        if ab_algorithm:
            # Map algorithm name to enum
            algorithm_map = {
                "collaborative": AlgorithmType.COLLABORATIVE,
                "content_based": AlgorithmType.CONTENT_BASED,
                "hybrid": AlgorithmType.HYBRID
            }
            algorithm = algorithm_map.get(ab_algorithm, AlgorithmType.HYBRID)

    # Create request and delegate to POST endpoint
    request = RecommendationRequest(
        user_id=user_id,
        top_n=top_n,
        algorithm=algorithm,
        exclude_interacted=True
    )

    return get_recommendations(request, use_cache=True, db=db)


@router.get("/similar-items/{item_id}")
def get_similar_items(
    item_id: int,
    top_n: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get items similar to a specific item (content-based)"""

    # Verify item exists
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Get similar items
    service = ContentBasedService(db)
    similar_tuples = service.get_similar_items(item_id, top_n)

    # Convert to response format
    similar_items = []
    for rank, (similar_item_id, score) in enumerate(similar_tuples, 1):
        similar_item = db.query(Item).filter(Item.id == similar_item_id).first()
        if similar_item:
            similar_items.append({
                "item_id": similar_item.id,
                "title": similar_item.title,
                "description": similar_item.description,
                "category": similar_item.category,
                "similarity_score": score,
                "rank": rank
            })

    return {
        "source_item_id": item_id,
        "source_item_title": item.title,
        "similar_items": similar_items
    }


@router.get("/trending")
def get_trending_recommendations(
    limit: int = Query(10, ge=1, le=100),
    time_window: int = Query(3600, description="Time window in seconds (default: 1 hour)")
):
    """Get trending items based on recent activity"""

    realtime_service = RealtimeUpdateService()
    trending_item_ids = realtime_service.get_trending_items(limit, time_window)

    return {
        "trending_items": trending_item_ids,
        "time_window_seconds": time_window,
        "count": len(trending_item_ids)
    }


@router.post("/explain")
def explain_recommendation(
    user_id: int = Query(..., description="User ID"),
    item_id: int = Query(..., description="Item ID"),
    db: Session = Depends(get_db)
):
    """
    Explain why an item was recommended to a user

    Returns the contribution of different algorithms to the recommendation score.
    """

    # Verify user and item exist
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Get explanation from hybrid service
    service = HybridRecommendationService(db)
    explanation = service.explain_recommendation(user_id, item_id)

    return {
        "user_id": user_id,
        "item_id": item_id,
        "item_title": item.title,
        "explanation": explanation
    }
