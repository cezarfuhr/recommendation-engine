"""Prometheus metrics configuration"""

from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator import Instrumentator
from typing import Callable
import time
from functools import wraps

# Application info
app_info = Info('recommendation_engine', 'Recommendation Engine Information')
app_info.info({
    'version': '1.0.0',
    'service': 'recommendation-engine-backend'
})

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Recommendation metrics
recommendations_generated_total = Counter(
    'recommendations_generated_total',
    'Total recommendations generated',
    ['algorithm', 'user_id']
)

recommendation_generation_duration_seconds = Histogram(
    'recommendation_generation_duration_seconds',
    'Time taken to generate recommendations',
    ['algorithm']
)

# Interaction metrics
interactions_created_total = Counter(
    'interactions_created_total',
    'Total interactions created',
    ['interaction_type']
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Model metrics
active_users_gauge = Gauge(
    'active_users',
    'Number of active users'
)

active_items_gauge = Gauge(
    'active_items',
    'Number of active items'
)

total_interactions_gauge = Gauge(
    'total_interactions',
    'Total number of interactions'
)

# A/B Testing metrics
ab_test_assignments_total = Counter(
    'ab_test_assignments_total',
    'Total A/B test assignments',
    ['test_name', 'variant']
)

# Database metrics
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type']
)

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

db_connection_pool_available = Gauge(
    'db_connection_pool_available',
    'Available database connections in pool'
)


def setup_metrics(app):
    """
    Setup Prometheus metrics for FastAPI app

    Args:
        app: FastAPI application instance
    """
    # Instrument app with default metrics
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True
    )

    instrumentator.instrument(app).expose(app, endpoint="/metrics")

    return instrumentator


def track_recommendation_time(algorithm: str):
    """
    Decorator to track recommendation generation time

    Usage:
        @track_recommendation_time("collaborative")
        def generate_recommendations():
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                recommendation_generation_duration_seconds.labels(
                    algorithm=algorithm
                ).observe(duration)

        return wrapper

    return decorator


def track_db_query(query_type: str):
    """
    Decorator to track database query time

    Usage:
        @track_db_query("select_users")
        def get_users():
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                db_query_duration_seconds.labels(
                    query_type=query_type
                ).observe(duration)

        return wrapper

    return decorator


def increment_cache_hit(cache_type: str = "redis"):
    """Increment cache hit counter"""
    cache_hits_total.labels(cache_type=cache_type).inc()


def increment_cache_miss(cache_type: str = "redis"):
    """Increment cache miss counter"""
    cache_misses_total.labels(cache_type=cache_type).inc()


def record_recommendation(algorithm: str, user_id: int, count: int = 1):
    """Record recommendation generation"""
    recommendations_generated_total.labels(
        algorithm=algorithm,
        user_id=str(user_id)
    ).inc(count)


def record_interaction(interaction_type: str):
    """Record interaction creation"""
    interactions_created_total.labels(
        interaction_type=interaction_type
    ).inc()


def record_ab_assignment(test_name: str, variant: str):
    """Record A/B test assignment"""
    ab_test_assignments_total.labels(
        test_name=test_name,
        variant=variant
    ).inc()


def update_system_metrics(db):
    """
    Update system-wide metrics (call periodically)

    Args:
        db: Database session
    """
    from ..models import User, Item, Interaction

    # Update user count
    user_count = db.query(User).count()
    active_users_gauge.set(user_count)

    # Update item count
    item_count = db.query(Item).count()
    active_items_gauge.set(item_count)

    # Update interaction count
    interaction_count = db.query(Interaction).count()
    total_interactions_gauge.set(interaction_count)
