"""
Factory pattern
---------------
PostFactory.build(user_id=...) creates an unsaved Post ORM instance.
We persist it via `db_session.add / commit` inside an `async_post` fixture
helper rather than using the shared `test_post` conftest fixture — this keeps
each test self-contained and makes the data requirements explicit.
 
For tests that need a user (to own a post or call authenticated endpoints),
we rely on the conftest-provided `test_user` / `test_user_2` / `auth_client` /
`auth_client_2` fixtures because those users are already wired to real JWTs.
"""

import uuid
from unittest.mock import Mock, patch
from types import SimpleNamespace

from factories import PostFactory
from httpx import AsyncClient


# ---------- Helpers -------------------------------------------------------
def form(
        title: str = "Test title",
        content: str = "Test content body",
        published: str = "true",
) -> dict:
    """
    Mulitpart form dict for POST /posts
    All values are strings - multipart/form-data is text on the wire.
    httpx sends this as form fields when passed to `data=`
    """
    return {"title" : title, "content" : content, "published" : published}
    

#------------- GET /posts -------------------------------------------------

class TestGetPosts:
    async def test_returns_empty_list_when_no_posts(self, client: AsyncClient):
        """Feed is empty before any posts are created"""
        response = await client.get("/posts")
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_posts_with_correct_shape(self, client: AsyncClient, persist_post):
        """
        Creates two posts via the factory and checks that GET /posts returns
        them both with the full PostWithVotes shape.
        """
        await persist_post(title="First Post")
        await persist_post(title="Second Post")

        response = await client.get("/posts")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2

        item = data[0]
        assert set(item.keys()) >= {"post", "owner", "votes"}

        post = item["post"]
        assert set(post.keys()) >= {"id", "title", "content", "created_at", "published"}

        owner = item['owner']
        assert set(owner.keys()) >= {"id", "email", "created_at"}

        assert isinstance(item["votes"], int)

#---------GET /posts/{id} ------------------------------------------------

class TestGetPost:
    async def test_returns_correct_post(self, client, persist_post):
        """Fetching by ID returns the right post with correct field values."""
        post = await persist_post(
            title="Specific Post",
            content="Specific content",
        )
 
        response = await client.get(f"/posts/{post.id}")
        assert response.status_code == 200
 
        data = response.json()
        assert data["post"]["id"] == str(post.id)
        assert data["post"]["title"] == "Specific Post"
        assert data["post"]["content"] == "Specific content"
        assert isinstance(data["votes"], int)
 
    async def test_returns_404_for_unknown_id(self, client):
        """A UUID that exists nowhere in the DB must return 404."""
        response = await client.get(f"/posts/{uuid.uuid4()}")
        assert response.status_code == 404

#----- POST /posts ------------------------------------------------------

class TestCreatePost:
    async def test_authenticated_user_can_create_post(self, auth_client: AsyncClient):
        """
        Authenticated user creates a text-only post
        Checks status 201 and that the response matches PostResponse shape
        """

        payload = form(title="My first post", content="Hello world")
        response = await auth_client.post("/posts", data=payload)
        assert response.status_code == 201

        data = response.json()
        assert data['title'] == "My first post"
        assert data['content'] == "Hello world"
        assert data['published'] is True
        assert data.get("image_url") is None

        for field in ("id", "created_at", "user_id", "owner"):
            assert field in data, f"Missing field: {field}"

    async def test_unauthenticated_user_cannot_create_post(self, client: AsyncClient):
        """Unauthenticated user returns 401"""
        response = await client.post("/posts", data=form())
        assert response.status_code == 401

    async def test_create_post_with_image(self, auth_client: AsyncClient):
        """
        When a file is attached the backend calls ImageKit.upload_file.
        We mock that call so no real HTTP request leaves the process, then
        assert the returned post has the image_url from the mock response.
 
        Patch target: `app.routers.posts.imagekit.files.upload`
        """
        mock_result = SimpleNamespace(
        url="https://ik.imagekit.io/test/photo.png",
        file_id="ik_fake_file_id_123",
        )

        fake_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16 # minimal valid-ish PNG

        with patch("app.routers.posts.imagekit.files.upload", new=Mock(return_value=mock_result)):
            response = await auth_client.post(
                "/posts",
                data=form(title="Post with image"),
                files={"image": ("photo.png", fake_bytes, "image/png")}
            )

        assert response.status_code == 201
        assert response.json()["image_url"] == "https://ik.imagekit.io/test/photo.png"

    async def test_create_multiple_posts_have_unique_ids(self, auth_client: AsyncClient):
        """
        Creating two posts must produce two distinct UUIDs
        Regression guard against accidental ID reuse
        """
        r1 = await auth_client.post("/posts", data=form(title="Post A"))
        r2 = await auth_client.post("/posts", data=form(title="Post B"))
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()['id'] != r2.json()['id']

#-------PATCH /posts/{id} -----------------------------------------------------------

class TestUpdatePost:
    async def test_owner_can_update_own_post(self, auth_client, persist_post):
        """Owner can change title and content via PATCH."""
        post = await persist_post(
            title="Original Title",
            content="Original content",
        )
 
        response = await auth_client.patch(
            f"/posts/{post.id}",
            json={"title": "Updated Title", "content": "Updated content"},
        )
        assert response.status_code == 200
 
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated content"
        assert data["id"] == str(post.id)
 
    async def test_non_owner_cannot_update_post(self, auth_client_2, persist_post):
        """
        test_user_2 (auth_client_2) cannot update a post owned by test_user.
        403 Forbidden, not 404 — the post exists, the user just can't touch it.
        """
        post = await persist_post()
 
        response = await auth_client_2.patch(
            f"/posts/{post.id}",
            json={"title": "Stolen Title"},
        )
        print(response.json())
        assert response.status_code == 403
 
    async def test_nonexistent_post_update(self, auth_client):
        """PATCH on a UUID that doesn't exist returns 404."""
        response = await auth_client.patch(
            f"/posts/{uuid.uuid4()}",
            json={"title": "Ghost"},
        )
        print(response.json())
        assert response.status_code == 404
 
    async def test_unauthenticated_user_update_post(self, client, persist_post):
        """No token → 401 before ownership is even checked."""
        post = await persist_post()
        response = await client.patch(f"/posts/{post.id}", json={"title": "No Auth"})
        assert response.status_code == 401
 
    async def test_partial_update_preserves_other_fields(
        self, auth_client, persist_post 
    ):
        """
        Sending only `title` in a PATCH should not wipe out `content`.
        Verifies the route does a true partial update, not a full replace.
        """
        post = await persist_post(
            title="Original",
            content="Do not erase me",
        )
 
        response = await auth_client.patch(
            f"/posts/{post.id}",
            json={"title": "New Title"},
        )
        print(response.json())
        assert response.status_code == 200
        assert response.json()["content"] == "Do not erase me"

#-----DELETE /posts/{id} -----------------------------------------------------

class TestDeletePost:
    async def test_owner_can_delete_own_post(self, auth_client, persist_post):
        """
        Owner deletes their post → 204 No Content.
        Follow-up GET confirms the row is actually gone.
        """
        post = await persist_post()
 
        response = await auth_client.delete(f"/posts/{post.id}")
        assert response.status_code == 204
 
        get_response = await auth_client.get(f"/posts/{post.id}")
        assert get_response.status_code == 404
 
    async def test_non_owner_cannot_delete_post(self, auth_client_2, persist_post):
        """test_user_2 cannot delete test_user's post."""
        post = await persist_post()
        response = await auth_client_2.delete(f"/posts/{post.id}")
        assert response.status_code == 403
 
    async def test_nonexistent_post_delete(self, auth_client):
        """DELETE on a made-up UUID must return 404."""
        response = await auth_client.delete(f"/posts/{uuid.uuid4()}")
        assert response.status_code == 404
 
    async def test_unauthenticated_user_delete_post(self, client, persist_post):
        """No token → 401."""
        post = await persist_post()
        response = await client.delete(f"/posts/{post.id}")
        assert response.status_code == 401
 
    async def test_delete_post_with_image_removes_imagekit_file(
        self, auth_client, persist_post 
    ):
        """
        When deleting a post that has an image, the router must call
        imagekit.files.delete with the stored file_id.
 
        We seed a post directly with a fake image_fileid (bypassing the upload
        path entirely) then mock the delete call and assert it fires correctly.
        This is cleaner than also mocking an upload just to set up state.
        """
        post = await persist_post(
            image_url="https://ik.imagekit.io/test/photo.jpg",
            image_fileid="ik_real_file_id_789",
        )
 
        with patch(
            "app.routers.posts.imagekit.files.delete",
            new = Mock(),
        ) as mock_delete:
            response = await auth_client.delete(f"/posts/{post.id}")
 
        assert response.status_code == 204
        mock_delete.assert_called_once_with("ik_real_file_id_789")
 
    async def test_delete_post_without_image_does_not_call_imagekit(
        self, auth_client, persist_post 
    ):
        """
        Deleting a text-only post (no image_fileid) must NOT call
        imagekit.files.delete — guards against calling delete with None.
        """
        post = await persist_post(
            image_url=None,
            image_fileid=None,
        )
 
        with patch(
            "app.routers.posts.imagekit.files.delete",
            new=Mock(),
        ) as mock_delete:
            response = await auth_client.delete(f"/posts/{post.id}")
 
        assert response.status_code == 204
        mock_delete.assert_not_called()