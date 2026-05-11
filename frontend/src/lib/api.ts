const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null{
    if(globalThis.window === undefined) return null;
    return localStorage.getItem("access_token");
}

function authHeaders(): HeadersInit {
    const token = getToken();
    return token ? {Authorization : `Bearer ${token}`} : {};
}

async function request<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        ...options,
        headers: {
            "Content-Type" : "application/json",
            ...authHeaders(),
            ...options.headers,
        },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Request failed"}));
        throw new Error(err.detail ?? "Request failed");
    }
    if (res.status == 204) return undefined as T;
    return res.json();
}

// ------- Auth ----------------------------------------------------------------

export async function login(email: string, password: string){
    const body = new URLSearchParams({username: email, password});
    const res = await fetch(`${BASE}/login`, {
        method: "POST",
        headers: { "Content-Type" : "application/x-www-form-urlencoded"},
        body,
    });
    if (!res.ok){
        const err = await res.json().catch(() => ({detail : "Login failed"}));
        throw new Error(err.detail ?? "Login failed");
    }
    return res.json() as Promise<{ access_token: string; token_type:string }>;
}

export async function signup(email: string, password: string) {
    return request<void>("/users",
        { method: "POST", body: JSON.stringify({email, password})}
    );
}

// --------Posts---------------------------------------------------------------


export interface PostData {
    id: string;
    title: string;
    content: string;
    created_at: string;
    published: boolean;
    image_url?: string;
}

export interface Post {
    post: PostData;
    owner: User;
    votes: number;
}

export interface PostMutationResponse {
    id: string;
    title: string;
    content: string;
    published: string;
    created_at: string;
    user_id: string;
    image_url?: string;
    owner: {
        email: string;
        created_at: string;
    };
}

export async function getPosts(): Promise<Post[]> {
    return request<Post[]>("/posts");
}

export async function getPostsById(id: string) {
    return request<Post>(`posts/${id}`);
}

export async function createPost(data: {
    title: string;
    content: string;
    image?: File;
}){
    // Must use FormData - backend expects multipart/form-data
    // Do Not set Content-Type manually - browser sets it with the correct boundary
    const formData = new FormData();
    formData.append("title", data.title);
    formData.append("content", data.content);
    if (data.image) {
        formData.append("image", data.image);
    }

    const res = await fetch(`${BASE}/posts`, {
        method: "POST",
        headers: {
            // Only the auth header
            ...authHeaders(),
        },
        body: formData,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({detail: "Request Failed"}));
        throw new Error(err.detail ?? "Request Failed");
    }

    return res.json() as Promise<PostMutationResponse>; 
}

export async function updatePost(
    id: string,
    data: { title?: string; content?: string }
){
    return request<PostMutationResponse>(`/posts/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
    });
}

export async function deletePost(id: string) {
    return request<void>(`/posts/${id}`, { method: "DELETE"});
}

// --------Votes-----------------------------------------------------------------

export async function vote(post_id: string, dir: 0 | 1) {
    return request<{ message: string }>("/vote", {
        method: "POST",
        body: JSON.stringify({ post_id, dir }),
    });
}

// --------Users----------------------------------------------------------------

export interface User {
    id: string;
    email: string;
    created_at: string;
}
export interface UserWithPosts {
    id: string;
    email: string;
    created_at: string;
    posts: PostData[];
}

export async function getMe() {
    return request<User>("/users/me");
}

export async function deleteAccount(id: string) {
    return request<void>(`users/${id}`, { method : "DELETE" });
}

export async function getUserPosts(userId: string) {
    return request<UserWithPosts>(`/users/userposts/${userId}`);
}