import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_agent_identity, get_db
from app.core.database import Base
from app.main import app
from app.models.agent_credential import AgentCredentialModel

TEST_AGENT_ID = "linux-test-01"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    def override_get_agent_identity():
        return AgentCredentialModel(
            agent_id=TEST_AGENT_ID,
            platform="linux",
            description="test agent",
            key_hash="unused-in-tests",
            is_active=True,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_agent_identity] = override_get_agent_identity
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
