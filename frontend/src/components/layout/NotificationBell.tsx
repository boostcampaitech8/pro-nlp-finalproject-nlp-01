"use client";

import { Bell, CheckCheck } from "lucide-react";
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
    const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
    const router = useRouter();

    // Filter to show ONLY unread notifications in the overlay
    const unreadNotifications = (notifications || []).filter(n => !n.is_read);

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
            <DropdownMenuContent align="end" className="w-80 max-h-[400px] overflow-y-auto scrollbar-hide">
                <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold">새 알림</span>
                        {unreadCount > 0 && <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">{unreadCount}</span>}
                    </div>
                    {unreadCount > 0 && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-slate-400 hover:text-blue-600"
                            title="모두 읽음 처리"
                            onClick={(e) => {
                                e.preventDefault(); // Prevent closing dropdown
                                markAllAsRead();
                            }}
                        >
                            <CheckCheck className="h-4 w-4" />
                        </Button>
                    )}
                </div>
                {unreadNotifications.length === 0 ? (
                    <div className="py-12 flex flex-col items-center justify-center text-slate-400 gap-2">
                        <Bell className="h-8 w-8 opacity-20" />
                        <span className="text-xs">새로운 알림이 없습니다.</span>
                    </div>
                ) : (
                    unreadNotifications.map((n) => (
                        <DropdownMenuItem
                            key={n.id}
                            className="flex flex-col items-start gap-1 p-4 cursor-pointer focus:bg-slate-50 border-b border-slate-50 last:border-0 bg-blue-50/30"
                            onClick={() => {
                                markAsRead(n.id);
                                if (n.link) router.push(n.link);
                            }}
                        >
                            <div className="flex items-center justify-between w-full">
                                <span className={cn("text-sm font-medium", !n.is_read && "text-blue-700")}>{n.title}</span>
                                <span className="text-[10px] text-slate-400">
                                    {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                            </div>
                            <p className="text-xs text-slate-500 line-clamp-2">{n.message}</p>
                        </DropdownMenuItem>
                    ))
                )}
                <div className="p-2 border-t border-slate-100 text-center sticky bottom-0 bg-white">
                    <Link href="/my/notifications" className="text-xs text-slate-400 hover:text-slate-600 block w-full py-1">
                        이전 알림 전체 보기
                    </Link>
                </div>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
