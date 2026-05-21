import pytest_asyncio
import os
from httpx import AsyncClient, ASGITransport
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from app.app import app
from app.database import get_db_conn, get_db_session
from app.oauth2 import create_access_token
from app.models import User, Post
from app.utils import hash_password
import sys
import asyncio
from factories import PostFactory

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#---------Load test environment ---------------------------------
load_dotenv(".env.test", override=True)

TEST_DATABASE_URL = os.getenv("DATABASE_URL")

if TEST_DATABASE_URL is not None:
    TEST_SA_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")


#-----------Session scoped pool ---------------------------------

@pytest_asyncio.fixture(scope="session")
async def test_pool():
    """Single connection pool shared across the entire test session"""

    if TEST_DATABASE_URL is None:
        raise RuntimeError("DATABASE_URL is not set in .env.test")

    pool = AsyncConnectionPool(
        conninfo=TEST_DATABASE_URL,
        min_size=2,
        max_size=10,
        open=False,
    )
    await pool.open()
    await pool.wait()
    yield pool
    await pool.close()

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Seperate SQLAlchemy engine with its own connection pool"""
    if TEST_SA_URL is None:
        raise RuntimeError("DATABASE_URL is not set in .env.test")
    
    engine = create_async_engine(
        TEST_SA_URL,
        poolclass=NullPool,
        echo=False,
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    """SqlAlchemy session factory using its own engine"""
    factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    yield factory

# ── Table cleanup between tests ───────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def cleanup(test_pool):
    """
    Truncates all tables after every test automatically.
    autouse=True means this runs for every test without needing to request it.
    Runs AFTER the test (yield comes first, cleanup after).
    """
    yield
    async with test_pool.connection() as conn:
        await conn.execute("""
            TRUNCATE TABLE votes, posts, users
            RESTART IDENTITY CASCADE
        """)
        await conn.commit()

#-----Per-test fixtures----------------------------------------------

@pytest_asyncio.fixture
async def db_conn(test_pool):
    """Per-test psycopg connection with automatic rollback"""
    async with test_pool.connection() as conn:
        yield conn

@pytest_asyncio.fixture
async def db_session(test_session_factory):
    """Per-test SQLAlchemy session with automatic rollback"""
    async with test_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

#------HTTP Client---------------------------------------------------

@pytest_asyncio.fixture
async def client(db_conn, db_session, test_pool, test_session_factory):
    """AsyncClient with test database dependencies injected"""

    async def override_get_db_conn():
        yield db_conn

    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_conn] = override_get_db_conn
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    app.state.db_pool = test_pool
    app.state.session_factory = test_session_factory

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

#-----Test users ----------------------------------------------------

@pytest_asyncio.fixture
async def test_user(db_session):
    """A real user in the test database"""
    user = User(
        email="testuser@example.com",
        password=hash_password("testpassword123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def test_user_2(db_session):
    """A second user for authorization tests"""
    user = User(
        email = "testuser2@example.com",
        password = hash_password("testpassword2123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

# ------- JWT tokens -------------------------------------------------

@pytest_asyncio.fixture
async def token(test_user):
    """Real JWT token for test_user"""
    access_token, _ = create_access_token(data={"user_id": str(test_user.id)})
    return access_token

@pytest_asyncio.fixture
async def token2(test_user_2):
    """Real JWT token for test_user_2"""
    access_token, _ = create_access_token(data={"user_id" : str(test_user_2.id)})
    return access_token

#-------- Authenticated clients ------------------------------------

@pytest_asyncio.fixture
async def auth_client(client, token):
    """AsyncClient pre-configured with auth headers for test_user"""
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client

@pytest_asyncio.fixture
async def auth_client_2(client, token2):
    """AsyncClient pre-configured with auth headers for test_user_2"""
    client.headers.update({"Authorization" : f"Bearer {token2}"})
    return client

# -------- Test post -----------------------------------------------

@pytest_asyncio.fixture
async def test_post(db_session, test_user):
    """A real post owned by test_user"""
    post = Post(
        title = "Test Post",
        content = "Test Content",
        published = True,
        user_id = test_user.id,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post

@pytest_asyncio.fixture
async def persist_post(db_session, test_user):
    """
    Returns an async callable that builds and persists a Post via PostFactory

    Defaults user_id to test_user.id - overrie any field via kwargs
    """
    async def _persist(**kwargs):
        kwargs.setdefault("user_id", test_user.id)
        post = PostFactory.build(**kwargs)
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)
        return post
    
    return _persist