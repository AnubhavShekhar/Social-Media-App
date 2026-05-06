"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Home, PenSquare, User } from "lucide-react";
import {
    Sidebar, 
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarSeparator,
} from "@/components/ui/sidebar";
import {
    Avatar,
    AvatarFallback,
} from "@/components/ui/avatar";

// --------Nav items ---------------------------------------------------
const navItems = [
    {
        label: "Feed",
        href: "/home",
        icon: Home,
    },
    {
        label: "New Post",
        href: "/new-post",
        icon: PenSquare,
    },
    {
        label: "Account",
        href: "/account",
        icon: User,
    },
];

//-----------Component---------------------------------------------------
export default function AppSidebar() {
    const pathname = usePathname();
    const { user } = useAuth();

    return (
        <Sidebar collapsible="icon">
            {/* Logo */}
            <SidebarHeader>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="lg" asChild>
                            <div className="flex items-center gap-2 cursor-default">
                                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">
                                    T
                                </div>
                                <span className="font-semibold tracking-tight">
                                    thread
                                </span>
                            </div>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>

            <SidebarSeparator/>

            {/* Nav Links */}
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navItems.map((item) => {
                                const Icon = item.icon;
                                const isActive = pathname === item.href;

                                return (
                                    <SidebarMenuItem key={item.href}>
                                        <SidebarMenuButton
                                            asChild
                                            isActive={isActive}
                                            tooltip={item.label}
                                        >
                                            <Link href={item.href}>
                                                <Icon />
                                                <span>{item.label}</span>
                                            </Link>
                                        </SidebarMenuButton>
                                   </SidebarMenuItem>
                                );
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>

            <SidebarSeparator/>

            {/*User info at bottom*/}
            <SidebarFooter>
                {user && (
                    <SidebarMenu>
                        <SidebarMenuItem>
                            <SidebarMenuButton size="lg" asChild tooltip={user.email}>
                                <Link href="/account">
                                    <Avatar className="h-8 w-8 rounded-lg">
                                        <AvatarFallback className="rounded-lg text-xs">
                                            {user.email[0].toUpperCase()}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-xs font-medium truncate">
                                            {user.email}
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                            Online
                                        </span>
                                    </div>
                                </Link>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                    </SidebarMenu>
                )}
            </SidebarFooter>
        </Sidebar>
    );
}