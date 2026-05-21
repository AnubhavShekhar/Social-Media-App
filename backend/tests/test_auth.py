from httpx import AsyncClient

class TestSignup:
    """Tests for POST /users - user registration"""

    async def test_signup_success(self, client: AsyncClient):
        """A new user can register with valid email and password"""
        response = await client.post("/users/", json={
            "email" : "newuser@example.com",
            "password" : "securepassword123",
        }) 
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "created_at" in data
        assert "password" not in data

    async def test_signup_duplicate_email(self, client: AsyncClient, test_user):
        """Registering with an already existing email returns 409"""
        response = await client.post("/users/", json={
            "email" : test_user.email,
            "password" : "somepassword123",
        })
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    async def test_signup_invalid_email(self, client: AsyncClient):
        """Registering with an invalid email format return 422"""
        response = await client.post("/users/", json={
            "email" : "notanemail",
            "password" : "securepassword123",
        })
        assert response.status_code == 422
    
    async def test_signup_missing_email(self, client:AsyncClient):
        """Registering without a email returns 422"""
        response = await client.post("/users/", json={
            "password": "somepassword123",
        })
        assert response.status_code == 422

    async def test_signup_empty_email(self, client:AsyncClient):
        """Registering with an empty email returns 422"""
        response = await client.post("/users/", json={
            "email" : "",
            "password" : "securepassword123",
        })
        assert response.status_code == 422

    async def test_signup_missing_password(self, client: AsyncClient):
        """Registering without a password returns 422"""
        response = await client.post("/users/", json={
            "email" : "newuser@example.com"
        })
        assert response.status_code == 422
    
    async def test_signup_empty_password(self, client: AsyncClient):
        """Registering with an empty password returns 422"""
        response = await client.post("/users/", json={
            "email" : "newuser@example.com",
            "password" : "",
        })
        assert response.status_code == 422

class TestLogin:
    """Tests for POST /login - user authentication"""

    async def test_login_success(self, client: AsyncClient, test_user):
        """A registered user can log in with the correct credentials"""
        response = await client.post("/login/", data={
            "username" : test_user.email,
            "password" : "testpassword123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Logging in with a wrong password returns 401"""
        response = await client.post("/login/", data={
            "username" : test_user.email,
            "password" : "wrongpassword",
        })
        assert response.status_code == 401
        assert "invalid credentials" in response.json()['detail'].lower()

    async def test_login_noexistent_email(self, client: AsyncClient):
        """Logging in with an email that doesn't exist returns 401"""
        response = await client.post("/login/", data={
            "username" : "nobody@example.com",
            "password" : "somepassword123",
        })
        assert response.status_code == 401

    async def test_login_missing_password(self, client: AsyncClient, test_user):
        """Logging in without a password returns 422"""
        response = await client.post("/login/", data={
            "username" : test_user.email,
        })
        assert response.status_code == 422

    async def test_login_missing_email(self, client: AsyncClient):
        """Logging in without a email returns 422"""
        response = await client.post("/login/", data={
            "password" : "somepassword123",
        })
        assert response.status_code == 422

class TestProtectedRoutes:
    """Tests for routes that require authentication"""

    async def test_access_protected_route_without_token(self, client: AsyncClient):
        """Accessing a protected route without a token returns 401"""
        response = await client.get("/users/me")
        assert response.status_code == 401

    async def test_access_protecected_route_with_invalid_token(self, client: AsyncClient):
        """Accessing a protected route with an invalid token returns 401"""
        response = await client.get("/users/me", headers={
            "Authorization": "Bearer invalidtoken"
        })
        assert response.status_code == 401
        
    async def test_access_protected_route_with_valid_token(self, auth_client: AsyncClient, test_user):
        """Accessing a protected route with a valid token returns 200"""
        response = await auth_client.get("/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == test_user.email