"use client";

import { Bell } from "lucide-react";
import { useNotifications } from "@/hooks/useNotifications";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";

// Note: If dropdown-menu component doesn't match exactly, I'll adjust as I see it.
// Assuming standard Radix UI pattern.

export function NotificationBell() {
    const { notifications, unreadCount, markAsRead } = useNotifications();
    const router = useRouter();

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="relative">
                    <Bell className="h-5 w-5 text-slate-600" />
                    {unreadCount > 0 && (
                        <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                        </span>
                    )}
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 max-h-[400px] overflow-y-auto">
                <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
                    <span className="text-sm font-semibold">알림</span>
                    {unreadCount > 0 && <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">{unreadCount}</span>}
                </div>
                {notifications.length === 0 ? (
                    <div className="py-8 text-center text-sm text-slate-400">새로운 알림이 없습니다.</div>
                ) : (
                    notifications.map((n) => (
                        <DropdownMenuItem
                            key={n.id}
                            className={cn(
                                "flex flex-col items-start gap-1 p-4 cursor-pointer focus:bg-slate-50 border-b border-slate-50 last:border-0",
                                !n.is_read && "bg-blue-50/50"
                            )}
                            onClick={() => {
                                markAsRead(n.id);
                                if (n.link) router.push(n.link);
                            }}
                        >
                            <div className="flex items-center justify-between w-full">
                                <span className="text-sm font-medium">{n.title}</span>
                                <span className="text-[10px] text-slate-400">
                                    {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                            </div>
                            <p className="text-xs text-slate-500 line-clamp-2">{n.message}</p>
                        </DropdownMenuItem>
                    ))
                )}
                <div className="p-2 border-t border-slate-100 text-center">
                    <Link href="/my/notifications" className="text-xs text-slate-400 hover:text-slate-600">
                        전체 알림 보기
                    </Link>
                </div>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
