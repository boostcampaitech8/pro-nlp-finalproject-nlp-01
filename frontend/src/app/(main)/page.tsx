"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/useAuthStore";

export default function LandingPage() {
    const { isAuthenticated } = useAuthStore();

    return (
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-140px)] text-center px-4 animate-in fade-in duration-700">
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight lg:text-7xl mb-6">
                취업의 모든 과정 <br />
                <span className="text-primary font-pretendard font-black">모두취업</span>과 함께
            </h1>
            <p className="text-xl text-muted-foreground max-w-[600px] mb-8 leading-relaxed">
                포트폴리오 관리부터 공고 추천, 자기소개서 작성까지.<br />
                AI가 당신의 커리어 여정을 완벽하게 서포트합니다.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
                <Link href="/recruit">
                    <Button size="lg" className="h-12 px-8 text-lg shadow-lg hover:shadow-xl transition-all font-bold">
                        {isAuthenticated ? "채용 공고 보러가기" : "지금 시작하기"}
                    </Button>
                </Link>
            </div>
        </div>
    );
}
