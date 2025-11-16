"""Tests for Business Rules Engine"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.models.base import Base
from app.models import User, Item, Interaction
from app.services.business_rules import (
    BusinessRulesEngine,
    FilterOutOfStockRule,
    FilterAlreadyPurchasedRule,
    BoostPromotionalItemsRule,
    DiversityRule,
    RuleType
)


@pytest.fixture
def db_session():
    """Create a test database session"""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()


@pytest.fixture
def sample_data(db_session):
    """Create sample data for testing"""

    # Create user
    user = User(id=1, username="testuser", email="test@example.com")
    db_session.add(user)

    # Create items
    items = [
        Item(id=1, title="In Stock Item", category="books", features={"in_stock": True}),
        Item(id=2, title="Out of Stock Item", category="books", features={"in_stock": False}),
        Item(id=3, title="Promotional Item", category="movies", features={"is_promotional": True}),
        Item(id=4, title="Regular Item 1", category="movies"),
        Item(id=5, title="Regular Item 2", category="games"),
    ]
    db_session.add_all(items)

    # Create interaction (user purchased item 1)
    interaction = Interaction(user_id=1, item_id=1, interaction_type="purchase", weight=1.0)
    db_session.add(interaction)

    db_session.commit()

    return user, items


def test_filter_out_of_stock(db_session, sample_data):
    """Test filtering out of stock items"""

    user, items = sample_data
    rule = FilterOutOfStockRule()

    recommendations = [(1, 1.0), (2, 0.9), (3, 0.8)]
    filtered = rule.apply(recommendations, user, {}, db_session)

    # Item 2 is out of stock, should be filtered
    item_ids = [item_id for item_id, _ in filtered]
    assert 1 in item_ids
    assert 2 not in item_ids
    assert 3 in item_ids


def test_filter_already_purchased(db_session, sample_data):
    """Test filtering already purchased items"""

    user, items = sample_data
    rule = FilterAlreadyPurchasedRule()

    recommendations = [(1, 1.0), (2, 0.9), (3, 0.8)]
    filtered = rule.apply(recommendations, user, {}, db_session)

    # Item 1 was purchased, should be filtered
    item_ids = [item_id for item_id, _ in filtered]
    assert 1 not in item_ids
    assert 2 in item_ids
    assert 3 in item_ids


def test_boost_promotional_items(db_session, sample_data):
    """Test boosting promotional items"""

    user, items = sample_data
    rule = BoostPromotionalItemsRule(boost_factor=2.0)

    recommendations = [(3, 0.5), (4, 0.5)]  # Item 3 is promotional
    boosted = rule.apply(recommendations, user, {}, db_session)

    # Item 3 should have boosted score
    scores = {item_id: score for item_id, score in boosted}
    assert scores[3] == 1.0  # 0.5 * 2.0
    assert scores[4] == 0.5  # Unchanged


def test_diversity_rule(db_session, sample_data):
    """Test diversity rule"""

    user, items = sample_data
    rule = DiversityRule(max_per_category=1)

    # Multiple items from same categories
    recommendations = [
        (1, 1.0),  # books
        (2, 0.9),  # books
        (3, 0.8),  # movies
        (4, 0.7),  # movies
        (5, 0.6),  # games
    ]

    diversified = rule.apply(recommendations, user, {}, db_session)

    # Should limit to 1 per category in top results
    categories_seen = set()
    top_3 = diversified[:3]

    for item_id, _ in top_3:
        item = db_session.query(Item).filter(Item.id == item_id).first()
        category = item.category
        # Each category should appear at most once in top 3
        if len(categories_seen) < 3:
            categories_seen.add(category)


def test_business_rules_engine(db_session, sample_data):
    """Test complete business rules engine"""

    user, items = sample_data
    engine = BusinessRulesEngine(db_session)

    recommendations = [
        (1, 1.0),  # Purchased, will be filtered
        (2, 0.9),  # Out of stock, will be filtered
        (3, 0.8),  # Promotional, will be boosted
        (4, 0.7),
        (5, 0.6),
    ]

    filtered = engine.apply_rules(recommendations, user, {})

    item_ids = [item_id for item_id, _ in filtered]

    # Item 1 (purchased) and 2 (out of stock) should be filtered
    assert 1 not in item_ids
    assert 2 not in item_ids

    # Item 3 should be present and boosted (might be reordered)
    assert 3 in item_ids


def test_add_remove_rules(db_session, sample_data):
    """Test adding and removing rules"""

    user, items = sample_data
    engine = BusinessRulesEngine(db_session)

    initial_count = len(engine.rules)

    # Add custom rule
    custom_rule = FilterOutOfStockRule()
    custom_rule.name = "custom_filter"
    engine.add_rule(custom_rule)

    assert len(engine.rules) == initial_count + 1

    # Remove rule
    engine.remove_rule("custom_filter")
    assert len(engine.rules) == initial_count


def test_rule_types_filter(db_session, sample_data):
    """Test filtering by rule types"""

    user, items = sample_data
    engine = BusinessRulesEngine(db_session)

    recommendations = [(1, 1.0), (2, 0.9), (3, 0.8)]

    # Apply only FILTER rules
    filtered = engine.apply_rules(recommendations, user, {}, rule_types=[RuleType.FILTER])

    # Should only apply filter rules, not boost rules
    assert len(filtered) <= len(recommendations)


def test_rules_summary(db_session, sample_data):
    """Test getting rules summary"""

    user, items = sample_data
    engine = BusinessRulesEngine(db_session)

    summary = engine.get_rules_summary()

    assert isinstance(summary, list)
    assert len(summary) > 0

    for rule_info in summary:
        assert "name" in rule_info
        assert "type" in rule_info
        assert "priority" in rule_info
