"""Business Rules Engine for filtering and boosting recommendations"""

from typing import List, Tuple, Dict, Any, Callable
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from enum import Enum

from ..models import User, Item, Interaction
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RuleType(str, Enum):
    """Types of business rules"""
    FILTER = "filter"  # Remove items from recommendations
    BOOST = "boost"    # Increase score of items
    RERANK = "rerank"  # Change ranking order


class BusinessRule:
    """Base class for business rules"""

    def __init__(self, name: str, rule_type: RuleType, priority: int = 0):
        self.name = name
        self.rule_type = rule_type
        self.priority = priority  # Higher priority rules execute first

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """
        Apply the business rule

        Args:
            recommendations: List of (item_id, score) tuples
            user: User object
            context: Additional context (e.g., location, time, device)
            db: Database session

        Returns:
            Modified list of recommendations
        """
        raise NotImplementedError


class FilterOutOfStockRule(BusinessRule):
    """Remove out-of-stock items from recommendations"""

    def __init__(self):
        super().__init__("filter_out_of_stock", RuleType.FILTER, priority=100)

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """Filter out items marked as out of stock"""

        filtered = []
        for item_id, score in recommendations:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                # Check if item is in stock (in features or preferences)
                in_stock = item.features.get("in_stock", True)
                if in_stock:
                    filtered.append((item_id, score))
                else:
                    logger.debug(f"Filtered out of stock item: {item_id}")

        return filtered


class FilterAlreadyPurchasedRule(BusinessRule):
    """Remove items user has already purchased"""

    def __init__(self):
        super().__init__("filter_purchased", RuleType.FILTER, priority=90)

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """Filter out already purchased items"""

        # Get purchased items
        purchased_items = set(
            i.item_id for i in db.query(Interaction).filter(
                Interaction.user_id == user.id,
                Interaction.interaction_type == "purchase"
            ).all()
        )

        filtered = [
            (item_id, score) for item_id, score in recommendations
            if item_id not in purchased_items
        ]

        filtered_count = len(recommendations) - len(filtered)
        if filtered_count > 0:
            logger.debug(f"Filtered {filtered_count} already purchased items")

        return filtered


class FilterAgeRestrictedRule(BusinessRule):
    """Remove age-restricted items for underage users"""

    def __init__(self):
        super().__init__("filter_age_restricted", RuleType.FILTER, priority=95)

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """Filter age-restricted content"""

        user_age = user.preferences.get("age")
        if user_age is None:
            # If age unknown, allow all (or implement stricter policy)
            return recommendations

        filtered = []
        for item_id, score in recommendations:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                min_age = item.features.get("min_age", 0)
                if user_age >= min_age:
                    filtered.append((item_id, score))
                else:
                    logger.debug(f"Filtered age-restricted item {item_id} (requires {min_age}+)")

        return filtered


class FilterGeoRestrictedRule(BusinessRule):
    """Remove geo-restricted items"""

    def __init__(self):
        super().__init__("filter_geo_restricted", RuleType.FILTER, priority=85)

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """Filter geo-restricted content"""

        user_country = context.get("country") or user.preferences.get("country")
        if not user_country:
            return recommendations

        filtered = []
        for item_id, score in recommendations:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                allowed_countries = item.features.get("allowed_countries", [])
                blocked_countries = item.features.get("blocked_countries", [])

                if allowed_countries and user_country not in allowed_countries:
                    logger.debug(f"Filtered geo-restricted item {item_id}")
                    continue

                if user_country in blocked_countries:
                    logger.debug(f"Filtered blocked item {item_id} for country {user_country}")
                    continue

                filtered.append((item_id, score))

        return filtered


class BoostPromotionalItemsRule(BusinessRule):
    """Boost items that are on promotion"""

    def __init__(self, boost_factor: float = 1.5):
        super().__init__("boost_promotional", RuleType.BOOST, priority=50)
        self.boost_factor = boost_factor

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """Boost promotional items"""

        boosted = []
        for item_id, score in recommendations:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                is_promotional = item.features.get("is_promotional", False)
                promo_end = item.features.get("promo_end_date")

                # Check if promotion is active
                if is_promotional:
                    if promo_end:
                        promo_end_date = datetime.fromisoformat(promo_end)
                        if datetime.utcnow() <= promo_end_date:
                            score *= self.boost_factor
                            logger.debug(f"Boosted promotional item {item_id}")
                    else:
                        score *= self.boost_factor
                        logger.debug(f"Boosted promotional item {item_id}")

            boosted.append((item_id, score))

        return boosted


class BoostNewItemsRule(BusinessRule):
    """Boost recently added items"""

    def __init__(self, days_threshold: int = 7, boost_factor: float = 1.3):
        super().__init__("boost_new_items", RuleType.BOOST, priority=40)
        self.days_threshold = days_threshold
        self.boost_factor = boost_factor

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """Boost new items"""

        threshold_date = datetime.utcnow() - timedelta(days=self.days_threshold)

        boosted = []
        for item_id, score in recommendations:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item and item.created_at >= threshold_date:
                score *= self.boost_factor
                logger.debug(f"Boosted new item {item_id}")

            boosted.append((item_id, score))

        return boosted


class BoostPersonalizedPreferencesRule(BusinessRule):
    """Boost items matching user's explicit preferences"""

    def __init__(self, boost_factor: float = 1.4):
        super().__init__("boost_preferences", RuleType.BOOST, priority=60)
        self.boost_factor = boost_factor

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """Boost items matching user preferences"""

        favorite_categories = user.preferences.get("favorite_categories", [])
        favorite_tags = user.preferences.get("favorite_tags", [])

        if not favorite_categories and not favorite_tags:
            return recommendations

        boosted = []
        for item_id, score in recommendations:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                boost = 1.0

                # Boost for category match
                if item.category in favorite_categories:
                    boost *= self.boost_factor
                    logger.debug(f"Boosted item {item_id} for category match")

                # Boost for tag match
                if item.tags and any(tag in favorite_tags for tag in item.tags):
                    boost *= 1.2
                    logger.debug(f"Boosted item {item_id} for tag match")

                score *= boost

            boosted.append((item_id, score))

        return boosted


class DiversityRule(BusinessRule):
    """Ensure diversity in recommendations (different categories)"""

    def __init__(self, max_per_category: int = 3):
        super().__init__("diversity", RuleType.RERANK, priority=20)
        self.max_per_category = max_per_category

    def apply(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Dict[str, Any],
        db: Session
    ) -> List[Tuple[int, float]]:
        """Ensure diversity by limiting items per category"""

        category_counts = {}
        diversified = []
        skipped = []

        for item_id, score in recommendations:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                category = item.category or "uncategorized"
                count = category_counts.get(category, 0)

                if count < self.max_per_category:
                    diversified.append((item_id, score))
                    category_counts[category] = count + 1
                else:
                    skipped.append((item_id, score))

        # Add skipped items at the end if space allows
        diversified.extend(skipped)

        if skipped:
            logger.debug(f"Applied diversity rule: reordered {len(skipped)} items")

        return diversified


class BusinessRulesEngine:
    """
    Main engine for applying business rules to recommendations
    """

    def __init__(self, db: Session):
        self.db = db
        self.rules: List[BusinessRule] = []
        self._load_default_rules()

    def _load_default_rules(self):
        """Load default business rules"""

        # Filter rules
        self.add_rule(FilterOutOfStockRule())
        self.add_rule(FilterAlreadyPurchasedRule())
        self.add_rule(FilterAgeRestrictedRule())
        self.add_rule(FilterGeoRestrictedRule())

        # Boost rules
        self.add_rule(BoostPromotionalItemsRule(boost_factor=1.5))
        self.add_rule(BoostNewItemsRule(days_threshold=7, boost_factor=1.3))
        self.add_rule(BoostPersonalizedPreferencesRule(boost_factor=1.4))

        # Rerank rules
        self.add_rule(DiversityRule(max_per_category=3))

    def add_rule(self, rule: BusinessRule):
        """Add a business rule"""
        self.rules.append(rule)
        # Sort by priority (descending)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added business rule: {rule.name} (priority: {rule.priority})")

    def remove_rule(self, rule_name: str):
        """Remove a business rule by name"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Removed business rule: {rule_name}")

    def apply_rules(
        self,
        recommendations: List[Tuple[int, float]],
        user: User,
        context: Optional[Dict[str, Any]] = None,
        rule_types: Optional[List[RuleType]] = None
    ) -> List[Tuple[int, float]]:
        """
        Apply all business rules to recommendations

        Args:
            recommendations: List of (item_id, score) tuples
            user: User object
            context: Additional context
            rule_types: Optional filter for rule types to apply

        Returns:
            Filtered and modified recommendations
        """
        context = context or {}

        logger.info(f"Applying business rules to {len(recommendations)} recommendations")

        result = recommendations
        rules_applied = 0

        for rule in self.rules:
            # Skip if rule type filter is specified and doesn't match
            if rule_types and rule.rule_type not in rule_types:
                continue

            try:
                before_count = len(result)
                result = rule.apply(result, user, context, self.db)
                after_count = len(result)

                rules_applied += 1

                if before_count != after_count:
                    logger.debug(
                        f"Rule '{rule.name}' changed count: {before_count} -> {after_count}"
                    )

            except Exception as e:
                logger.error(f"Error applying rule '{rule.name}': {e}", exc_info=True)
                # Continue with other rules

        # Re-sort by score after boosting
        result.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            f"Applied {rules_applied} business rules. "
            f"Recommendations: {len(recommendations)} -> {len(result)}"
        )

        return result

    def get_rules_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all active rules"""
        return [
            {
                "name": rule.name,
                "type": rule.rule_type.value,
                "priority": rule.priority
            }
            for rule in self.rules
        ]


# Optional import
from typing import Optional
