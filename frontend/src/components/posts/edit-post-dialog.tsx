"use client";

import { useState } from "react";
import { updatePost } from "@/lib/api";
import type { Post, PostMutationResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
    Dialog, 
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// ------ Props -------------------------------------------------

interface EditPostDialogProps {
    post : Post | null;
    open : boolean;
    onOpenChange: (open: boolean) => void;
    onSaved : (updated: PostMutationResponse) => void;
}

// -- Inner from - only rendered when a post is actually selected ----

interface EditFormProps {
    post: Post;
    onOpenChange: (open: boolean) => void;
    onSaved: (updated: PostMutationResponse) => void;
}

// ------ Component ----------------------------------------------

function EditForm({
    post, 
    onOpenChange,
    onSaved,
}: Readonly<EditFormProps>) {
    const [title, setTitle] = useState(post.post.title);
    const [content, setContent] = useState(post.post.content);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function handleSubmit(e: React.SubmitEvent) {
        e.preventDefault();
        if (!post) return;
        setError("");
        setLoading(true);
        try{
            const updated = await updatePost(post.post.id, {title, content});
            onSaved(updated);
            onOpenChange(false);
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("failed to update post");
            }
        } finally {
            setLoading(false);
        }
    }

    return (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <div className="grid gap-2">
                    <Label htmlFor="edit-title">Title</Label>
                    <Input 
                        id="edit-title"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        required
                        maxLength={200}
                    />
                </div>     

                <div className="grid gap-2">
                    <Label htmlFor="edit-content">Content</Label>
                    <Textarea
                        id="edit-content"
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        required
                        rows={6}
                        className="resize-none"
                    />
                </div>

                {error && (
                    <p className="text-sm text-destructive">{error}</p>
                )}

                <DialogFooter>
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={loading}
                    >
                        Cancel
                    </Button>
                    <Button type="submit" disabled={loading}>
                        {loading ? "Saving..." : "Save Changes"}
                    </Button>
                </DialogFooter>
            </form> 

    );
}

// ---- Outer dialog - controls open state and guards against null post ------

export default function EditPostDialog({
    post,
    open,
    onOpenChange,
    onSaved,
}: Readonly<EditPostDialogProps>) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Edit post</DialogTitle>
                    <DialogDescription>
                        Make changes to your post. Click save when done.
                    </DialogDescription>
                </DialogHeader>

                {post && (
                    <EditForm
                        post={post}
                        onOpenChange={onOpenChange}
                        onSaved={onSaved}
                    />
                )}
           </DialogContent>
        </Dialog>
    );
}