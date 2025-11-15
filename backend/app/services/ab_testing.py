"""A/B Testing Service"""

import hashlib
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import ABTest, ABTestAssignment


class ABTestingService:
    """
    A/B Testing framework for comparing recommendation algorithms

    Allows running experiments to compare different recommendation
    algorithms and track which performs better.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_test(
        self,
        name: str,
        description: str,
        variant_a_algorithm: str,
        variant_b_algorithm: str,
        variant_a_name: str = "control",
        variant_b_name: str = "treatment",
        split_ratio: float = 0.5,
        config: Optional[Dict[str, Any]] = None
    ) -> ABTest:
        """
        Create a new A/B test

        Args:
            name: Test name (unique identifier)
            description: Test description
            variant_a_algorithm: Algorithm for variant A
            variant_b_algorithm: Algorithm for variant B
            variant_a_name: Name for variant A (default: "control")
            variant_b_name: Name for variant B (default: "treatment")
            split_ratio: Ratio of users in variant A (default: 0.5 for 50/50 split)
            config: Additional configuration dictionary

        Returns:
            Created ABTest object
        """

        ab_test = ABTest(
            name=name,
            description=description,
            variant_a_name=variant_a_name,
            variant_b_name=variant_b_name,
            variant_a_algorithm=variant_a_algorithm,
            variant_b_algorithm=variant_b_algorithm,
            split_ratio=split_ratio,
            is_active=True,
            config=config or {}
        )

        self.db.add(ab_test)
        self.db.commit()
        self.db.refresh(ab_test)

        return ab_test

    def get_test(self, test_id: int) -> Optional[ABTest]:
        """
        Get an A/B test by ID

        Args:
            test_id: Test ID

        Returns:
            ABTest object or None
        """

        return self.db.query(ABTest).filter(ABTest.id == test_id).first()

    def get_test_by_name(self, name: str) -> Optional[ABTest]:
        """
        Get an A/B test by name

        Args:
            name: Test name

        Returns:
            ABTest object or None
        """

        return self.db.query(ABTest).filter(ABTest.name == name).first()

    def get_active_tests(self) -> list:
        """
        Get all active A/B tests

        Returns:
            List of active ABTest objects
        """

        return self.db.query(ABTest).filter(ABTest.is_active == True).all()

    def assign_user_to_test(self, test_id: int, user_id: int) -> str:
        """
        Assign a user to a variant in an A/B test

        Uses deterministic hashing to ensure consistent assignments.

        Args:
            test_id: Test ID
            user_id: User ID

        Returns:
            Variant assignment ('A' or 'B')
        """

        # Check if user already has an assignment
        existing_assignment = (
            self.db.query(ABTestAssignment)
            .filter(
                ABTestAssignment.ab_test_id == test_id,
                ABTestAssignment.user_id == user_id
            )
            .first()
        )

        if existing_assignment:
            return existing_assignment.variant

        # Get test configuration
        ab_test = self.get_test(test_id)
        if not ab_test:
            raise ValueError(f"A/B test {test_id} not found")

        # Deterministic assignment using hash
        variant = self._hash_assignment(user_id, test_id, ab_test.split_ratio)

        # Store assignment
        assignment = ABTestAssignment(
            ab_test_id=test_id,
            user_id=user_id,
            variant=variant
        )

        self.db.add(assignment)
        self.db.commit()

        return variant

    def get_user_variant(self, test_id: int, user_id: int) -> Optional[str]:
        """
        Get user's variant assignment for a test

        Args:
            test_id: Test ID
            user_id: User ID

        Returns:
            Variant ('A' or 'B') or None if not assigned
        """

        assignment = (
            self.db.query(ABTestAssignment)
            .filter(
                ABTestAssignment.ab_test_id == test_id,
                ABTestAssignment.user_id == user_id
            )
            .first()
        )

        return assignment.variant if assignment else None

    def get_algorithm_for_user(self, test_name: str, user_id: int) -> Optional[str]:
        """
        Get the algorithm that should be used for a user based on A/B test

        Args:
            test_name: Test name
            user_id: User ID

        Returns:
            Algorithm name or None if test not found/active
        """

        ab_test = self.get_test_by_name(test_name)

        if not ab_test or not ab_test.is_active:
            return None

        # Get or assign variant
        variant = self.get_user_variant(ab_test.id, user_id)
        if not variant:
            variant = self.assign_user_to_test(ab_test.id, user_id)

        # Return appropriate algorithm
        if variant == 'A':
            return ab_test.variant_a_algorithm
        else:
            return ab_test.variant_b_algorithm

    def get_test_statistics(self, test_id: int) -> Dict[str, Any]:
        """
        Get statistics for an A/B test

        Args:
            test_id: Test ID

        Returns:
            Dictionary with test statistics
        """

        ab_test = self.get_test(test_id)
        if not ab_test:
            return {}

        # Count assignments per variant
        variant_counts = (
            self.db.query(
                ABTestAssignment.variant,
                func.count(ABTestAssignment.id).label('count')
            )
            .filter(ABTestAssignment.ab_test_id == test_id)
            .group_by(ABTestAssignment.variant)
            .all()
        )

        counts = {variant: count for variant, count in variant_counts}
        total_users = sum(counts.values())

        return {
            "test_id": test_id,
            "test_name": ab_test.name,
            "variant_a_name": ab_test.variant_a_name,
            "variant_b_name": ab_test.variant_b_name,
            "variant_a_algorithm": ab_test.variant_a_algorithm,
            "variant_b_algorithm": ab_test.variant_b_algorithm,
            "variant_a_count": counts.get('A', 0),
            "variant_b_count": counts.get('B', 0),
            "total_users": total_users,
            "variant_a_percentage": (counts.get('A', 0) / total_users * 100) if total_users > 0 else 0,
            "variant_b_percentage": (counts.get('B', 0) / total_users * 100) if total_users > 0 else 0,
            "is_active": ab_test.is_active
        }

    def deactivate_test(self, test_id: int) -> bool:
        """
        Deactivate an A/B test

        Args:
            test_id: Test ID

        Returns:
            True if successful, False otherwise
        """

        ab_test = self.get_test(test_id)
        if not ab_test:
            return False

        ab_test.is_active = False
        self.db.commit()

        return True

    def _hash_assignment(self, user_id: int, test_id: int, split_ratio: float) -> str:
        """
        Deterministically assign user to variant using hash

        Args:
            user_id: User ID
            test_id: Test ID
            split_ratio: Ratio for variant A (0.5 = 50/50 split)

        Returns:
            'A' or 'B'
        """

        # Create deterministic hash
        hash_input = f"{user_id}:{test_id}".encode('utf-8')
        hash_value = hashlib.md5(hash_input).hexdigest()

        # Convert hash to number between 0 and 1
        hash_number = int(hash_value, 16) / (16 ** 32)

        # Assign based on split ratio
        return 'A' if hash_number < split_ratio else 'B'
