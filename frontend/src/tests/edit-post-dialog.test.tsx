import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import type { Post } from "@/lib/api";

import EditPostDialog from "@/components/posts/edit-post-dialog";

// --- Test data ----------------------------------------------------------

const OWNER = {
    id: "user-uuid-1",
    email: "owner@example.com",
    created_at: new Date().toISOString(),
};

const TEST_POST: Post = {
    post: {
        id: "post-uuid-1",
        title: "Original Title",
        content: "Original content",
        created_at: new Date().toISOString(),
        published: true,
    },
    owner: OWNER,
    votes: 3,
};

describe("EditPostDialog", () => {
    const onOpenChange = vi.fn();
    const onSaved = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    // --- Rendering -------------------------------------------------------

    it("renders nothing when post is null", () => {
        render(
            <EditPostDialog
                post={null}
                open={true}
                onOpenChange={onOpenChange}
                onSaved={onSaved}
            />
        );
        // Dialog header renders but the form should not
        expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
        expect(screen.queryByLabelText("Content")).not.toBeInTheDocument();
    });

    it("renders title and content fields pre-filled with post data", () => {
        render(
            <EditPostDialog
                post={TEST_POST}
                open={true}
                onOpenChange={onOpenChange}
                onSaved={onSaved}
            />
        );
        expect(screen.getByLabelText("Title")).toHaveValue("Original Title");
        expect(screen.getByLabelText("Content")).toHaveValue("Original content");
    });

    it("does not render when open is false", () => {
        render(
            <EditPostDialog
                post={TEST_POST}
                open={false}
                onOpenChange={onOpenChange}
                onSaved={onSaved}
            />
        );
        expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
    });

    // --- Successful save -------------------------------------------------

    it("calls onSaved and closes dialog on successful submit", async () => {
        const user = userEvent.setup();
        render(
            <EditPostDialog
                post={TEST_POST}
                open={true}
                onOpenChange={onOpenChange}
                onSaved={onSaved}
            />
        );

        await user.clear(screen.getByLabelText("Title"));
        await user.type(screen.getByLabelText("Title"), "Updated Title");
        await user.click(screen.getByRole("button", { name: /save changes/i }));

        await waitFor(() => {
            expect(onSaved).toHaveBeenCalledWith(
                expect.objectContaining({ title: "Updated Title" })
            );
            expect(onOpenChange).toHaveBeenCalledWith(false);
        });
    });

it("shows loading state while saving", async () => {
    server.use(
        http.patch("http://localhost:8000/posts/:id", async () => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            return HttpResponse.json({
                id: "post-uuid-1",
                title: "Updated Title",
                content: "Updated content",
                published: true,
                created_at: new Date().toISOString(),
                user_id: "user-uuid-1",
                image_url: null,
                owner: { email: "test@example.com", created_at: new Date().toISOString() },
            });
        })
    );

    const user = userEvent.setup({ delay: null });
    render(
        <EditPostDialog
            post={TEST_POST}
            open={true}
            onOpenChange={onOpenChange}
            onSaved={onSaved}
        />
    );

    const clickPromise = user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
        expect(screen.getByRole("button", { name: /saving/i })).toBeDisabled();
    });

    await clickPromise;
});
    // --- Failed save -----------------------------------------------------

    it("shows error message when save fails", async () => {
        server.use(
            http.patch("http://localhost:8000/posts/:id", () =>
                HttpResponse.json(
                    { detail: "Failed to update post" },
                    { status: 500 }
                )
            )
        );

        const user = userEvent.setup();
        render(
            <EditPostDialog
                post={TEST_POST}
                open={true}
                onOpenChange={onOpenChange}
                onSaved={onSaved}
            />
        );

        await user.click(screen.getByRole("button", { name: /save changes/i }));

        await waitFor(() => {
            expect(screen.getByText("Failed to update post")).toBeInTheDocument();
        });

        expect(onSaved).not.toHaveBeenCalled();
        expect(onOpenChange).not.toHaveBeenCalledWith(false);
    });

    it("re-enables save button after a failed save", async () => {
        server.use(
            http.patch("http://localhost:8000/posts/:id", () =>
                HttpResponse.json({ detail: "Failed to update post" }, { status: 500 })
            )
        );

        const user = userEvent.setup();
        render(
            <EditPostDialog
                post={TEST_POST}
                open={true}
                onOpenChange={onOpenChange}
                onSaved={onSaved}
            />
        );

        await user.click(screen.getByRole("button", { name: /save changes/i }));

        await waitFor(() => {
            expect(
                screen.getByRole("button", { name: /save changes/i })
            ).not.toBeDisabled();
        });
    });

    // --- Cancel ----------------------------------------------------------

    it("calls onOpenChange(false) when cancel is clicked", async () => {
        const user = userEvent.setup();
        render(
            <EditPostDialog
                post={TEST_POST}
                open={true}
                onOpenChange={onOpenChange}
                onSaved={onSaved}
            />
        );

        await user.click(screen.getByRole("button", { name: /cancel/i }));
        expect(onOpenChange).toHaveBeenCalledWith(false);
    });
});