"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { createPost } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
    SidebarProvider,
    SidebarInset,
    SidebarTrigger,
} from '@/components/ui/sidebar';
import { TooltipProvider } from "@/components/ui/tooltip";
import AppSidebar from "@/components/nav/sidebar";
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from "@/components/ui/separator";
import { ImagePlus, X } from "lucide-react";
import Image from "next/image";

export default function NewPostPage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    
    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const fileInputRef = useRef<HTMLInputElement>(null);

    //------ Auth guard --------------------------------
    useEffect(() => {
        if(!authLoading && !user) {
            router.replace("/login");
        }
    }, [user, authLoading, router]);

    //---------Image selection -----------------------------
    function handleImageChange(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if(!file) return;

        // Validate type
        const allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"];
        if(!allowedTypes.includes(file.type)) {
            setError("Invalid file type. Allowed: jpeg, png, webp, gif");
            return;
        }

        // Validate size - 5MB
        if (file.size > 5 * 1024 * 1024) {
            setError("Image must be under 5MB");
            return;
        }

        setError("");
        setImageFile(file);

        //Generate a local preview URL so the user can see the image before it's uploaded
        const previewUrl = URL.createObjectURL(file);
        setImagePreview(previewUrl);
    }

    function handleRemoveImage() {
        setImageFile(null);
        // Revoke the object URL to free browser memory
        if (imagePreview) {
            URL.revokeObjectURL(imagePreview);
            setImagePreview(null);
        }
        // Reset the file input so the same file can be re-selected
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }

    // ------Submit-------------------------------------
    async function handleSubmit(e: React.SubmitEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try{
            await createPost({
                title, 
                content,
                ...(imageFile ? {image : imageFile} : {}),
            });
            // Clean up preview URL before navigating
            if (imagePreview) URL.revokeObjectURL(imagePreview);
            router.push("/home");
        } catch (err: unknown) {
            if (err instanceof Error){
                setError(err.message)
            } else {
                setError("Failed to create post");
            }
        } finally {
            setLoading(false);
        }
    }

    if (authLoading) return null;

    return (
        <TooltipProvider>
            <SidebarProvider>
                <AppSidebar/>
                <SidebarInset>
                    {/* Top bar */}
                    <header className="flex items-center gap-2 px-4 py-3 border-b border-border">
                        <SidebarTrigger/>
                        <Separator orientation="vertical" className="h-4"/>
                        <span className="text-sm font-medium">New Post</span>
                    </header>

                    {/* Content */}
                    <main className="flex flex-col gap-4 p-4 max-w-2xl mx-auto w-full">
                        <Card>
                            <CardHeader>
                                <CardTitle>Create a post</CardTitle>
                                <CardDescription>
                                    Share something with the community
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                                    {/* Title */}
                                    <div className="grid gap-2">
                                        <Label htmlFor="title">Title</Label>
                                        <Input 
                                            id="title"
                                            placeholder="Give your post a title"
                                            required
                                            maxLength={200}
                                            value={title}
                                            onChange={(e) => setTitle(e.target.value)}
                                        />
                                        <span className="text-xs text-muted-foreground text-right">
                                            {title.length}/200
                                        </span>
                                    </div>

                                    {/* Content */}
                                    <div className="grid gap-2">
                                        <Label htmlFor="content">Content</Label>
                                        <Textarea
                                            id="content"
                                            placeholder="What's on your mind?"
                                            required
                                            rows={8}
                                            className="resize-none"
                                            value={content}
                                            onChange={(e) => setContent(e.target.value)}
                                        />
                                    </div>

                                    {/* Image upload */}
                                    <div className="grid gap-2">
                                        <Label>Image</Label>

                                        {/* Hidden real file input */}
                                        <input 
                                            ref={fileInputRef}
                                            type="file"
                                            accept="image/jpeg,image/png,image/webp,image/gif"
                                            className="hidden"
                                            onChange={handleImageChange}
                                        />

                                        {/* Show preview if image selected */}
                                        {imagePreview ? (
                                            <div className="relative w-full rounded-md overflow-hidden border border-border" style={{ aspectRatio: "auto", minHeight: "200px", maxHeight: "320px" }}>
                                                <Image
                                                    src={imagePreview}
                                                    alt="preview"
                                                    fill
                                                    className="object-contain"
                                                    sizes="(max-width: 672px) 100vw, 672px"
                                                    unoptimized
                                                />
                                                <button
                                                    type="button"
                                                    onClick={handleRemoveImage}
                                                    className="absolute top-2 right-2 bg-background/80 backdrop-blur-sm rounded-full p-1 hover:bg-background transition-colors"
                                                    aria-label="Remove image"
                                                >
                                                    <X size={14}/>
                                                </button>
                                            </div>
                                        ) : (
                                            /* Upload button when no image selected */
                                            <button 
                                                type="button"
                                                onClick={() => fileInputRef.current?.click()}
                                                className="flex flex-col items-center justify-center gap-2 w-full h-32 rounded-md border border-dashed border-border text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                                            >
                                                <ImagePlus size={20}/>
                                                <span className="text-xs">
                                                    Click to upload image
                                                </span>
                                                <span className="text-xs opacity-60">
                                                    JPEG, PNG, WebP, GIF - max 5MB
                                                </span>
                                            </button>
                                        )}
                                    </div>

                                    {error && (
                                        <p className="text-sm text-destructive">{error}</p>
                                    )}

                                    <div className="flex justify-end gap-3">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            onClick={() => router.push("/home")}
                                            disabled={loading}
                                        >
                                            Cancel
                                        </Button>
                                        <Button type="submit" disabled={loading}>
                                            {loading ? "Publishing..." : "Publish post"}
                                        </Button>
                                    </div>
                                </form>
                            </CardContent>
                        </Card>
                    </main>
                </SidebarInset>
            </SidebarProvider>
        </TooltipProvider>
    );
}