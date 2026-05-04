"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login, getMe } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";


export default function LoginPage() {
    const router = useRouter();
    const { setUser } = useAuth();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.SubmitEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try{
            const { access_token } = await login(email, password);
            localStorage.setItem("access_token", access_token);
            const me = await getMe();
            setUser(me);
            router.push("/home");
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Login failed");
            } 
        } finally {
                setLoading(false);
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
            <Card className="w-full max-w-sm">
                <CardHeader>
                    <CardTitle>Welcome Back</CardTitle>
                    <CardDescription>
                        Sign in to your account
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
                        <div className="grid gap-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                autoComplete="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                placeholder="••••••••"
                                autoComplete="current-password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </div>

                        {/* Error Message */}
                        {error && (
                            <p className="text-sm text-destructive">{error}</p>
                        )}

                        {/* Submit - lives inside the form so it triggers onSubmit */}
                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? "Signing in ..." : "Sign in"}
                        </Button>
                    </form>
                </CardContent>
                <CardFooter className="justify-center">
                    <p className="text-sm text-muted-foreground">
                        Don&apos;t have an account? {" "}
                        <Link
                            href={"/signup"}
                            className="text-primary font-medium hover:underline">
                                Create one
                        </Link>
                    </p>
                </CardFooter>
            </Card>
        </div>
    );
}