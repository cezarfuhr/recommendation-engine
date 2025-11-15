"""Celery configuration and task definitions"""

from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery
celery_app = Celery(
    "recommendation_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/2"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/3")
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic tasks schedule
celery_app.conf.beat_schedule = {
    'retrain-collaborative-model': {
        'task': 'app.tasks.celery_tasks.retrain_collaborative_model',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
    },
    'update-item-features': {
        'task': 'app.tasks.celery_tasks.update_item_features_task',
        'schedule': crontab(hour=3, minute=0),  # Run at 3 AM daily
    },
    'generate-batch-recommendations': {
        'task': 'app.tasks.celery_tasks.generate_batch_recommendations',
        'schedule': crontab(hour=4, minute=0),  # Run at 4 AM daily
    },
    'cleanup-old-cache': {
        'task': 'app.tasks.celery_tasks.cleanup_old_cache',
        'schedule': crontab(hour=1, minute=0),  # Run at 1 AM daily
    },
    'update-system-metrics': {
        'task': 'app.tasks.celery_tasks.update_metrics_task',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
