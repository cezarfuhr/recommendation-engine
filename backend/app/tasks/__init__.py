"""Task module initialization"""

from .celery_config import celery_app
from . import celery_tasks

__all__ = ["celery_app", "celery_tasks"]
