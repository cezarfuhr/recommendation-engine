"""A/B Testing API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from ..models import ABTest
from ..utils.database import get_db
from ..services.ab_testing import ABTestingService

router = APIRouter()


class ABTestCreate(BaseModel):
    """Schema for creating an A/B test"""

    name: str = Field(..., min_length=1, max_length=200)
    description: str
    variant_a_algorithm: str = Field(..., min_length=1, max_length=50)
    variant_b_algorithm: str = Field(..., min_length=1, max_length=50)
    variant_a_name: str = "control"
    variant_b_name: str = "treatment"
    split_ratio: float = Field(0.5, ge=0, le=1)
    config: Optional[Dict[str, Any]] = {}


class ABTestResponse(BaseModel):
    """Schema for A/B test response"""

    id: int
    name: str
    description: str
    variant_a_name: str
    variant_b_name: str
    variant_a_algorithm: str
    variant_b_algorithm: str
    split_ratio: float
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=ABTestResponse, status_code=status.HTTP_201_CREATED)
def create_ab_test(test: ABTestCreate, db: Session = Depends(get_db)):
    """Create a new A/B test"""

    service = ABTestingService(db)

    # Check if test with same name exists
    existing = service.get_test_by_name(test.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A/B test with this name already exists"
        )

    ab_test = service.create_test(
        name=test.name,
        description=test.description,
        variant_a_algorithm=test.variant_a_algorithm,
        variant_b_algorithm=test.variant_b_algorithm,
        variant_a_name=test.variant_a_name,
        variant_b_name=test.variant_b_name,
        split_ratio=test.split_ratio,
        config=test.config
    )

    return ab_test


@router.get("/", response_model=List[ABTestResponse])
def list_ab_tests(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all A/B tests"""

    service = ABTestingService(db)

    if active_only:
        tests = service.get_active_tests()
    else:
        tests = db.query(ABTest).all()

    return tests


@router.get("/{test_id}", response_model=ABTestResponse)
def get_ab_test(test_id: int, db: Session = Depends(get_db)):
    """Get a specific A/B test"""

    service = ABTestingService(db)
    ab_test = service.get_test(test_id)

    if not ab_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A/B test not found"
        )

    return ab_test


@router.get("/{test_id}/stats")
def get_ab_test_statistics(test_id: int, db: Session = Depends(get_db)):
    """Get statistics for an A/B test"""

    service = ABTestingService(db)
    stats = service.get_test_statistics(test_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A/B test not found"
        )

    return stats


@router.post("/{test_id}/assign/{user_id}")
def assign_user_to_variant(test_id: int, user_id: int, db: Session = Depends(get_db)):
    """Assign a user to a variant in an A/B test"""

    service = ABTestingService(db)

    try:
        variant = service.assign_user_to_test(test_id, user_id)
        ab_test = service.get_test(test_id)

        return {
            "test_id": test_id,
            "test_name": ab_test.name,
            "user_id": user_id,
            "variant": variant,
            "algorithm": ab_test.variant_a_algorithm if variant == 'A' else ab_test.variant_b_algorithm
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{test_id}/user/{user_id}")
def get_user_variant(test_id: int, user_id: int, db: Session = Depends(get_db)):
    """Get a user's variant assignment for an A/B test"""

    service = ABTestingService(db)
    variant = service.get_user_variant(test_id, user_id)

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not assigned to this test"
        )

    ab_test = service.get_test(test_id)

    return {
        "test_id": test_id,
        "test_name": ab_test.name,
        "user_id": user_id,
        "variant": variant,
        "algorithm": ab_test.variant_a_algorithm if variant == 'A' else ab_test.variant_b_algorithm
    }


@router.post("/{test_id}/deactivate")
def deactivate_ab_test(test_id: int, db: Session = Depends(get_db)):
    """Deactivate an A/B test"""

    service = ABTestingService(db)
    success = service.deactivate_test(test_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A/B test not found"
        )

    return {"message": "A/B test deactivated successfully", "test_id": test_id}
