"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getPosts } from "@/lib/api";
import type { Post, PostMutationResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import AppSidebar from "@/components/nav/sidebar";
import PostCard from "@/components/posts/post-card";
import EditPostDialog from "@/components/posts/edit-post-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

// ----- Loading skeleton -----------------------------------

function PostSkeleton() {
    return (
        <div className="flex flex-col gap-3 p-4 border border-border rounded-lg">
            <div className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-full"/>
                <div className="flex flex-col gap-1">
                    <Skeleton className="h-3 w-32"/>
                    <Skeleton className="h-3 w-20"/>
                </div>
            </div>
            <Skeleton className="h-4 w-3/4"/>
            <Skeleton className="h-16 w-full"/>
        </div>
    );
}


// -------- Page ----------------------------------------------

export default function HomePage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();

    const [posts, setPosts] = useState<Post[]>([]);
    const [postsLoading, setPostsLoading] = useState(true);
    const [error, setError] = useState("");

    // edit dialog state
    const [editingPost, setEditingPost] = useState<Post | null>(null);
    const [editOpen, setEditOpen] = useState(false);

    // ----- Auth guard -----------------------------------------
    useEffect(() => {
        if (!authLoading && !user){
            router.replace("/login");
        }
    }, [user, authLoading, router]);

    //----- Fetch posts ------------------------------------------
    const fetchPosts = useCallback(async () => {
        setPostsLoading(true);
        setError("");
        try {
            const data = await getPosts();
            setPosts(data);
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to load posts");
            }
        } finally {
            setPostsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!user) return;
        
        async function loadPosts() {
            await fetchPosts();
        }

        loadPosts();
    }, [user, fetchPosts]);

    // ------ Post handlers ---------------------------------

    function handleEdit(post: Post) {
        setEditingPost(post);
        setEditOpen(true);
    }

    function handleDeleted(postId: string) {
        setPosts((prev) => prev.filter((p) => p.post.id !== postId));
    }

    function handleSaved(updated: PostMutationResponse) {
        setPosts((prev) =>
            prev.map((p) => {
                if (p.post.id !== updated.id) return p;
                return {
                    ...p,
                    post: {
                        ...p.post,
                        title: updated.title,
                        content: updated.content,
                    },
                };
            })
        );
    }

    // ---- Render -------------------------------------

    if (authLoading) return null;

    return (
        <SidebarProvider>
            <AppSidebar/>
            <SidebarInset>
                {/* Top bar */}
                <header className="flex items-center gap-2 px-4 py-3 border-b border-border">
                    <SidebarTrigger/>
                    <Separator orientation="vertical" className="h-4"/>
                    <span className="text-sm font-medium">Feed</span>
                </header>

                {/* Feed */}
                <main className="flex flex-col gap-4 p-4 max-w-2x1 mx-auto w-full">
                    {/* Loading skeletons */}
                    {postsLoading && (
                        <>
                            <PostSkeleton />
                            <PostSkeleton />
                            <PostSkeleton /> 
                        </>
                    )}

                    {/* Error state */}
                    {!postsLoading && error && (
                        <div className="text-center py-12">
                            <p className="text-sm text-destructive">{error}</p>
                            <button 
                                onClick={fetchPosts}
                                className="mt-2 text-sm text-muted-foreground hover:text-foreground underline">
                                    Try again
                                </button>
                        </div>
                    )}

                    {/* Empty state */}
                    {!postsLoading && !error && posts.length === 0 && (
                        <div className="text-center py-12">
                            <p className="text-sm text-muted-foreground">
                                No posts yet. Be the first to post.
                            </p>
                        </div>
                    )}

                    {/* Posts */}
                    {!postsLoading && !error && posts.map((post) => (
                        <PostCard
                            key={post.post.id}
                            post={post}
                            onEdit={handleEdit}
                            onDeleted={handleDeleted}
                        />
                    ))}
                </main>
            </SidebarInset>

            {/* Edit dialog - lives outside the feed so it isn't unmounted on scroll */}
            <EditPostDialog
                post={editingPost}
                open={editOpen}
                onOpenChage={setEditOpen}
                onSaved={handleSaved}
            />
        </SidebarProvider>
    );
}