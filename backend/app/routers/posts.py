from email.policy import HTTP

from fastapi import HTTPException, status, Response, Depends, Request, APIRouter
from app.schemas import Post, PostResponse, PostWithVotes, PostsResponse
import app.models as models
from psycopg.rows import dict_row
from typing import List, Optional
from app.dependencies import CurrentUser
from app.database import DBConn, DBSession
from app.utils import add_owner_info
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from uuid import UUID
import logging

logger = logging.getLogger("app.posts")

router = APIRouter(prefix='/posts', tags=['Posts'])

@router.get('/', status_code=status.HTTP_200_OK, response_model=List[PostWithVotes])
async def get_posts(conn: DBConn, session: DBSession, limit: int = 15, skip: int = 0, search : Optional[str] = ''):
    # async with conn.cursor(row_factory=dict_row) as cur:
    #     pattern = f"%{search}%" if search else "%"
    #     await cur.execute("""--sql
    #                       SELECT p.*,
    #                       u.id AS owner_id,
    #                       u.email AS owner_email,
    #                       u.created_at AS owner_created_at
    #                       FROM posts as p
    #                       JOIN users as u
    #                       ON p.user_id = u.id
    #                       WHERE p.title ILIKE %s
    #                       ORDER BY p.created_at DESC
    #                       LIMIT %s
    #                       OFFSET %s
    #                       """, (pattern, limit, skip)
    #                       )
    #     posts = await cur.fetchall()
    # return posts
    logger.info("get_posts_requested limit=%s skip=%s search=%s", limit, skip, search)

    try: 
        posts_result = await session.execute(
            select(models.Post, func.count(models.Vote.post_id).label("votes"))
            .options(selectinload(models.Post.user))
            .join(models.Vote, models.Vote.post_id == models.Post.id, isouter=True)
            .group_by(models.Post.id)
            .where(models.Post.title.contains(search))
            .limit(limit)
            .offset(skip)
            )
        
        rows = posts_result.all()
        posts = [
            {
                "post" : post,
                "owner" : post.user,
                "votes" : votes, 
            }
            for post, votes in rows
        ]
        # print([post.__dict__ for post in posts])
        logger.info("get_posts_succeeded count=%s", len(posts))
        return posts

    except Exception:
        logger.exception("get_posts_failed")
        raise


@router.get('/{id}', response_model=PostWithVotes)
async def get_post(id: UUID, conn: DBConn, session : DBSession):
    # async with conn.cursor(row_factory=dict_row) as cur:
    #     await cur.execute("""--sql
    #                       SELECT * FROM posts WHERE id = %s
    #                       """, (id, )
    #                       )
    #     post = await cur.fetchone()
    logger.info("get_post_requested post_id=%s", id)

    try:
        post_result = await session.execute(
            select(models.Post, func.count(models.Vote.post_id).label("votes"))
            .options(selectinload(models.Post.user))
            .join(models.Vote, models.Vote.post_id == models.Post.id, isouter=True)
            .group_by(models.Post.id)
            .where(models.Post.id == id)
            )
        
        row = post_result.fetchone()

        if row is None:
            logger.warning("get_post_not_found post_id=%s", id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"post with id {id} not found")

        post = {
            "post" : row[0],
            "owner" : row[0].user,
            "votes" : row[1]
        }

        logger.info("get_post_succeeded post_id=%s", id)
        return post

    except HTTPException:
        raise
    except Exception:
        logger.exception("get_post_failed post_id=%s", id)
        raise 


@router.post('/', status_code=status.HTTP_201_CREATED, response_model=PostResponse)
async def create_post(post: Post, conn: DBConn, user: CurrentUser):
    logger.info("create_post_requested user_id=%s", user['id'])
    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql
                                INSERT INTO posts
                                (title, content, published, user_id) 
                                VALUES (%s, %s, %s, %s)
                                RETURNING *
                                """, (post.title, post.content, post.published, user['id']),
                            )
            
            new_post = await cur.fetchone()
            await conn.commit()
            if new_post:
                new_post = add_owner_info(new_post, user)
                logger.info("create_post_succeeded user_id=%s post_id=%s", user['id'], new_post['id'])
        
        return new_post
    
    except Exception:
        await conn.rollback()
        logger.exception("create_post_failed user_id=%s", user['id'])
        raise


@router.put('/{id}', response_model=PostResponse)
async def update_post(id: UUID, post: Post, conn: DBConn, user : CurrentUser):
    logger.info("update_post_requested post_id=%s user_id=%s", id, user["id"])

    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql 
                              SELECT user_id FROM posts where id = %s
                              """, (id,),
            )
            owner_query = await cur.fetchone()

            if owner_query is None:
                logger.warning("update_post_not_found post_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"post with id {id} not found",
                )

            if user["id"] != owner_query["user_id"]:
                logger.warning("update_post_forbidden post_id=%s user_id=%s", id, user["id"])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized to perform this request",
                )

            await cur.execute(
                """--sql
                UPDATE posts
                SET title = %s, content = %s
                WHERE id = %s
                RETURNING *
                """,
                (post.title, post.content, id),
            )

            updated_post = await cur.fetchone()
            await conn.commit()

            if cur.rowcount <= 0:
                logger.warning("update_post_not_found_after_update post_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"post with id {id} not found",
                )

            if updated_post:
                updated_post = add_owner_info(updated_post, user)

            logger.info("update_post_succeeded post_id=%s user_id=%s", id, user["id"])
            return updated_post

    except HTTPException:
        raise
    except Exception:
        await conn.rollback()
        logger.exception("update_post_failed post_id=%s user_id=%s", id, user["id"])
        raise

@router.patch('/{id}', response_model=PostResponse)
async def update_post_partially(id: UUID, post: Post, conn: DBConn, user : CurrentUser):
    logger.info("patch_post_requested post_id=%s user_id=%s", id, user['id'])

    fields = []
    values = []

    if post.title:
        fields.append("title=%s")
        values.append(post.title)

    if post.content:
        fields.append("content=%s")
        values.append(post.content)

    if not fields:
        logger.warning("patch_post_empty_payload post_id=%s user_id=%s", id, user['id'])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter data to be changed",
        ) 

    values.append(id)
    set_clause = ', '.join(fields)
    sql = f"""--sql
            UPDATE posts
            SET {set_clause}
            WHERE id = %s
            RETURNING *
            """
    
    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql
                            SELECT user_id FROM posts where id = %s
                            """, (id, ))
            owner_query = await cur.fetchone()
            
            if owner_query is None:
                logger.warning("patch_post_not_found post_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"post with id {id} not found",
                )
            if user['id'] != owner_query['user_id']:
                logger.warning("patch_post_forbidden post_id=%s user_id=%s", id, user["id"])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unathorized to perform this request",
                )

            await cur.execute(sql, values)
            updated_post = await cur.fetchone()
            await conn.commit()

            if cur.rowcount <= 0:
                logger.warning("patch_post_not_found_after_update post_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"post with id {id} not found"
                )

            if updated_post:
                updated_post = add_owner_info(updated_post, user)
                logger.info("patch_post_succeeded post_id=%s user_id=%s", id, user['id'])

            return updated_post

    except HTTPException:
        raise
    except Exception:
        await conn.rollback()
        logger.exception("patch_post_failed post_id=%s user_id=%s", id, user['id'])
        raise 


@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(id: UUID, conn: DBConn, user : CurrentUser):
    logger.info("delete_post_requested post_id=%s user_id=%s", id, user['id'])
    
    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql
                            SELECT user_id FROM posts where id = %s
                            """, (id, ))
            owner_query = await cur.fetchone()

            if owner_query is None:
                logger.warning("delete_post_not_found post_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"post with id : {id} not found",
                )
            
            if user['id'] != owner_query['user_id']:
                logger.warning("delete_post_forbidden post_id=%s user_id=%s", id, user['id'])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unathorized to perform this request"
                )

            await cur.execute("""--sql
                            DELETE FROM posts WHERE id = %s
                            """, (id, ))
            await conn.commit()

            if cur.rowcount <= 0:
                logger.warning("delete_post_not_found_after_delete post_id=%s", id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"post with id : {id} not found",
                )
            
            logger.info("delete_post_succeeded post_id=%s user_id=%s", id, user['id'])
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    except HTTPException:
        raise
    except Exception:
        await conn.rollback()
        logger.exception("delete_post_failed post_id=%s user_id=%s", id, user['id'])
        raise