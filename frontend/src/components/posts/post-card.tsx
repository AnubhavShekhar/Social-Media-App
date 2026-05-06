"use client";

import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { Heart, Pencil, Trash2, MoreHorizontal } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { vote, deletePost } from "@/lib/api";
import type { Post } from "@/lib/api";
import {
    Card,
    CardContent,
    CardFooter,
    CardHeader,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

// -------- Props -----------------------------------------------------

interface PostCardProps {
    post : Post;
    onEdit: (post: Post) => void;
    onDeleted: (postId: string) => void;
}

// ------- Component ---------------------------------------------------

export default function PostCard ({ post, onEdit, onDeleted }: Readonly<PostCardProps>) {
    const { user } = useAuth();
    const isOwner = user?.id === post.owner.id;

    //----- Vote state -----------------------------------------
    const [hasVoted, setHasVoted] = useState(false);
    const[voteCount, setVoteCount] = useState(post.votes);
    const [voteLoading, setVoteLoading] = useState(false);

    //----- Delete state -------------------------------------
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [deleteLoading, setDeleteLoading] = useState(false);

    //----- Handlers -----------------------------------------
    async function handleVote() {
        if (voteLoading) return;
        const newHasVoted = !hasVoted;
        const dir = newHasVoted ? 1 : 0;

        // Optimistic update - update UI immediately before API call
        setHasVoted(newHasVoted);
        setVoteCount((prev) => prev + (newHasVoted ? 1 : -1));
        setVoteLoading(true);

        try {
            await vote(post.post.id, dir as 0 | 1);
        } catch {
            // Revert on failure
            setHasVoted(!newHasVoted);
            setVoteCount((prev) => prev + (newHasVoted ? -1 : 1));
        } finally {
            setVoteLoading(false);
        }
    }

    async function handleDelete() {
        setDeleteLoading(true);
        try {
            await deletePost(post.post.id);
            onDeleted(post.post.id);
        } catch {
            setDeleteLoading(false);
            setShowDeleteDialog(false);
        }
    }

    // ---------- Render -------------------------------------------------

    return (
        <>
            <Card>
                {/* Header - avatar, author, time, owner actions */}
                <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0 pb-3">
                    <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                            <AvatarFallback className="text-xs">
                                {post.owner.email[0].toUpperCase()}
                            </AvatarFallback>
                        </Avatar>
                        <div className="flex flex-col">
                            <span className="text-sm font-medium">
                                {post.owner.email}
                            </span>
                            <span className="text-xs text-muted-foreground">
                                {formatDistanceToNow(new Date(post.post.created_at), {addSuffix: true,})}
                            </span>
                        </div>
                    </div>

                    {/* Edit / delete dropdown - only visible to post owner */}
                    {isOwner && (
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button 
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 text-muted-foreground"
                                >
                                    <MoreHorizontal size={16}/>
                                    <span className="sr-only">Post options</span>
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuItem 
                                    onClick={() => onEdit(post)}
                                    className="gap-2 cursor-pointer"
                                >
                                    <Pencil size={14}/>
                                    Edit post 
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={() => setShowDeleteDialog(true)}
                                    className="gap-2 cursor-pointer text-destructive focus:text-destructive"
                                >
                                    <Trash2 size={14}/>
                                    Delete post
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    )}
                </CardHeader>

                {/* Body - title and content */}
                <CardContent className="pb-3">
                    <h2 className="text-base font-semibold mb-1">
                        {post.post.title}
                    </h2>
                    <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                        {post.post.content}
                    </p>

                    {/* Image- shown if present */}
                    {post.post.image_url && (
                        <div className="mt-3 rounded-md overflow-hidden border border-border">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                                src={post.post.image_url}
                                alt={post.post.title}
                                className="w-full object-cover max-h-96"
                            />
                        </div>
                    )}
                </CardContent>

                {/* Footer - vote button */}
                <CardFooter className="pt-0">
                    <button 
                        onClick={handleVote}
                        disabled={voteLoading}
                        className={cn(
                            "flex items-center gap-1.5 text-sm transition-colors",
                            hasVoted
                                ? "text-red-500"
                                : "text-muted-foreground hover:text-red-500"
                        )}
                        aria-label={hasVoted ? "Remove vote" : "Vote"}
                    >
                        <Heart  
                            size={16}
                            className={cn(
                                "transition-all",
                                hasVoted && "fill-red-500"
                            )}
                        />
                        <span>{voteCount}</span>
                    </button>
                </CardFooter>
            </Card>

            {/* Delete confirmation dialog */}
            <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete post?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete your post. This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={deleteLoading}>
                            Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDelete}
                            disabled={deleteLoading}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {deleteLoading ? "Deleting..." : "Delete"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}