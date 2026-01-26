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
                const res = await fetch(getApiUrl(`/auth/kakao/callback?code=${code}`));
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
        <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50">
            <div className="space-y-4 text-center">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <h2 className="text-xl font-bold text-slate-800">카카오 로그인 처리 중...</h2>
                <p className="text-slate-500">잠시만 기다려 주세요.</p>
            </div>
        </div>
    );
}
