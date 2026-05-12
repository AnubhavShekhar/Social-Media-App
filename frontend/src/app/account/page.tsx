"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { deleteAccount } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
    SidebarProvider,
    SidebarInset,
    SidebarTrigger,
} from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppSidebar from "@/components/nav/sidebar";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { type } from '../../../.next/dev/types/routes';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export default function AccountPage() {
    const router = useRouter();
    const { user, loading: authLoading, logout} = useAuth();

    const [confirmEmail, setConfirmEmail] = useState("");
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [deleteError, setDeleteError] = useState("");

    // ------- Auth guard ----------------------------------
    useEffect(() => {
        if (!authLoading && !user){
            router.replace("/login");
        }
    }, [user, authLoading, router]);

    //----- Handlers ----------------------------------------
    function handleLogout() {
        logout();
        router.replace("/login");
    }

    async function handleDeleteAccount() {
        if (!user) return;
        if (confirmEmail !== user.email){
            setDeleteError(`Type your email "${user.email}" to confirm`);
            return;
        }
        setDeleteError("");
        setDeleteLoading(true);
        try{
            await deleteAccount(user.id);
            logout();
            router.replace("/login");
        } catch (err: unknown) {
            if (err instanceof Error){
                setDeleteError(err.message);
            } else {
                setDeleteError("Failed to delete account")
            }
        } finally {
            setDeleteLoading(false);
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
                        <span className="text-sm font-medium">Account</span>
                    </header>

                    <main className="flex flex-col gap-4 p-4 max-w-2xl mx-auto w-full">
                        {/* Profile card */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Profile</CardTitle>
                                <CardDescription>
                                    Your account information
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center gap-4">
                                    <Avatar className="h-14 w-14">
                                        <AvatarFallback className="text-lg">
                                            {user?.email[0].toUpperCase()}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-sm font-medium">
                                            {user?.email}
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                            Member since {" "}
                                            {user?.created_at
                                                ? new Date(user.created_at).toLocaleDateString("en-US", {
                                                    month: "long",
                                                    year: "numeric",
                                                })
                                            : "-"}
                                        </span>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Session card */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Session</CardTitle>
                                <CardDescription>
                                    Manage your current session
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-muted-foreground mb-4">
                                    Signing out will end your session on this device.
                                    Your posts and data will remain intact.
                                </p>
                                <Button variant="outline" onClick={handleLogout}>
                                    Sign out
                                </Button>
                            </CardContent>
                        </Card>

                        {/* Danger zone card */}
                        <Card className="border-destructive/40">
                            <CardHeader>
                                <CardTitle className="text-destructive">
                                    Delete Account
                                </CardTitle>
                                <CardDescription>
                                    Permanently delete your account and all your posts.
                                    This action cannot be undone.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex flex-col gap-4">
                                <div className="grid gap-2">
                                    <Label htmlFor="confirmEmail">
                                        Type your email to confirm
                                    </Label>
                                    <Input 
                                        id="confirmEmail"
                                        type="email"
                                        placeholder={user?.email}
                                        value={confirmEmail}
                                        onChange={(e) => {
                                            setConfirmEmail(e.target.value);
                                            setDeleteError("");
                                        }}
                                    />
                                    {deleteError && (
                                        <p className="text-sm text-destructive">
                                            {deleteError}
                                        </p>
                                    )}
                                </div>

                                <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                        <Button
                                            variant="destructive"
                                            disabled={confirmEmail !== user?.email}
                                            className="w-fit"
                                        >
                                            Delete account
                                        </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                        <AlertDialogHeader>
                                            <AlertDialogTitle>
                                                Are you absolutely sure?
                                            </AlertDialogTitle>
                                            <AlertDialogDescription>
                                                This will permanently delete your account and every posts you 
                                                have ever made. This action is irreversible.
                                            </AlertDialogDescription>
                                        </AlertDialogHeader>
                                        <AlertDialogFooter>
                                            <AlertDialogCancel disabled={deleteLoading}>
                                                Cancel
                                            </AlertDialogCancel>
                                            <AlertDialogAction
                                                onClick={handleDeleteAccount}
                                                disabled={deleteLoading}
                                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                            >
                                                {deleteLoading ? "Deleting..." : "Yes, delete everything"}
                                            </AlertDialogAction>
                                        </AlertDialogFooter>
                                    </AlertDialogContent>
                                </AlertDialog>
                            </CardContent>
                        </Card>
                    </main>
                </SidebarInset>
            </SidebarProvider>
        </TooltipProvider>
    );
}