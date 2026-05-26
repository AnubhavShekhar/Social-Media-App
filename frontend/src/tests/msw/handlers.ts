import { http, HttpResponse } from "msw";

const BASE = "http://localhost:8000";

export const handlers = [
    // POST /login - receives application/x-www-from-urlencoded
    http.post(`${BASE}/login`, () =>
    HttpResponse.json({
        access_token: "fake_jwt_token",
        token_type: "bearer",
        expires_in: 1800,
        })
    ),

    // POST /users (signup)
    http.post(`${BASE}/users`, () =>
        HttpResponse.json(
            {
                id: "user-uuid-1",
                email: "test@example.com",
                created_at: new Date().toISOString(),
            },
            { status: 201 }
        )
    ),

    // GET /users/me
    http.get(`${BASE}/users/me`, () =>
    HttpResponse.json({
        id: "user-uuid-1",
        email: "test@example.com",
        created_at : new Date().toISOString(),
        })
    ),

    // POST /vote
    http.post(`${BASE}/vote`, () =>
        HttpResponse.json({ message: "vote added"}, {status: 201})
    ),

    // PATCH /posts/:id
    http.patch(`${BASE}/posts/:id`, () =>
        HttpResponse.json({
            id: "post-uuid-1",
            title: "Updated Title",
            content: "Updated content",
            published: true,
            created_at : new Date().toISOString(),
            user_id : "user-uuid-1",
            image_url: null,
            owner: {
                email: "test@example.com",
                created_at: new Date().toISOString(),
            },
        })
    ),

    // DELETE /posts/:id
    http.delete(`${BASE}/posts/:id`, () =>
        new HttpResponse(null, { status : 204 })
    )
]