from fastapi import HTTPException, status, Response, Depends, Request, APIRouter, UploadFile, File, Form
from app.schemas import Post, PostResponse, PostUpdate, PostWithVotes, PostsResponse
import app.models as models
from psycopg.rows import dict_row
from typing import List, Optional, Annotated, cast
from app.dependencies import CurrentUser
from app.database import DBConn, DBSession
from app.utils import add_owner_info
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from uuid import UUID
import logging
from pathlib import Path
from imagekitio import ImageKit
import tempfile
import os
from dotenv import load_dotenv
import aiofiles.tempfile

load_dotenv()

logger = logging.getLogger("app.posts")

router = APIRouter(prefix='/posts', tags=['Posts'])

# ------- ImageKit client ------------------------------------------

imagekit = ImageKit(
    private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"),
)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024 # 5MB

@router.get('', status_code=status.HTTP_200_OK, response_model=List[PostWithVotes])
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

async def _upload_post_image(image: UploadFile, user_id: UUID) -> tuple[str, str]:
    filename = image.filename
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image filename is missing",
        )
    
    logger.info(
        "image_upload_started user_id=%s filename=%s content_type=%s",
        user_id, filename, image.content_type,
    )

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        logger.warning(
            "image_upload_invalid_type user_id=%s content_type=%s",
            user_id, image.content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed : jpeg, png, webp, gif",
        )

    contents = await image.read()
    file_size = len(contents)
    logger.info("image_upload_read user_id=%s size_bytes=%s", user_id, file_size)

    if file_size > MAX_IMAGE_SIZE_BYTES:
        logger.warning("image_upload_too_large user_id=%s size_bytes=%s", user_id, file_size)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be under 5MB",
        )

    temp_file_path: Path | None = None

    try:
        suffix = Path(filename).suffix

        async with aiofiles.tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            await tmp.write(contents)
            temp_file_path = Path(cast(str, tmp.name))

        logger.info("image_temp_file_created user_id=%s path=%s", user_id, temp_file_path)

        upload_result = imagekit.files.upload(
            file=temp_file_path,
            file_name=filename,
            folder="/posts",
            tags=["post-image"],
        )

        uploaded_url, uploaded_fileid = upload_result.url, upload_result.file_id
        if not uploaded_url:
            logger.error("imagekit_upload_missing_url user_id=%s filename=%s", user_id, filename)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Image upload failed"
            )
        if not uploaded_fileid:
            logger.error("imagekit_upload_missing_fileid user_id=%s filename=%s", user_id, filename)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Image upload failed"
            )

        logger.info("imagekit_upload_succeeded user_id=%s url=%s", user_id, uploaded_url)
        return uploaded_url, uploaded_fileid

    except HTTPException:
        raise

    except Exception:
        logger.exception("imagekit_upload_failed user_id=%s filename=%s", user_id, filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image upload failed",
        )

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            logger.info("image_temp_file_deleted user_id=%s path=%s", user_id, temp_file_path)

@router.post('', status_code=status.HTTP_201_CREATED, response_model=PostResponse)
async def create_post(
    conn: DBConn,
    user: CurrentUser,
    title: Annotated[str, Form(...)],
    content: Annotated[str, Form(...)],
    published: Annotated[bool, Form()] = True,
    image: Annotated[UploadFile | None, File()] = None,
):
    logger.info("create_post_requested user_id=%s", user['id'])

    image_url = None
    image_fileid = None

    #-------- Upload image to ImageKit if provided --------------------------
    if image and image.filename:
        image_url, image_fileid = await _upload_post_image(image, user['id'])

    else:
        logger.info("create_post_no_image user_id=%s", user['id'])

    #----- Insert post into DB --------------------------------------

    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql
                                INSERT INTO posts
                                (title, content, published, user_id, image_url, image_fileid) 
                                VALUES (%s, %s, %s, %s, %s, %s)
                                RETURNING *
                                """, (title, content, published, user['id'], image_url, image_fileid),
                            )
            
            new_post = await cur.fetchone()
            await conn.commit()
            if new_post:
                new_post = add_owner_info(new_post, user)
                logger.info("create_post_succeeded user_id=%s post_id=%s image_url=%s", user['id'], new_post['id'], image_url)
        
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
async def update_post_partially(id: UUID, post: PostUpdate, conn: DBConn, user : CurrentUser):
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
                            SELECT user_id, image_fileid FROM posts where id = %s
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
            
            logger.info("delete_post_db_succeeded post_id=%s user_id=%s", id, user['id'])

            # ----------- Delete image from ImageKit if present ----------------------
            image_fileid = owner_query.get('image_fileid')
            if image_fileid:
                try: 
                    imagekit.files.delete(image_fileid)
                    logger.info("imagekit_delete_succeeded post_id=%s file_id=%s", id, image_fileid)
                except Exception:
                    # Log but don't fail the request - post is already deleted from DB
                    # so we don't want to return an error to the client
                    logger.exception("imagekit_delete_failed post_id=%s file_id=%s", id, image_fileid)
            
            logger.info("delete_post_succeeded post_id=%s user_id=%s", id, user['id'])
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    except HTTPException:
        raise
    except Exception:
        await conn.rollback()
        logger.exception("delete_post_failed post_id=%s user_id=%s", id, user['id'])
        raise