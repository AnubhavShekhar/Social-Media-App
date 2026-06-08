from email.policy import HTTP

from fastapi import HTTPException, status, APIRouter, Response
from app.schemas import UserCreate, UserResponse, UserWithPostsResponse
from app.utils import hash_password
from psycopg import errors
from psycopg.rows import dict_row
from app.database import DBConn
from app.dependencies import CurrentUser
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import DBSession
from app.models import User, Post
from uuid import UUID
import logging

logger = logging.getLogger("app.users")

router = APIRouter(prefix='/users', tags=['Users'])


@router.post('', status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(user: UserCreate, conn: DBConn):
    logger.info("create_user_requested email=%s", user.email)
    hashed_password = hash_password(user.password)

    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql
                                INSERT INTO users 
                                (email, password) 
                                VALUES (%s, %s)
                                RETURNING *
                                """, (user.email, hashed_password),
                            )
            
            new_user = await cur.fetchone()
            await conn.commit()

            if new_user:
                logger.info("create_user_succeeded user_id=%s email=%s", new_user['id'], user.email)
    
        return new_user
    
    except errors.UniqueViolation:
        await conn.rollback()
        logger.warning("create_user_conflict email=%s", user.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    except Exception:
        await conn.rollback()
        logger.exception("create_user_failed email=%s", user.email)
        raise


@router.get('/me', response_model=UserResponse)
async def read_current_user(user: CurrentUser):
    logger.info("read_current_user_succeeded user_id=%s", user['id'])
    return user

@router.get('/{id}', response_model=UserResponse)
async def get_user(id: UUID, conn: DBConn):
    logger.info("get_user_requested user_id=%s", id)

    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql
                            SELECT * FROM users WHERE id = %s
                            """, (id, ))
            user = await cur.fetchone()

            if user is None:
                logger.warning("get_user_not_found user_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"user with id {id} not found"
                )
            
            logger.info("get_user_succeeded user_id=%s", id)
            return user
    
    except HTTPException:
        raise
    except Exception:
        logger.exception("get_user_failed user_id=%s", id)
        raise

@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(id: UUID, conn: DBConn, user: CurrentUser):
    logger.info("delete_user_requested user_id=%s", id)

    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql
                              SELECT * FROM users where id = %s
                              """, (id, ))
            db_user = await cur.fetchone()

            if db_user is None:
                logger.warning("delete_user_not_found user_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"user with id : {id} not found"
                )

            if user['id'] != id:
                logger.warning("delete_user_forbidden user_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Unauthorized to perform this request"
                )
            
            await cur.execute("""--sql
                            DELETE FROM users WHERE id = %s
                            """, (id, ))
            await conn.commit()

            if cur.rowcount <= 0:
                logger.warning("delete_user_not_found_after_delete user_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"user with id : {id} not found"
                )
            
            logger.info("delete_user_succeeded user_id=%s", id)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    except HTTPException:
        raise
    except Exception:
        await conn.rollback()
        logger.exception("delete_user_failed user_id=%s", id)
        raise 
            


@router.get('/userposts/{id}', response_model=UserWithPostsResponse)
async def get_user_posts(id : UUID, session: DBSession):
    logger.info("get_user_posts_requested user_id=%s", id)

    try:
        result = await session.execute(
            select(User)
            .where(User.id == id)
            .options(selectinload(User.posts))
        )

        user = result.scalar_one_or_none()

        if user is None:
            logger.warning("get_user_posts_not_found user_id=%s", id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No posts found for user with id :{id}"
            )
        
        logger.info("get_user_posts_succeeded user_id=%s post_count=%s", id, len(user.posts))
        return user
    
    except HTTPException:
        raise
    except Exception:
        logger.exception("get_user_posts_failed user_id=%s", id)
        raise
