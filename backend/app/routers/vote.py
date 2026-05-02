from fastapi import HTTPException, APIRouter, status, Depends
from app.database import DBSession
from app.models import Vote, Post
import app.schemas as schemas
from app.dependencies import CurrentUser
from sqlalchemy import select
import logging

logger = logging.getLogger("app.vote")
router = APIRouter(prefix='/vote', tags=['Vote'])


@router.post('/', status_code=status.HTTP_201_CREATED)
async def vote(vote: schemas.Vote, session: DBSession, user: CurrentUser):
    logger.info("vote_requested user_id=%s post_id=%s dir=%s", user['id'], vote.post_id, vote.dir)

    try:
    # Check if post exists in the posts table
        post_result = await session.execute(
            select(Post).where(Post.id == vote.post_id)
            )
        post = post_result.scalar_one_or_none()

        if post is None:
            logger.warning("vote_post_not_found user_id=%s post_id=%s", user['id'], vote.post_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {vote.post_id} not found"
            )

        existing_vote_result = await session.execute(
            select(Vote).where(
                Vote.post_id == vote.post_id,
                Vote.user_id == user['id']
                )
            )
        existing_vote = existing_vote_result.scalar_one_or_none()

        if vote.dir == 1:
            if existing_vote is not None:
                logger.warning("vote_conflict user_id=%s post_id=%s", user['id'], vote.post_id)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"user: {user['id']} has already voted on post : {vote.post_id}"
                )

            new_vote = Vote(
                post_id=vote.post_id,
                user_id=user['id']
                )
            session.add(new_vote)
            await session.commit()

            logger.info("vote_added user_id=%s post_id=%s", user['id'], vote.post_id)

            return {"message": "successfully added vote"}
        else:
            if not existing_vote:
                logger.warning("vote_missing_for_delete user_id=%s post_id=%s", user['id'], vote.post_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vote does not exist"
                )

            await session.delete(existing_vote)
            await session.commit()

            logger.info("vote_removed user_id=%s post_id=%s", user['id'], vote.post_id)

            return {"message": "successfully deleted vote"}

    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        logger.exception("vote_failed user_id=%s post_id=%s dir=%s", user['id'], vote.post_id, vote.dir)
        raise