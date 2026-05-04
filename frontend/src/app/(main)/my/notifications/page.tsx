"use client";

import { useEffect } from "react";
import { useNotifications } from "@/hooks/useNotifications";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Bell, ArrowLeft, ExternalLink } from "lucide-react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export default function NotificationsPage() {
    const { notifications, markAsRead, refresh } = useNotifications({ showToast: false });
    const router = useRouter();

    useEffect(() => {
        refresh();
    }, [refresh]);

    return (
        <div className="container max-w-4xl mx-auto py-12 px-4 animate-in fade-in duration-500">
            <Button
                variant="ghost"
                className="mb-8 hover:bg-slate-100 text-slate-500 font-bold"
                onClick={() => router.back()}
            >
                <ArrowLeft className="h-4 w-4 mr-2" /> 뒤로 가기
            </Button>

            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-black tracking-tight text-slate-900">알림 센터</h1>
                    <p className="text-slate-500 mt-2 font-medium">활동 내역과 처리 상태 알림을 확인하세요.</p>
                </div>
            </div>

            <div className="space-y-4">
                {notifications.length === 0 ? (
                    <Card className="py-16 text-center shadow-sm border-dashed border-slate-200 bg-slate-50/50">
                        <div className="flex flex-col items-center">
                            <Bell className="h-12 w-12 text-slate-300 mb-4" />
                            <p className="text-slate-400 font-medium text-lg">새로운 알림이 없습니다.</p>
                        </div>
                    </Card>
                ) : (
                    notifications.map((n, index) => (
                        <motion.div
                            key={n.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05 }}
                        >
                            <Card
                                className={cn(
                                    "group hover:shadow-md transition-all duration-300 cursor-pointer border-slate-100",
                                    !n.is_read && "ring-1 ring-blue-500/10 bg-blue-50/20 border-blue-50"
                                )}
                                onClick={() => {
                                    markAsRead(n.id);
                                    if (n.link) router.push(n.link);
                                }}
                            >
                                <CardContent className="p-6">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                                {!n.is_read && <div className="h-2 w-2 rounded-full bg-blue-600 animate-pulse" />}
                                                <h3 className={cn("font-bold text-slate-800", !n.is_read && "text-blue-900")}>
                                                    {n.title}
                                                </h3>
                                            </div>
                                            <p className="text-sm text-slate-500 leading-relaxed mb-3">
                                                {n.message}
                                            </p>
                                            <div className="flex items-center gap-4 text-[11px] text-slate-400 font-bold uppercase tracking-wider">
                                                <span>{new Date(n.created_at).toLocaleString()}</span>
                                                {n.link && (
                                                    <span className="flex items-center gap-1 text-blue-600 hover:text-blue-700 transition-colors">
                                                        <ExternalLink className="h-3 w-3" /> 연관 페이지로 이동
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    ))
                )}
            </div>
        </div>
    );
}
