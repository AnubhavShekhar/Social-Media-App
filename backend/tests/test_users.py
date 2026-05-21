from turtle import title
import uuid

#------- GET /users/me --------------------------------

class TestGetMe:
    async def test_current_user(self, auth_client, test_user):
        """Authenticated user gets their own profile back"""
        response = await auth_client.get("/users/me")
        assert response.status_code == 200

        data = response.json()
        assert data['id'] == str(test_user.id)
        assert data['email'] == test_user.email
        assert 'created_at' in data
        assert 'password' not in data

    async def test_unauthenticated_user(self, client):
        """No token -> 401"""
        response = await client.get("/users/me")
        assert response.status_code == 401

#-------- GET /users/{id} --------------------------------

class TestGetUser:
    async def test_get_user_by_id(self, client, test_user):
        """Public endpoint returns the correct user for a known ID"""
        response = await client.get(f"/users/{test_user.id}")
        assert response.status_code == 200

        data = response.json()
        assert data['id'] == str(test_user.id)
        assert data['email'] == test_user.email
        assert 'created_at' in data
        assert 'password' not in data

    async def test_unknown_user_id(self, client):
        """A UUID with no matching user returns 404"""
        response = await client.get(f"/users/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_does_not_require_authentication(self, client, test_user):
        """GET /users/{id} is public - unauthenticated requests must succeed"""
        response = await client.get(f"/users/{test_user.id}")
        assert response.status_code == 200

#----------- DELETE /users/{id} ------------------------------------

class TestDeleteUser:
    async def test_user_can_delete_own_account(self, auth_client, test_user):
        """
        Authenticated user deletes their own account -> 204 no content
        Follow up GET confirms the row is gone
        """
        response = await auth_client.delete(f"/users/{test_user.id}")
        assert response.status_code == 204

        get_response = await auth_client.get(f"/users/{test_user.id}")
        assert get_response.status_code == 404  

    async def test_cannot_delete_another_user(self, auth_client, test_user_2):
        """
        Authenticated user cannot delete a different user's account -> 403
        The router checks 404 first then 403, so the target user must exist
        """

        response = await auth_client.delete(f"/users/{test_user_2.id}")
        assert response.status_code == 403

    async def test_delete_nonexistent_user(self, auth_client):
        """Trying to delete a UUID that doesn't exist returns 404"""
        response = await auth_client.delete(f"/users/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_unauthenticated_user_delete(self, client, test_user):
        """No token -> 401 before any ownership check runs"""
        response = await client.delete(f"/users/{test_user.id}")
        assert response.status_code == 401

#------------- GET /users/userposts/{id} -----------------------------------

class TestGetUserPosts:
    async def test_user_with_posts(self, client, test_user, persist_post):
        """
        Creates two posts fro test_user then checks that userposts returns
        the user object with both posts embedded
        """
        await persist_post(title="First post")
        await persist_post(title="Second post")
        
        response = await client.get(f"/users/userposts/{test_user.id}")
        assert response.status_code == 200

        data = response.json()
        assert data['id'] == str(test_user.id)
        assert data['email'] == test_user.email
        assert 'password' not in data

        assert 'posts' in data
        assert len(data['posts']) == 2
        titles = {p['title'] for p in data['posts']}
        assert titles == {"First post", "Second post"}

    async def test_user_with_empty_posts(self, client, test_user):
        """
        A user with no posts should still return 200 with an empty posts list,
        not 404- the user exists, they just haven't posted yet
        """
        response = await client.get(f"/users/userposts/{test_user.id}")
        assert response.status_code == 200

        data = response.json()
        assert data['id'] == str(test_user.id)
        assert data['posts'] == []
        
    async def test_unknown_user(self, client):
        """A UUID with no matching user returns 404"""
        response = await client.get(f"/users/userposts/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_only_returns_own_posts(self, client, test_user, test_user_2, persist_post):
        """
        Posts from test_user_2 must not appear in test user's userposts
        Verifies the query filters by user_id correctly
        """
        await persist_post(title="User 1 post")
        await persist_post(user_id=test_user_2.id, title="User 2 post")

        response = await client.get(f"/users/userposts/{test_user.id}")
        assert response.status_code == 200

        titles = {p['title'] for p in response.json()['posts']}
        assert 'User 1 post' in titles
        assert 'User 2 post' not in titles

    async def test_does_not_require_authentication(self, client, test_user):
        """GET /users/userposts/{id} is public"""
        response = await client.get(f"users/userposts/{test_user.id}")
        assert response.status_code == 200