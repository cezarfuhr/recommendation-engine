"""Background task definitions"""

from .celery_config import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime, timedelta

from ..config import settings
from ..models import User, Item, Interaction, Recommendation
from ..services.collaborative_filtering import CollaborativeFilteringService
from ..services.content_based import ContentBasedService
from ..services.hybrid import HybridRecommendationService
from ..services.realtime import RealtimeUpdateService
from ..utils.logging import get_logger
from ..utils.metrics import update_system_metrics

logger = get_logger(__name__)

# Database session for tasks
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@celery_app.task(name="app.tasks.celery_tasks.retrain_collaborative_model")
def retrain_collaborative_model():
    """
    Retrain collaborative filtering model

    Runs periodically to update the model with new interactions.
    """
    logger.info("Starting collaborative model retraining")
    db = SessionLocal()

    try:
        service = CollaborativeFilteringService(db)

        # Rebuild matrices
        logger.info("Building user-item matrix")
        service.build_user_item_matrix()

        logger.info("Computing user similarity")
        service.compute_user_similarity()

        logger.info("Computing item similarity")
        service.compute_item_similarity()

        logger.info("Collaborative model retraining completed successfully")

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Collaborative model retrained"
        }

    except Exception as e:
        logger.error("Error retraining collaborative model", exc_info=True)
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.celery_tasks.update_item_features_task")
def update_item_features_task():
    """
    Update item features for content-based filtering

    Recalculates TF-IDF features and item similarity matrix.
    """
    logger.info("Starting item features update")
    db = SessionLocal()

    try:
        service = ContentBasedService(db)

        logger.info("Building item features")
        service.build_item_features()

        logger.info("Computing item similarity")
        service.compute_item_similarity()

        # Update item popularity scores
        items = db.query(Item).all()
        for item in items:
            interaction_count = db.query(Interaction).filter(
                Interaction.item_id == item.id
            ).count()

            avg_rating = db.query(Interaction).filter(
                Interaction.item_id == item.id,
                Interaction.rating.isnot(None)
            ).with_entities(
                func.avg(Interaction.rating)
            ).scalar() or 0.0

            item.popularity_score = interaction_count * 0.3 + avg_rating * 0.7

        db.commit()

        logger.info("Item features update completed successfully")

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "items_updated": len(items),
            "message": "Item features updated"
        }

    except Exception as e:
        logger.error("Error updating item features", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.celery_tasks.generate_batch_recommendations")
def generate_batch_recommendations(top_n: int = 20):
    """
    Generate recommendations for all users in batch

    Args:
        top_n: Number of recommendations per user
    """
    logger.info(f"Starting batch recommendation generation for top {top_n} items")
    db = SessionLocal()

    try:
        # Get all users
        users = db.query(User).all()
        logger.info(f"Generating recommendations for {len(users)} users")

        service = HybridRecommendationService(db)
        total_recommendations = 0

        for user in users:
            # Generate recommendations
            recommendations = service.get_recommendations(
                user.id,
                top_n=top_n,
                exclude_interacted=True,
                method="weighted"
            )

            # Delete old hybrid recommendations for this user
            db.query(Recommendation).filter(
                Recommendation.user_id == user.id,
                Recommendation.algorithm == "hybrid"
            ).delete()

            # Store new recommendations
            for rank, (item_id, score) in enumerate(recommendations, 1):
                rec = Recommendation(
                    user_id=user.id,
                    item_id=item_id,
                    score=score,
                    algorithm="hybrid",
                    rank=rank
                )
                db.add(rec)
                total_recommendations += 1

        db.commit()

        logger.info(f"Batch recommendation generation completed: {total_recommendations} recommendations")

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "users_processed": len(users),
            "recommendations_generated": total_recommendations,
            "message": "Batch recommendations generated"
        }

    except Exception as e:
        logger.error("Error generating batch recommendations", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.celery_tasks.cleanup_old_cache")
def cleanup_old_cache():
    """
    Clean up old cached data in Redis

    Removes expired cache entries and old interaction data.
    """
    logger.info("Starting cache cleanup")

    try:
        realtime_service = RealtimeUpdateService()

        # Redis automatically expires keys, but we can do additional cleanup
        # For example, clean up old interaction tracking data

        # This is a placeholder - implement based on your needs
        logger.info("Cache cleanup completed")

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Cache cleaned up"
        }

    except Exception as e:
        logger.error("Error cleaning up cache", exc_info=True)
        raise


@celery_app.task(name="app.tasks.celery_tasks.update_metrics_task")
def update_metrics_task():
    """
    Update Prometheus metrics

    Runs periodically to update system-wide metrics.
    """
    db = SessionLocal()

    try:
        update_system_metrics(db)

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Metrics updated"
        }

    except Exception as e:
        logger.error("Error updating metrics", exc_info=True)
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.celery_tasks.send_recommendation_email")
def send_recommendation_email(user_id: int, recommendations: list):
    """
    Send recommendation email to user (placeholder)

    Args:
        user_id: User ID
        recommendations: List of recommended items
    """
    logger.info(f"Sending recommendation email to user {user_id}")

    # TODO: Implement email sending with SMTP or email service
    # This is a placeholder

    return {
        "status": "success",
        "user_id": user_id,
        "recommendations_count": len(recommendations),
        "message": "Email sent"
    }


# Import func for SQL operations
from sqlalchemy import func
