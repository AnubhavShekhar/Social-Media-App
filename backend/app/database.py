from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Request, Depends
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool    
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import logging

logger = logging.getLogger("app.database")

async def get_db_conn(request: Request) -> AsyncGenerator[AsyncConnection, None]:
    pool : AsyncConnectionPool = request.app.state.db_pool
    async with pool.connection() as conn:
        yield conn

async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory : async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session

DBConn = Annotated[AsyncConnection, Depends(get_db_conn)]       
DBSession = Annotated[AsyncSession, Depends(get_db_session)]