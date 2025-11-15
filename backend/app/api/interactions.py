"""Interaction API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..schemas.interaction import InteractionCreate, InteractionResponse
from ..models import Interaction, User, Item
from ..utils.database import get_db
from ..services.realtime import RealtimeUpdateService

router = APIRouter()


@router.post("/", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
def create_interaction(interaction: InteractionCreate, db: Session = Depends(get_db)):
    """Create a new user-item interaction"""

    # Verify user exists
    user = db.query(User).filter(User.id == interaction.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify item exists
    item = db.query(Item).filter(Item.id == interaction.item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Create interaction
    db_interaction = Interaction(**interaction.model_dump())
    db.add(db_interaction)

    # Update item popularity
    item.popularity_score += interaction.weight

    db.commit()
    db.refresh(db_interaction)

    # Track in real-time cache
    realtime_service = RealtimeUpdateService()
    realtime_service.track_interaction(
        interaction.user_id,
        interaction.item_id,
        interaction.interaction_type,
        interaction.weight
    )
    realtime_service.update_item_popularity(interaction.item_id, interaction.weight)
    realtime_service.record_trending_activity(interaction.item_id)

    return db_interaction


@router.get("/user/{user_id}", response_model=List[InteractionResponse])
def get_user_interactions(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all interactions for a specific user"""

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    interactions = (
        db.query(Interaction)
        .filter(Interaction.user_id == user_id)
        .order_by(Interaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return interactions


@router.get("/item/{item_id}", response_model=List[InteractionResponse])
def get_item_interactions(item_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all interactions for a specific item"""

    # Verify item exists
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    interactions = (
        db.query(Interaction)
        .filter(Interaction.item_id == item_id)
        .order_by(Interaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return interactions


@router.get("/stats/user/{user_id}")
def get_user_interaction_stats(user_id: int, db: Session = Depends(get_db)):
    """Get interaction statistics for a user"""

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get stats
    stats = (
        db.query(
            Interaction.interaction_type,
            func.count(Interaction.id).label('count')
        )
        .filter(Interaction.user_id == user_id)
        .group_by(Interaction.interaction_type)
        .all()
    )

    total = sum(count for _, count in stats)

    return {
        "user_id": user_id,
        "total_interactions": total,
        "by_type": {interaction_type: count for interaction_type, count in stats}
    }
