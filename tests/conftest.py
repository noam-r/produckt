"""
Pytest configuration and shared fixtures.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.main import app
from backend.models import Organization, User, UserRoleEnum


# Test database URL (in-memory for tests)
# Use check_same_thread=False with poolclass=StaticPool to ensure all connections
# share the same in-memory database
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine using in-memory SQLite."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Critical for in-memory SQLite in tests
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """
    Create a test database session.
    """
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(test_db):
    """
    Create a FastAPI test client with test database.
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_organization(test_db: Session):
    """Create a test organization."""
    org = Organization(name="Test Organization")
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org


@pytest.fixture
def test_user(test_db: Session, test_organization: Organization):
    """Create a test user with hashed password."""
    import bcrypt

    password = "TestPass123!"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user = User(
        email="test@example.com",
        password_hash=password_hash,
        name="Test User",
        role=UserRoleEnum.PRODUCT_MANAGER,
        organization_id=test_organization.id,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Attach plain password for testing
    user.plain_password = password

    return user


@pytest.fixture
def admin_user(test_db: Session, test_organization: Organization):
    """Create a test admin user."""
    import bcrypt

    password = "AdminPass123!"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user = User(
        email="admin@example.com",
        password_hash=password_hash,
        name="Admin User",
        role=UserRoleEnum.ADMIN,
        organization_id=test_organization.id,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Attach plain password for testing
    user.plain_password = password

    return user


@pytest.fixture
def test_client(client, test_user, test_organization):
    """
    Create an authenticated test client.

    Each test gets a fresh session created for the test user.
    """
    from backend.auth.session import session_manager

    # Create session for test user
    session = session_manager.create_session(
        user_id=test_user.id,
        email=test_user.email,
        name=test_user.name,
        role=test_user.role,
        organization_id=test_organization.id,
        organization_name=test_organization.name
    )

    # Set session cookie on client (must be named "session_id" to match Cookie dependency)
    client.cookies.set("session_id", session.session_id)

    return client


@pytest.fixture
def test_client_no_auth(client):
    """
    Create an unauthenticated test client.
    """
    return client


@pytest.fixture
def test_context(test_db: Session, test_organization: Organization, test_user):
    """Create a test organizational context."""
    from backend.models import Context

    context = Context(
        organization_id=test_organization.id,
        company_mission="Test company mission",
        strategic_objectives="Test strategic objectives",
        target_markets="Test target markets",
        competitive_landscape="Test competitive landscape",
        technical_constraints="Test technical constraints",
        version=1,
        is_current=True,
        created_by=test_user.id
    )
    test_db.add(context)
    test_db.commit()
    test_db.refresh(context)
    return context


@pytest.fixture
def test_initiative(test_db: Session, test_organization: Organization, test_user):
    """Create a test initiative."""
    from backend.models import Initiative, InitiativeStatus

    initiative = Initiative(
        title="Test Initiative",
        description="Test initiative description",
        status=InitiativeStatus.DRAFT,
        organization_id=test_organization.id,
        created_by=test_user.id,
        iteration_count=0
    )
    test_db.add(initiative)
    test_db.commit()
    test_db.refresh(initiative)
    return initiative


@pytest.fixture(autouse=True, scope="function")
def reset_session_manager():
    """
    Reset the session manager before each test to prevent state leakage.

    This runs automatically before every test (autouse=True) to ensure
    each test starts with a clean session state.
    """
    from backend.auth.session import session_manager

    # Clear all sessions before test
    session_manager._sessions.clear()

    # Yield - test runs here
    yield

    # Clean up after test
    session_manager._sessions.clear()


# Aliases for commonly used fixtures
@pytest.fixture
def organization(test_organization):
    """Alias for test_organization."""
    return test_organization


@pytest.fixture
def user(test_user):
    """Alias for test_user."""
    return test_user


@pytest.fixture
def initiative(test_initiative):
    """Alias for test_initiative."""
    return test_initiative


@pytest.fixture
def auth_headers(test_user, test_organization):
    """Create session cookie for authenticated requests."""
    from backend.auth.session import session_manager

    # Create a session for the test user
    session = session_manager.create_session(
        user_id=test_user.id,
        email=test_user.email,
        name=test_user.name,
        role=test_user.role.value,
        organization_id=test_organization.id,
        organization_name=test_organization.name
    )

    # Return cookies dict that can be used with test client
    return {"cookies": {"session_id": session.session_id}}
