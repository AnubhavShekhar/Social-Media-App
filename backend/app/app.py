from fastapi import FastAPI
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv
from .routers import posts, users, auth, vote

from app.models import Base, User, Post, Vote
import logging
from app.core.logging import configure_logging
from app.middleware.logging_middleware import RequestLoggingMiddleware
from scalar_fastapi import get_scalar_api_reference

load_dotenv()

configure_logging()
logger = logging.getLogger("app.app")

DATABASE_URL = os.getenv('DATABASE_URL')


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup_begin")

    if DATABASE_URL is None:
        logger.critical("database_url_missing")
        raise RuntimeError("DATABASE_URL is not set")

    try:
        logger.info("creating_db_pool") 

        pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=10,
            open=False,
            close_returns=True,
        )

        await pool.open()
        await pool.wait()
        logger.info("db_pool_opened")

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1;")
                await cur.fetchone()
        
        logger.info("db_healthcheck_passed")

        logger.info("creating_sqlalchemy_engine")
        sa_engine = create_async_engine(
            "postgresql+psycopg://", poolclass=NullPool, async_creator=pool.getconn, echo=False)

        session_factory = async_sessionmaker(
            bind=sa_engine, expire_on_commit=False, autoflush=False,)
        
        logger.info("sqlalchemy_session_factory_created")

        app.state.db_pool = pool
        app.state.sa_engine = sa_engine
        app.state.session_factory = session_factory
        logger.info("app_state_initialized")

        logger.info("application_startup_complete")

        yield

    except Exception:
        logger.exception("application_startup_failed")
        raise

    finally:
        logger.info("application_shutdown_begin")
        try:
            if hasattr(app.state, "sa_engine"):
                await sa_engine.dispose()
                logger.info("sqlalchemy_engine_disposed")
        except Exception:
            logger.exception("sqlalchemy_engine_dispose_failed")
        
        try:
            if hasattr(app.state, "db_pool"):
                await pool.close()
                logger.info("db_pool_closed")
        except Exception:
            logger.exception("db_pool_close_failed")
        
        logger.info("application_shutdown_complete")


app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(posts.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(vote.router)

@app.get('/')
async def root():
    logger.info("root_endpoint_called")
    return {'message': 'Welcome'}

@app.get('/scalar', include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(openapi_url=app.openapi_url, scalar_proxy_url="https://proxy.scalar.com",)
