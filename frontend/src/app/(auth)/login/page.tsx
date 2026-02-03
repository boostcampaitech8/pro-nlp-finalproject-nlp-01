"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { MessageCircle, ArrowRight } from "lucide-react";
import { getApiUrl } from "@/lib/apiUtils";

export default function LoginPage() {
    const [loading, setLoading] = useState(false);
    const router = useRouter();
    // const { login } = useAuthStore(); // Unused

    const handleKakaoLogin = () => {
        setLoading(true);
        const client_id = "36cb87d77a70e26540f4e7c71bc02c87";
        const redirect_uri = window.location.origin + "/auth/kakao/callback";
        const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${client_id}&redirect_uri=${redirect_uri}&response_type=code`;
        window.location.href = kakaoAuthUrl;
    };

    const handleTestLogin = async (role: string) => {
        setLoading(true);
        try {
            const res = await fetch(getApiUrl("/auth/test-login"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ role })
            });
            if (res.ok) {
                const data = await res.json();
                localStorage.setItem("access_token", data.access_token);
                localStorage.setItem("user", JSON.stringify(data.user));
                router.push("/my/dashboard");
            } else {
                alert("테스트 로그인에 실패했습니다.");
            }
        } catch (e) {
            console.error(e);
            alert("로그인 중 오류가 발생했습니다.");
        } finally {
            setLoading(false);
        }
    };



    return (
        <div className="flex items-center justify-center min-h-screen px-4 bg-slate-50/50 animate-in fade-in duration-700">
            <div className="w-full max-w-[440px] space-y-4">

                {/* Branding Section */}
                <div className="text-center space-y-1 mb-6">
                    <h1 className="text-3xl font-black tracking-tight text-slate-900">
                        Pro-NLP <span className="text-blue-600">Login</span>
                    </h1>
                    <p className="text-xs text-slate-500 font-bold uppercase tracking-widest opacity-60">
                        Secure AI Recruitment Partner
                    </p>
                </div>

                <Card className={cn(
                    "border-slate-200 bg-white overflow-hidden rounded-[32px] transition-all duration-500",
                    loading ? "shadow-none" : "shadow-2xl"
                )}>
                    <CardHeader className="space-y-2 text-center bg-slate-50/30 border-b border-slate-100/50 py-8">
                        <CardTitle className="text-2xl font-black text-slate-800 tracking-tight">환영합니다!</CardTitle>
                        <CardDescription className="text-slate-400 text-[13px] max-w-[240px] mx-auto leading-relaxed font-medium">
                            카카오 계정으로 안전하고 빠르게<br />서비스를 시작해 보세요.
                        </CardDescription>
                    </CardHeader>

                    <CardContent className="pt-10 pb-6 px-10">
                        <div className="flex flex-col gap-6">
                            <Button
                                type="button"
                                size="lg"
                                className="w-full h-15 bg-[#FEE500] hover:bg-[#FEE500]/95 text-slate-900 text-base font-bold shadow-xl shadow-yellow-200/50 transition-all active:scale-[0.97] rounded-2xl border-none"
                                onClick={handleKakaoLogin}
                                disabled={loading}
                            >
                                <MessageCircle className="mr-3 h-6 w-6 fill-current" />
                                {loading ? "연결 중..." : "카카오로 3초만에 시작하기"}
                            </Button>

                            <div className="space-y-3">
                                <div className="flex items-center gap-3 py-2">
                                    <div className="h-[1px] flex-1 bg-slate-100" />
                                    <span className="text-[10px] font-black text-slate-300 uppercase tracking-widest">빠른 체험하기</span>
                                    <div className="h-[1px] flex-1 bg-slate-100" />
                                </div>
                                <div className="grid grid-cols-1 gap-2">
                                    {[
                                        { id: 'frontend', label: '프론트엔드 아이디로 로그인', color: 'bg-blue-50 text-blue-700 border-blue-100 hover:bg-blue-100' },
                                        { id: 'backend', label: '백엔드 아이디로 로그인', color: 'bg-indigo-50 text-indigo-700 border-indigo-100 hover:bg-indigo-100' },
                                        { id: 'data', label: '데이터 엔지니어 아이디로 로그인', color: 'bg-emerald-50 text-emerald-700 border-emerald-100 hover:bg-emerald-100' }
                                    ].map((role) => (
                                        <Button
                                            key={role.id}
                                            variant="outline"
                                            className={cn("h-11 rounded-xl text-xs font-bold border transition-all active:scale-[0.98]", role.color)}
                                            onClick={() => handleTestLogin(role.id)}
                                            disabled={loading}
                                        >
                                            {role.label}
                                        </Button>
                                    ))}
                                </div>
                            </div>

                            <p className="text-[10px] text-center text-slate-400/80 leading-relaxed px-6 font-medium">
                                로그인 시 Pro-NLP의 <span className="underline cursor-pointer hover:text-blue-500 transition-colors">이용약관</span> 및 <span className="underline cursor-pointer hover:text-blue-500 transition-colors">개인정보처리방침</span>에 동의하게 됩니다.
                            </p>

                            <div className="pt-2">
                                <Button
                                    variant="ghost"
                                    className="w-full h-12 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-2xl font-bold flex items-center justify-center gap-2"
                                    onClick={() => router.push("/")}
                                >
                                    홈으로 돌아가기
                                </Button>
                            </div>
                        </div>
                    </CardContent>

                    <CardFooter className="flex flex-col justify-center pb-8 pt-2 gap-4">
                        <div className="flex items-center gap-2 text-[8px] font-black text-slate-300 tracking-[0.3em] uppercase">
                            <ArrowRight className="h-2 w-2 opacity-30" /> Powered by Advanced NLP
                        </div>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
}
