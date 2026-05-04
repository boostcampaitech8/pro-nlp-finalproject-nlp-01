"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/useAuthStore";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { NotificationBell } from "./NotificationBell";
import { Menu, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

export function Header() {
    const { isAuthenticated, logout, user } = useAuthStore();
    const router = useRouter();
    const [mounted, setMounted] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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
        setIsMobileMenuOpen(false);
        router.push("/login"); // 로그아웃 후 로그인 페이지로 이동
    };

    if (!mounted) return (
        <header className="sticky top-0 z-50 w-full border-b bg-white">
            <div className="container max-w-screen-xl mx-auto flex h-16 items-center px-4 md:px-8">
                <span className="font-pretendard font-black text-xl tracking-tight">모두취업</span>
            </div>
        </header>
    );

    const navLinks = [
        { href: "/recruit", label: "채용 공고" },
        ...(isAuthenticated ? [
            { href: "/my/cover-letters", label: "내 자소서" },
            { href: "/my/portfolios", label: "내 포트폴리오" },
            { href: "/my/profile", label: "내 프로필" },
        ] : []),
    ];

    return (
        <header className="sticky top-0 z-50 w-full border-b border-border bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
            <div className="container max-w-screen-xl mx-auto flex h-16 items-center justify-between px-4 md:px-8">
                {/* Logo & Nav */}
                <div className="flex items-center gap-8">
                    <Link href="/" className="flex items-center">
                        <span className="font-pretendard font-black text-xl tracking-tight text-foreground">모두취업</span>
                    </Link>
                    <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-muted-foreground">
                        {navLinks.map((link) => (
                            <Link key={link.href} href={link.href} className="hover:text-blue-600 transition-colors">
                                {link.label}
                            </Link>
                        ))}
                    </nav>
                </div>

                {/* Right Side Actions */}
                <div className="flex items-center gap-2 md:gap-3">
                    <div className="hidden md:flex items-center gap-3">
                        {isAuthenticated ? (
                            <>
                                <NotificationBell />
                                <span className="text-sm text-gray-500 hidden lg:inline-block mr-2 ml-1">
                                    <strong>{user?.name}</strong>님 환영합니다
                                </span>
                                <Button variant="ghost" size="sm" onClick={handleLogout} className="text-slate-600 hover:text-red-600 hover:bg-red-50">
                                    로그아웃
                                </Button>
                            </>
                        ) : (
                            <Link href="/login">
                                <Button variant="ghost" size="sm" className="text-gray-600 font-medium hover:text-gray-900">로그인</Button>
                            </Link>
                        )}
                    </div>

                    {/* Mobile Menu Toggle */}
                    <div className="flex md:hidden items-center gap-2">
                        {isAuthenticated && <NotificationBell />}
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                            className="text-foreground"
                        >
                            {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                        </Button>
                    </div>
                </div>
            </div>

            {/* Mobile Navigation Menu */}
            <AnimatePresence>
                {isMobileMenuOpen && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="md:hidden border-b border-border bg-background"
                    >
                        <nav className="flex flex-col p-4 gap-2">
                            {navLinks.map((link) => (
                                <Link
                                    key={link.href}
                                    href={link.href}
                                    onClick={() => setIsMobileMenuOpen(false)}
                                    className="px-4 py-3 rounded-xl hover:bg-muted text-sm font-medium transition-colors"
                                >
                                    {link.label}
                                </Link>
                            ))}
                            <div className="h-px bg-border my-2" />
                            {isAuthenticated ? (
                                <div className="px-4 py-3 flex flex-col gap-4">
                                    <div className="text-sm text-muted-foreground">
                                        <strong>{user?.name}</strong>님 안녕하세요
                                    </div>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleLogout}
                                        className="w-full justify-center text-red-600 border-red-100 hover:bg-red-50 hover:border-red-200"
                                    >
                                        로그아웃
                                    </Button>
                                </div>
                            ) : (
                                <Link href="/login" onClick={() => setIsMobileMenuOpen(false)} className="px-4 py-2">
                                    <Button className="w-full justify-center">로그인</Button>
                                </Link>
                            )}
                        </nav>
                    </motion.div>
                )}
            </AnimatePresence>
        </header>
    );
}
