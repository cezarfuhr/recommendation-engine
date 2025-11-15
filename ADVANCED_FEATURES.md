# 🚀 Advanced Features Guide

This document describes the advanced production-ready features implemented in the Recommendation Engine.

## Table of Contents

1. [JWT Authentication & Authorization](#1-jwt-authentication--authorization)
2. [Rate Limiting](#2-rate-limiting)
3. [Structured Logging & Observability](#3-structured-logging--observability)
4. [Prometheus Metrics](#4-prometheus-metrics)
5. [Background Jobs with Celery](#5-background-jobs-with-celery)
6. [Feature Store](#6-feature-store)
7. [Business Rules Engine](#7-business-rules-engine)

---

## 1. JWT Authentication & Authorization

### Overview

Secure user authentication using JSON Web Tokens (JWT) with access and refresh tokens.

### Features

- **User Registration**: Create accounts with hashed passwords
- **Login/Logout**: JWT token-based authentication
- **Token Refresh**: Refresh access tokens without re-login
- **Protected Endpoints**: Require authentication for sensitive operations
- **Role-Based Access Control (RBAC)**: Support for user roles

### Usage

#### Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepass123",
    "preferences": {}
  }'
```

#### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepass123"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Use Protected Endpoints

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

### Configuration

```python
# backend/app/utils/auth.py
SECRET_KEY = "your-secret-key"  # Change in production!
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
```

---

## 2. Rate Limiting

### Overview

Prevent API abuse with intelligent rate limiting using Redis-backed storage.

### Features

- **IP-based Limiting**: Limit requests per IP address
- **User-based Limiting**: Authenticated users have separate limits
- **Configurable Limits**: Set different limits per endpoint
- **Redis Storage**: Distributed rate limiting across multiple instances

### Configuration

Default limits:
- **Anonymous users**: 100 requests/minute
- **Authenticated users**: 200 requests/minute

### Custom Rate Limits

Apply custom limits to specific endpoints:

```python
from app.utils.rate_limit import limiter

@router.get("/expensive-operation")
@limiter.limit("5/minute")  # Only 5 requests per minute
async def expensive_operation():
    pass
```

### Monitoring

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

## 3. Structured Logging & Observability

### Overview

JSON-formatted structured logging for better log aggregation and analysis.

### Features

- **JSON Output**: Machine-readable logs
- **Contextual Information**: Automatic inclusion of request IDs, user IDs, etc.
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Correlation IDs**: Track requests across services

### Log Format

```json
{
  "timestamp": "2025-11-15T10:30:00.123Z",
  "level": "INFO",
  "service": "recommendation-engine",
  "logger_name": "app.main",
  "message": "Request completed",
  "method": "GET",
  "url": "/api/v1/recommendations/user/1",
  "status_code": 200,
  "duration_ms": 45
}
```

### Usage in Code

```python
from app.utils.logging import get_logger

logger = get_logger(__name__)

logger.info("User action", user_id=123, action="login")
logger.error("Database error", error=str(e), query="SELECT * FROM users")
```

### Log Aggregation

Logs can be easily aggregated using:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **Datadog**
- **CloudWatch Logs**

---

## 4. Prometheus Metrics

### Overview

Comprehensive metrics collection for monitoring and alerting.

### Features

- **HTTP Metrics**: Request count, duration, status codes
- **Business Metrics**: Recommendations generated, interactions created
- **System Metrics**: Active users, items, database connections
- **Custom Metrics**: Easy to add domain-specific metrics

### Available Metrics

#### HTTP Metrics
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration histogram
- `http_requests_inprogress`: Currently processing requests

#### Recommendation Metrics
- `recommendations_generated_total`: Total recommendations generated
- `recommendation_generation_duration_seconds`: Time to generate recommendations

#### Cache Metrics
- `cache_hits_total`: Cache hits
- `cache_misses_total`: Cache misses

#### System Metrics
- `active_users`: Number of active users
- `active_items`: Number of active items
- `total_interactions`: Total interactions

### Accessing Metrics

```bash
curl http://localhost:8000/metrics
```

### Sample Output

```
# HELP recommendations_generated_total Total recommendations generated
# TYPE recommendations_generated_total counter
recommendations_generated_total{algorithm="hybrid",user_id="1"} 10.0

# HELP recommendation_generation_duration_seconds Time to generate recommendations
# TYPE recommendation_generation_duration_seconds histogram
recommendation_generation_duration_seconds_bucket{algorithm="hybrid",le="0.1"} 45.0
recommendation_generation_duration_seconds_bucket{algorithm="hybrid",le="0.5"} 89.0
```

### Grafana Dashboard

Create dashboards to visualize:
- Request rate and latency
- Error rates
- Recommendation algorithm performance
- Cache hit rates
- System resource usage

---

## 5. Background Jobs with Celery

### Overview

Asynchronous task processing for heavy computations and scheduled jobs.

### Features

- **Distributed Workers**: Scale horizontally
- **Scheduled Tasks**: Cron-like scheduling
- **Task Monitoring**: Flower web UI
- **Retry Logic**: Automatic retry on failure
- **Task Chaining**: Complex workflows

### Available Tasks

#### 1. Model Retraining (Daily at 2 AM)
```python
retrain_collaborative_model()
```
Rebuilds collaborative filtering matrices with latest data.

#### 2. Feature Updates (Daily at 3 AM)
```python
update_item_features_task()
```
Recalculates TF-IDF features and item popularity.

#### 3. Batch Recommendations (Daily at 4 AM)
```python
generate_batch_recommendations(top_n=20)
```
Pre-generates recommendations for all users.

#### 4. Cache Cleanup (Daily at 1 AM)
```python
cleanup_old_cache()
```
Removes expired cache entries.

#### 5. Metrics Update (Every 5 minutes)
```python
update_metrics_task()
```
Updates Prometheus gauges with system stats.

### Manual Task Execution

```python
from app.tasks.celery_tasks import retrain_collaborative_model

# Execute task asynchronously
result = retrain_collaborative_model.delay()

# Check task status
print(result.status)  # 'PENDING', 'SUCCESS', 'FAILURE'

# Get result
print(result.get())  # Wait for completion
```

### Flower Monitoring

Access Celery Flower UI:
```
http://localhost:5555
```

Features:
- Real-time task monitoring
- Worker status
- Task history
- Task graphs and statistics

### Custom Tasks

Create custom background tasks:

```python
from app.tasks.celery_config import celery_app

@celery_app.task
def my_custom_task(param1, param2):
    # Your task logic
    return {"status": "success"}

# Execute
my_custom_task.delay("value1", "value2")
```

---

## 6. Feature Store

### Overview

Centralized feature management for consistent feature computation across training and serving.

### Features

- **User Features**: Activity score, preferences, behavior patterns
- **Item Features**: Popularity, category, tags, engagement metrics
- **User-Item Features**: Contextual features for specific pairs
- **Caching**: Redis-backed feature cache
- **Batch Retrieval**: Efficient bulk feature fetching

### Available Features

#### User Features
- `total_interactions`: Total user interactions
- `avg_rating`: Average rating given by user
- `favorite_categories`: Top categories user engages with
- `activity_score`: How active the user is (0-1)
- `recency_score`: How recently user was active (0-1)
- `account_age_days`: Days since account creation

#### Item Features
- `total_interactions`: Total interactions on item
- `avg_rating`: Average rating received
- `popularity_score`: Overall popularity
- `view_count`: Number of views
- `click_count`: Number of clicks
- `purchase_count`: Number of purchases
- `age_days`: Days since item creation

### Usage

```python
from app.services.feature_store import FeatureStore
from app.utils.database import SessionLocal

db = SessionLocal()
feature_store = FeatureStore(db)

# Get user features
user_features = feature_store.get_user_features(user_id=1)
print(user_features)
# {
#   "user_id": 1,
#   "total_interactions": 45,
#   "avg_rating": 4.2,
#   "favorite_categories": ["movies", "books"],
#   "activity_score": 0.85,
#   "recency_score": 0.95
# }

# Get item features
item_features = feature_store.get_item_features(item_id=100)

# Get user-item contextual features
context_features = feature_store.get_user_item_features(
    user_id=1,
    item_id=100
)
```

### Batch Operations

```python
import pandas as pd

# Get features for multiple users as DataFrame
user_ids = [1, 2, 3, 4, 5]
features_df = feature_store.get_user_features_batch(user_ids)
print(features_df.head())
```

### Cache Management

```python
# Invalidate user features
feature_store.invalidate_user_features(user_id=1)

# Invalidate item features
feature_store.invalidate_item_features(item_id=100)

# Invalidate all features
feature_store.invalidate_all_features()
```

---

## 7. Business Rules Engine

### Overview

Flexible rule-based system for filtering and boosting recommendations based on business logic.

### Features

- **Filter Rules**: Remove unwanted items
- **Boost Rules**: Increase scores for promoted items
- **Rerank Rules**: Change recommendation order
- **Priority System**: Control rule execution order
- **Easy Extension**: Add custom rules easily

### Built-in Rules

#### Filter Rules

1. **FilterOutOfStockRule**
   - Removes items marked as out of stock
   - Priority: 100

2. **FilterAlreadyPurchasedRule**
   - Removes items user already purchased
   - Priority: 90

3. **FilterAgeRestrictedRule**
   - Removes age-restricted content for underage users
   - Priority: 95

4. **FilterGeoRestrictedRule**
   - Removes geo-blocked content
   - Priority: 85

#### Boost Rules

1. **BoostPromotionalItemsRule**
   - Boosts items on promotion (1.5x default)
   - Priority: 50

2. **BoostNewItemsRule**
   - Boosts recently added items (1.3x default)
   - Priority: 40

3. **BoostPersonalizedPreferencesRule**
   - Boosts items matching user preferences (1.4x default)
   - Priority: 60

#### Rerank Rules

1. **DiversityRule**
   - Limits items per category for diversity
   - Priority: 20

### Usage

```python
from app.services.business_rules import BusinessRulesEngine
from app.utils.database import SessionLocal

db = SessionLocal()
engine = BusinessRulesEngine(db)

# Get recommendations from algorithm
raw_recommendations = [
    (item_id_1, score_1),
    (item_id_2, score_2),
    ...
]

# Apply business rules
filtered_recommendations = engine.apply_rules(
    recommendations=raw_recommendations,
    user=user,
    context={"country": "US", "device": "mobile"}
)
```

### Custom Rules

Create custom business rules:

```python
from app.services.business_rules import BusinessRule, RuleType

class BoostLocalItemsRule(BusinessRule):
    """Boost items from user's location"""

    def __init__(self, boost_factor=1.5):
        super().__init__("boost_local", RuleType.BOOST, priority=55)
        self.boost_factor = boost_factor

    def apply(self, recommendations, user, context, db):
        user_country = user.preferences.get("country")

        boosted = []
        for item_id, score in recommendations:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                item_country = item.features.get("origin_country")
                if item_country == user_country:
                    score *= self.boost_factor

            boosted.append((item_id, score))

        return boosted

# Add to engine
engine.add_rule(BoostLocalItemsRule())
```

### Rule Management

```python
# Get active rules
summary = engine.get_rules_summary()
print(summary)
# [
#   {"name": "filter_out_of_stock", "type": "filter", "priority": 100},
#   {"name": "boost_promotional", "type": "boost", "priority": 50},
#   ...
# ]

# Remove a rule
engine.remove_rule("boost_new_items")

# Apply only specific rule types
filtered = engine.apply_rules(
    recommendations,
    user,
    context,
    rule_types=[RuleType.FILTER]  # Only filters
)
```

### Context Variables

Pass additional context for rule decisions:

```python
context = {
    "country": "US",
    "device": "mobile",
    "time_of_day": "evening",
    "is_weekend": True,
    "weather": "rainy"
}

recommendations = engine.apply_rules(raw_recs, user, context)
```

---

## Integration Example

### Complete Workflow

```python
from app.services.hybrid import HybridRecommendationService
from app.services.business_rules import BusinessRulesEngine
from app.services.feature_store import FeatureStore
from app.utils.database import SessionLocal

db = SessionLocal()

# 1. Get user features
feature_store = FeatureStore(db)
user_features = feature_store.get_user_features(user_id=1)

# 2. Generate recommendations
rec_service = HybridRecommendationService(db)
raw_recommendations = rec_service.get_recommendations(
    user_id=1,
    top_n=20,
    method="weighted"
)

# 3. Apply business rules
rules_engine = BusinessRulesEngine(db)
final_recommendations = rules_engine.apply_rules(
    recommendations=raw_recommendations,
    user=user,
    context={"country": "US"}
)

# 4. Return top 10
return final_recommendations[:10]
```

---

## Monitoring & Operations

### Health Checks

```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "status": "healthy",
  "redis": "connected",
  "database": "connected",
  "version": "1.0.0"
}
```

### Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

### Flower (Celery)

```
http://localhost:5555
```

### Logs

View structured JSON logs:

```bash
docker-compose logs -f backend | jq .
```

---

## Configuration

All features can be configured via environment variables in `.env`:

```env
# JWT
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Celery
CELERY_BROKER_URL=redis://redis:6379/2
CELERY_RESULT_BACKEND=redis://redis:6379/3

# Feature Store
FEATURE_CACHE_TTL=3600

# Business Rules
ENABLE_BUSINESS_RULES=true
DIVERSITY_MAX_PER_CATEGORY=3
```

---

## Production Checklist

- [ ] Change SECRET_KEY to strong random value
- [ ] Configure CORS for specific origins
- [ ] Set up proper database backups
- [ ] Configure log aggregation (ELK, Splunk, etc.)
- [ ] Set up Prometheus + Grafana
- [ ] Configure alerting rules
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limiting per environment
- [ ] Set up Redis persistence
- [ ] Configure Celery worker auto-scaling
- [ ] Set up monitoring dashboards
- [ ] Configure backup Celery broker
- [ ] Test disaster recovery procedures

---

## Support

For issues or questions about advanced features:
- Check the main [README.md](README.md)
- Review the API documentation at `/docs`
- Check Prometheus metrics at `/metrics`
- Monitor Celery tasks at http://localhost:5555

---

**Built with Production Best Practices** 🚀
