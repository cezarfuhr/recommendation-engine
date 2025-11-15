"""Configuration settings for the recommendation engine"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Recommendation Engine"
    VERSION: str = "1.0.0"

    # Database Settings
    POSTGRES_USER: str = "recommender"
    POSTGRES_PASSWORD: str = "recommender_pass"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "recommendation_engine"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis Settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Spark Settings
    SPARK_MASTER: str = "local[*]"
    SPARK_APP_NAME: str = "RecommendationEngine"

    # Recommendation Settings
    COLLABORATIVE_K_NEIGHBORS: int = 20
    CONTENT_TOP_N: int = 10
    HYBRID_ALPHA: float = 0.6  # Weight for collaborative filtering (1-alpha for content-based)
    MIN_INTERACTIONS: int = 5

    # A/B Testing Settings
    AB_TEST_RATIO: float = 0.5  # 50/50 split

    # Cache Settings
    CACHE_TTL: int = 3600  # 1 hour

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
