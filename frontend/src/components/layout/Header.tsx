"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/useAuthStore";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { NotificationBell } from "./NotificationBell";

export function Header() {
    const { isAuthenticated, logout, user } = useAuthStore();
    const router = useRouter();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setMounted(true);
    }, []);

    useEffect(() => {
        // 클라이언트 사이드에서만 쿠키 체크
        const hasToken = document.cookie.split(';').some((item) => item.trim().startsWith('accessToken='));

        // 쿠키는 없는데 상태는 로그인인 경우 로그아웃 처리
        if (!hasToken && isAuthenticated) {
            logout();
        }
    }, [isAuthenticated, logout]);

    const handleLogout = () => {
        logout();
        // 쿠키 삭제
        document.cookie = "accessToken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        router.push("/login"); // 로그아웃 후 로그인 페이지로 이동
    };

    if (!mounted) return (
        <header className="sticky top-0 z-50 w-full border-b bg-white">
            <div className="container max-w-screen-xl mx-auto flex h-16 items-center px-4 md:px-8">
                <span className="font-bold text-xl tracking-tight">Pro-NLP</span>
            </div>
        </header>
    );

    return (
        <header className="sticky top-0 z-50 w-full border-b border-slate-100 bg-white/80 backdrop-blur-md supports-[backdrop-filter]:bg-white/60">
            <div className="container max-w-screen-xl mx-auto flex h-16 items-center justify-between px-4 md:px-8">
                {/* Logo & Nav */}
                <div className="flex items-center gap-8">
                    <Link href="/" className="flex items-center">
                        <span className="font-extrabold text-xl tracking-tight text-gray-900">Pro-NLP</span>
                    </Link>
                    <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600">
                        <Link href="/recruit" className="hover:text-blue-600 transition-colors">
                            채용 공고
                        </Link>
                        {isAuthenticated && (
                            <>
                                <Link href="/my/cover-letters" className="hover:text-blue-600 transition-colors">
                                    내 자소서
                                </Link>
                                <Link href="/my/portfolios" className="hover:text-blue-600 transition-colors">
                                    내 포트폴리오
                                </Link>
                                <Link href="/my/profile" className="hover:text-blue-600 transition-colors">
                                    내 프로필
                                </Link>
                            </>
                        )}
                    </nav>
                </div>

                {/* Right Side Actions */}
                <div className="flex items-center gap-3">
                    {isAuthenticated ? (
                        <>
                            <NotificationBell />
                            <span className="text-sm text-gray-500 hidden sm:inline-block mr-2 ml-1">
                                <strong>{user?.name}</strong>님 환영합니다
                            </span>
                            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-slate-600 hover:text-red-600 hover:bg-red-50">
                                로그아웃
                            </Button>
                        </>
                    ) : (
                        <>
                            <Link href="/login">
                                <Button variant="ghost" size="sm" className="text-gray-600 font-medium hover:text-gray-900">로그인</Button>
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </header>
    );
}
