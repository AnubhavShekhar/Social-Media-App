"""
tests/test_votes.py
 
Coverage for POST /vote.
 
The vote endpoint is a toggle: dir=1 adds a vote, dir=0 removes one.
All mutations require authentication.
"""
import uuid

from httpx import AsyncClient

#------- Helper ------------------------------------------------------

async def cast_vote(client, post_id, direction: int):
    """Thin wrapper so tests stay readable"""
    return await client.post("/vote/", json={
        "post_id": str(post_id),
        "dir": direction,
    })

class TestVote:
    async def test_vote_on_post(self, auth_client: AsyncClient, persist_post):
        """First vote on a post (dir=1) returns 201"""
        post = await persist_post()
        response = await cast_vote(auth_client, post.id, 1)
        assert response.status_code == 201

    async def test_vote_increments_vote_count(self, auth_client: AsyncClient, persist_post):
        """
        After voting, GET /posts/{id} must show votes == 1
        Confirms the vote was actually written to the DB, not just acknowledged
        """
        post = await persist_post()
        await cast_vote(auth_client, post.id, 1)

        response = await auth_client.get(f"/posts/{post.id}")
        assert response.status_code == 200
        assert response.json()['votes'] == 1

    async def test_duplicate_vote(self, auth_client: AsyncClient, persist_post):
        """
        Voting twice on the same post (dir=1 twice) returns 409 conflict
        The second vote should be rejected not silently ignored
        """

        post = await persist_post()
        await cast_vote(auth_client, post.id, 1)
        response = await cast_vote(auth_client, post.id, 1)
        assert response.status_code == 409

    async def test_unvote(self, auth_client: AsyncClient, persist_post):
        """
        dir=0 on a post the user has already voted on returns 200
        and remove the vote
        """
        post = await persist_post()
        await cast_vote(auth_client, post.id, 1)
        response = await cast_vote(auth_client, post.id, 0)
        assert response.status_code == 201

    async def test_unvote_decrements_vote_count(self, auth_client: AsyncClient, persist_post):
        """After voting then unvoting the vote count must return 0"""
        post = await persist_post()
        await cast_vote(auth_client, post.id, 1)
        await cast_vote(auth_client, post.id, 0)
        
        response = await auth_client.get(f"/posts/{post.id}")
        assert response.status_code == 200
        assert response.json()['votes'] == 0

    async def test_unvote_without_existing_vote(self, auth_client: AsyncClient, persist_post):
        """
        dir=0 when the user has not voted returns 409
        There is no vote row to delete - this is a conflict, not a 404
        because the post exists but the vote state is wrong
        """
        post = await persist_post()
        response = await cast_vote(auth_client, post.id, 0)
        assert response.status_code == 409

    async def test_vote_on_nonexistent_post(self, auth_client: AsyncClient):
        """Voting on a UUID that has no corresponding post returns 404"""
        response = await cast_vote(auth_client, uuid.uuid4(), 1)
        assert response.status_code == 404

    async def test_unauthenticated_vote(self, client: AsyncClient, persist_post):
        """No token -> returns 401 before any DB logic runs"""
        post = await persist_post()
        response = await cast_vote(client, post.id, 1)
        assert response.status_code == 401

    async def test_two_users_can_vote_on_same_post(self, auth_client: AsyncClient, auth_client_2: AsyncClient, persist_post):
        """
        Votes are per (user, post) pair - two different users voting on the
        same post must each succeed and count must reach 2
        """
        post = await persist_post()
        r1 = await cast_vote(auth_client, post.id, 1)
        r2 = await cast_vote(auth_client_2, post.id, 1)
        assert r1.status_code == 201
        assert r2.status_code == 201

        response = await auth_client.get(f"/posts/{post.id}")
        assert response.json()['votes'] == 2

    async def test_user_can_vote_on_own_post(self, auth_client: AsyncClient, persist_post):
        """
        Voting on own post returns 201
        """
        post = await persist_post()
        response = await cast_vote(auth_client, post.id, 1)
        assert response.status_code == 201