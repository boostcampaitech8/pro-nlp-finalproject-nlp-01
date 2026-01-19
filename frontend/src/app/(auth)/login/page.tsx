"use client";

import { useAuthStore } from "@/stores/useAuthStore";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import Link from "next/link";
import { Mail, Lock, MessageCircle, ArrowRight } from "lucide-react";

export default function LoginPage() {
    const { login } = useAuthStore();
    const router = useRouter();
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setTimeout(() => {
            // Zustand 상태 저장
            login({ id: 1, email: "test@example.com", name: "김코딩" }, "mock-jwt-token");

            // 미들웨어를 위한 쿠키 설정
            document.cookie = "accessToken=mock-jwt-token; path=/; max-age=86400";

            setLoading(false);
            router.push("/recruit");
        }, 1200);
    };

    const handleKakaoLogin = () => {
        alert("카카오 로그인은 추후 도입 예정입니다.");
    };

    return (
        <div className="flex items-center justify-center min-h-screen px-4 bg-slate-50/50 animate-in fade-in duration-700">
            <div className="w-full max-w-[600px] space-y-6">

                {/* Branding Section */}
                <div className="text-center space-y-2">
                    <h1 className="text-3xl font-black tracking-tight text-slate-900">
                        Pro-NLP <span className="text-blue-600">Login</span>
                    </h1>
                    <p className="text-slate-500">
                        다시 오신 것을 환영합니다. 당신의 성장을 지원합니다.
                    </p>
                </div>

                <Card className="shadow-2xl border-slate-200 bg-white overflow-hidden rounded-xl">
                    <CardHeader className="space-y-1 text-center bg-slate-50/50 border-b border-slate-100 py-8">
                        <CardTitle className="text-xl font-bold text-slate-800">계정 로그인</CardTitle>
                        <CardDescription className="text-slate-400 text-sm">
                            이메일 주소와 비밀번호를 입력해주세요.
                        </CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-6 p-10">
                        <form onSubmit={handleLogin} className="space-y-5">
                            <div className="space-y-2">
                                <Label htmlFor="email" className="text-xs font-bold text-slate-500 uppercase tracking-wider ml-1">이메일 주소</Label>
                                <div className="relative border-none">
                                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                                        <Mail className="h-4 w-4" />
                                    </div>
                                    <Input
                                        id="email"
                                        type="email"
                                        placeholder="name@example.com"
                                        required
                                        defaultValue="test@example.com"
                                        className="pl-11 h-11 border-slate-200 focus-visible:ring-blue-500 bg-slate-50/30 text-sm transition-all focus:bg-white rounded-md"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="flex items-center justify-between ml-1">
                                    <Label htmlFor="password" className="text-xs font-bold text-slate-500 uppercase tracking-wider">비밀번호</Label>
                                    <Link href="#" className="text-xs text-slate-400 hover:text-blue-500 transition-colors">비밀번호 찾기</Link>
                                </div>
                                <div className="relative border-none">
                                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                                        <Lock className="h-4 w-4" />
                                    </div>
                                    <Input
                                        id="password"
                                        type="password"
                                        required
                                        defaultValue="password"
                                        placeholder="••••••••"
                                        className="pl-11 h-11 border-slate-200 focus-visible:ring-blue-500 bg-slate-50/30 text-sm transition-all focus:bg-white rounded-md"
                                    />
                                </div>
                            </div>

                            <div className="pt-2">
                                <Button
                                    variant="brand"
                                    size="lg"
                                    className="w-full rounded-md"
                                    type="submit"
                                    disabled={loading}
                                >
                                    {loading ? (
                                        "로그인 중..."
                                    ) : (
                                        <span className="flex items-center gap-2">
                                            로그인하기 <ArrowRight className="h-4 w-4" />
                                        </span>
                                    )}
                                </Button>
                            </div>
                        </form>

                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-slate-100" />
                            </div>
                            <div className="relative flex justify-center text-[10px] uppercase font-bold tracking-widest">
                                <span className="bg-white px-4 text-slate-300">OR</span>
                            </div>
                        </div>

                        <Button
                            type="button"
                            className="w-full h-11 bg-[#FEE500] hover:bg-[#FEE500]/90 text-slate-900 text-sm font-bold shadow-sm transition-all active:scale-[0.98] rounded-md border border-[#E6CF00]/30"
                            onClick={handleKakaoLogin}
                        >
                            <MessageCircle className="mr-2 h-5 w-5 fill-current" />
                            카카오로 3초만에 시작하기
                        </Button>
                    </CardContent>

                    <CardFooter className="flex justify-center pb-8 pt-0">
                        <p className="text-sm text-slate-500">
                            계정이 없으신가요?{" "}
                            <Link href="/signup" className="text-blue-600 font-bold hover:underline transition-colors ml-1">
                                회원가입하기
                            </Link>
                        </p>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
}
