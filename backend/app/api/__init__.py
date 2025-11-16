"""API routes"""

from fastapi import APIRouter
from .users import router as users_router
from .items import router as items_router
from .interactions import router as interactions_router
from .recommendations import router as recommendations_router
from .ab_tests import router as ab_tests_router

api_router = APIRouter()

api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(items_router, prefix="/items", tags=["items"])
api_router.include_router(interactions_router, prefix="/interactions", tags=["interactions"])
api_router.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(ab_tests_router, prefix="/ab-tests", tags=["ab-tests"])
