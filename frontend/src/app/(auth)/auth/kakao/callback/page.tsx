"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/stores/useAuthStore";
import { getApiUrl } from "@/lib/apiUtils";

export default function KakaoCallbackPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { login } = useAuthStore();
    const isProcessing = useRef(false);

    useEffect(() => {
        const code = searchParams.get("code");
        if (!code || isProcessing.current) return;

        isProcessing.current = true;

        const handleCallback = async () => {
            try {
                const redirectUri = window.location.origin + "/auth/kakao/callback";
                const res = await fetch(getApiUrl(`/auth/kakao/callback?code=${code}&redirect_uri=${encodeURIComponent(redirectUri)}`));
                if (!res.ok) throw new Error("로그인 처리 중 오류가 발생했습니다.");

                const data = await res.json();

                // Zustand 상태 저장
                login(data.user, data.access_token);

                // 쿠키 설정 (미들웨어용)
                document.cookie = `accessToken=${data.access_token}; path=/; max-age=86400; SameSite=Lax; Secure`;

                // 메인 페이지로 이동
                router.push("/recruit");
            } catch (err) {
                console.error("Kakao login error:", err);
                alert("로그인에 실패했습니다. 다시 시도해주세요.");
                router.push("/login");
            }
        };

        handleCallback();
    }, [searchParams, login, router]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50/30">
            <div className="space-y-6 text-center animate-in fade-in duration-1000">
                <div className="relative">
                    <div className="w-16 h-16 border-4 border-slate-100 rounded-full mx-auto"></div>
                    <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto absolute inset-0"></div>
                </div>
                <div className="space-y-2">
                    <h2 className="text-xl font-black text-slate-800 tracking-tight">카카오 로그인 처리 중</h2>
                    <p className="text-sm text-slate-400 font-medium">안전한 로그인을 위해 잠시만 기다려 주세요.</p>
                </div>
            </div>
        </div>
    );
}
