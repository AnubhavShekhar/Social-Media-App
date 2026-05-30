import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import type { Post } from "@/lib/api";

// ------- Mock useAuth -----------------------------------------
// PostCard uses useAuth to check if the current user is the post owner
// We expose mockUser so individual tests can swap it out

let mockUser : { id: string; email: string; created_at: string } | null = null;

vi.mock("@/lib/auth-context", () => ({
    useAuth: () => ({ user: mockUser }),
}));

// ----- Mock next/image -----------------------------------------------
// next/image does complex optmisation that doesn't work in jsdom
// We replace it with a plain <img> so image-related tests still work

vi.mock("next/image", () => ({
    default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => (
        // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
        <img {...props} />
    ),
}));

import PostCard from "@/components/posts/post-card";

// -------- Test data -------------------------------------

const OWNER = {
    id: "user-uuid-1",
    email: "owner@example.com",
    created_at: new Date().toISOString(),
};

const OTHER_USER = {
    id: "user-uuid-2",
    email: "other@example.com",
    created_at: new Date().toISOString(),
};

function makePost(overrides: Partial<Post> = {}): Post {
    return {
        post: {
            id: "post-uuid-1",
            title: "Test Post Title",
            content: "Test post content",
            created_at: new Date().toISOString(),
            published: true,
            image_url: undefined,
        },
        owner: OWNER,
        votes: 5,
        ...overrides,
    };
}

describe("PostCard", () => {
    const onEdit = vi.fn();
    const onDeleted = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        mockUser = null;
    });

    // ----------- Rendering ------------------------------------

    it("renders post title and content", () => {
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted}/>);
        expect(screen.getByText("Test Post Title")).toBeInTheDocument();
        expect(screen.getByText("Test post content")).toBeInTheDocument();
    });

    it("renders the author email", () => {
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted}/>);
        expect(screen.getByText("owner@example.com")).toBeInTheDocument();
    });

    it("renders the vote count", () => {
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted}/>);
        expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("renders image when the image_url is present", () => {
        const post = makePost({
            post: {
                id: "post-uuid-1",
                title: "Test Post Title",
                content: "Test post content",
                created_at: new Date().toISOString(),
                published: true,
                image_url: "https://ik.imagekit.io/test/photo.jpg",
            },
        });

        render(<PostCard post={post} onEdit={onEdit} onDeleted={onDeleted}/>);
        expect(screen.getByRole("img")).toHaveAttribute(
            "src",
            "https://ik.imagekit.io/test/photo.jpg"
        );
    });

    it("does not render an image when image_url is absent", () => {
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted}/>);
        expect(screen.queryByRole("img")).not.toBeInTheDocument();
    });

    //------------ Owner actions --------------------------------------

    it("shows edit/delete dropdown for post owner", () => {
        mockUser = OWNER;
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted}/>);
        expect(screen.getByRole("button", { name: /post options/i })).toBeInTheDocument();
    });

    it("hides edit/delete dropdown for non-owner", () => {
        mockUser = OTHER_USER;
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted}/>);
        expect(screen.queryByRole("button", { name: /post options/i })).not.toBeInTheDocument();
    });

    it("hides edit/delete dropdown when not logged in", () => {
        mockUser= null;
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted}/>);
        expect(screen.queryByRole("button", { name: /post options/i })).not.toBeInTheDocument();
    });

    it("calls onEdit with the post when edit is clicked", async () => {
        mockUser = OWNER;
        const user = userEvent.setup();
        const post = makePost();
        render(<PostCard post={post} onEdit={onEdit} onDeleted={onDeleted}/>);

        await user.click(screen.getByRole("button", { name: /post options/i }));
        await user.click(screen.getByText("Edit post"));

        expect(onEdit).toHaveBeenCalledWith(post);
    });

    it("opens delete confirmation dialog when delete is clicked", async () => {
        mockUser = OWNER;
        const user = userEvent.setup();
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted}/>);

        await user.click(screen.getByRole("button", { name: /post options/i }));
        await user.click(screen.getByText("Delete post"));

        expect(screen.getByText("Delete post?")).toBeInTheDocument();
        expect(screen.getByText(/permanently delete your post/i )).toBeInTheDocument();
    });

    it("calls onDeleted with post id after confirming delete", async () => {
        mockUser = OWNER;
        const user = userEvent.setup();
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted} />);
 
        await user.click(screen.getByRole("button", { name: /post options/i }));
        await user.click(screen.getByText("Delete post"));
        await user.click(screen.getByRole("button", { name: /^delete$/i }));
 
        await waitFor(() => {
            expect(onDeleted).toHaveBeenCalledWith("post-uuid-1");
        });
    });
 
    it("closes delete dialog when cancel is clicked", async () => {
        mockUser = OWNER;
        const user = userEvent.setup();
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted} />);
 
        await user.click(screen.getByRole("button", { name: /post options/i }));
        await user.click(screen.getByText("Delete post"));
        await user.click(screen.getByRole("button", { name: /cancel/i }));
 
        await waitFor(() => {
            expect(screen.queryByText("Delete post?")).not.toBeInTheDocument();
        });
    });
 
    // --- Voting ----------------------------------------------------------
 
    it("increments vote count optimistically on click", async () => {
        const user = userEvent.setup();
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted} />);
 
        await user.click(screen.getByRole("button", { name: /^vote$/i }));
        expect(screen.getByText("6")).toBeInTheDocument();
    });
 
    it("decrements vote count on second click (unvote)", async () => {
        const user = userEvent.setup();
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted} />);
 
        await user.click(screen.getByRole("button", { name: /^vote$/i }));
        await user.click(screen.getByRole("button", { name: /remove vote/i }));
        expect(screen.getByText("5")).toBeInTheDocument();
    });
 
    it("reverts vote count when API call fails", async () => {
        server.use(
            http.post("http://localhost:8000/vote", async () => {
                await new Promise((resolve) => setTimeout(resolve, 100));
                return HttpResponse.json({ detail: "Server error" }, { status: 500 });
            })
        );
 
        const user = userEvent.setup();
        render(<PostCard post={makePost()} onEdit={onEdit} onDeleted={onDeleted} />);
 
        await user.click(screen.getByRole("button", { name: /^vote$/i }));
 
        // Optimistic update fires immediately
        expect(screen.getByText("6")).toBeInTheDocument();
 
        // After API failure, reverts back
        await waitFor(() => {
            expect(screen.getByText("5")).toBeInTheDocument();
        });
    });
});