"use client";

import { useAuthStore } from "@/stores/useAuthStore";

export default function DashboardPage() {
    const { user } = useAuthStore();

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold">안녕하세요, {user?.name}님!</h1>
            <p className="text-muted-foreground">대시보드 페이지 준비 중입니다.</p>
        </div>
    );
}
