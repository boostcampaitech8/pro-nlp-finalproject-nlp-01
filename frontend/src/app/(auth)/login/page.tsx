"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { MessageCircle, ArrowRight } from "lucide-react";

export default function LoginPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);

    const handleKakaoLogin = () => {
        setLoading(true);
        const client_id = "36cb87d77a70e26540f4e7c71bc02c87";
        const redirect_uri = window.location.origin + "/kakao/callback";
        const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${client_id}&redirect_uri=${redirect_uri}&response_type=code`;
        window.location.href = kakaoAuthUrl;
    };

    return (
        <div className="flex items-center justify-center min-h-screen px-4 bg-slate-50/50 animate-in fade-in duration-700">
            <div className="w-full max-w-[480px] space-y-4">

                {/* Branding Section */}
                <div className="text-center space-y-1 mb-8">
                    <h1 className="text-3xl font-black tracking-tight text-slate-900">
                        Pro-NLP <span className="text-blue-600">Login</span>
                    </h1>
                    <p className="text-sm text-slate-500 font-medium">
                        다시 오신 것을 환영합니다. 당신의 성장을 지원합니다.
                    </p>
                </div>

                <Card className="shadow-2xl border-slate-200 bg-white overflow-hidden rounded-2xl">
                    <CardHeader className="space-y-2 text-center bg-slate-50/50 border-b border-slate-100 py-8">
                        <CardTitle className="text-2xl font-bold text-slate-800 tracking-tight">환영합니다!</CardTitle>
                        <CardDescription className="text-slate-400 text-sm max-w-[280px] mx-auto leading-relaxed">
                            카카오 계정으로 안전하고 빠르게<br />서비스를 시작해 보세요.
                        </CardDescription>
                    </CardHeader>

                    <CardContent className="pt-10 pb-6 px-10">
                        <div className="flex flex-col gap-6">
                            <Button
                                type="button"
                                size="lg"
                                className="w-full h-14 bg-[#FEE500] hover:bg-[#FEE500]/90 text-slate-900 text-base font-bold shadow-sm transition-all active:scale-[0.98] rounded-xl border border-[#E6CF00]/30"
                                onClick={handleKakaoLogin}
                                disabled={loading}
                            >
                                <MessageCircle className="mr-3 h-6 w-6 fill-current" />
                                {loading ? "카카오 로그인 중..." : "카카오로 3초만에 시작하기"}
                            </Button>

                            <p className="text-[10px] text-center text-slate-400 leading-relaxed px-4">
                                로그인 시 Pro-NLP의 <span className="underline cursor-pointer hover:text-blue-500 transition-colors">이용약관</span> 및 <span className="underline cursor-pointer hover:text-blue-500 transition-colors">개인정보처리방침</span>에 동의하게 됩니다.
                            </p>
                        </div>
                    </CardContent>

                    <CardFooter className="flex justify-center pb-8 pt-4 border-t border-slate-50/50 bg-slate-50/20">
                        <div className="flex items-center gap-2 text-[9px] font-black text-slate-300 tracking-[0.2em] uppercase antialiased">
                            <ArrowRight className="h-2.5 w-2.5 opacity-50" /> Secure AI Recruitment Platform
                        </div>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
}
