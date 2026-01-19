"use client";

import { useEffect, useState, use } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Recruit } from "@/types";
import { useRouter } from "next/navigation";
import { Calendar, Building, Briefcase, PenTool, Info, AlignLeft } from "lucide-react";
import { useAuthStore } from "@/stores/useAuthStore";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface RecruitDetail extends Recruit {
    content: string;
}

interface ExistingDoc {
    id: number;
    title: string;
    updatedAt: string;
}

export default function RecruitDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const router = useRouter();
    const { id } = use(params);
    const { isAuthenticated } = useAuthStore();
    const [recruit, setRecruit] = useState<RecruitDetail | null>(null);
    const [existingDocs, setExistingDocs] = useState<ExistingDoc[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`/api/recruits/${id}`)
            .then((res) => {
                if (!res.ok) {
                    if (res.headers.get("content-type")?.includes("text/html")) {
                        throw new Error("HTML response (Mocking inactive?)");
                    }
                    throw new Error("Not Found");
                }
                return res.json();
            })
            .then((data) => {
                setRecruit(data);
                setLoading(false);
            })
            .catch((err) => {
                console.error(err);
                setLoading(false);
            });

        if (isAuthenticated && id) {
            fetch(`/api/cover-letters?recruitId=${id}`, { cache: 'no-store' })
                .then(res => res.ok ? res.json() : { items: [] })
                .then(data => setExistingDocs(data.items || []))
                .catch(err => console.error(err));
        }
    }, [id, isAuthenticated]);

    if (loading) return null;
    if (!recruit) return <div className="py-20 text-center text-slate-500">공고를 찾을 수 없습니다.</div>;

    return (
        <div className="container max-w-screen-xl mx-auto py-12 px-4 md:px-8 animate-in fade-in zoom-in-95 duration-500">
            {/* Header Section */}
            <div className="mb-10 pb-8 border-b border-slate-100">
                <div className="flex flex-wrap items-center gap-2 mb-4">
                    <Badge variant="outline" className="px-3 py-1 text-sm font-medium bg-white border-slate-200 text-slate-600 gap-1.5 shadow-sm">
                        <Building className="h-3.5 w-3.5" />
                        {recruit.company}
                    </Badge>
                    {recruit.tags.map(tag => (
                        <Badge key={tag} variant="secondary" className="px-3 py-1 text-sm font-medium bg-slate-100 text-slate-600">
                            {tag}
                        </Badge>
                    ))}
                </div>
                <h1 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
                    {recruit.title}
                </h1>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

                {/* [Left Column] 상세 모집 내용 */}
                <div className="lg:col-span-8">
                    <Card className="shadow-sm border border-slate-200 bg-white">
                        <CardHeader className="border-b border-slate-100 bg-slate-50/30 pb-4">
                            <CardTitle className="text-lg font-bold flex items-center gap-2 text-slate-700">
                                <AlignLeft className="h-5 w-5" />
                                상세 모집 내용
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-8 leading-relaxed whitespace-pre-line text-lg text-slate-700 min-h-[500px]">
                            {recruit.content}
                            <br /><br />
                            <div className="space-y-4 text-base text-slate-500 mt-8 p-6 bg-slate-50 rounded-lg border border-slate-100">
                                <div>
                                    <strong className="text-slate-800 block mb-2">[자격 요건]</strong>
                                    <ul className="list-disc pl-5 space-y-1">
                                        <li>관련 경력 3년 이상</li>
                                        <li>React, Next.js 등 모던 프레임워크 능숙자</li>
                                    </ul>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* [Right Column] Sticky Sidebar */}
                <div className="lg:col-span-4 sticky top-24 space-y-6">
                    {/* 작성 중인 자소서 알림 */}
                    {existingDocs.length > 0 && (
                        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5">
                            <h4 className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-3">
                                <Info className="h-4 w-4" />
                                작성 중인 자소가 있습니다
                            </h4>
                            <ul className="space-y-2">
                                {existingDocs.map((doc) => (
                                    <li key={doc.id}>
                                        <Link href={`/my/cover-letters/${doc.id}`} className="block bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-200 transition-all group shadow-sm hover:shadow-md">
                                            <div className="font-medium text-sm text-slate-900 group-hover:text-blue-600 truncate transition-colors">{doc.title}</div>
                                            <div className="text-xs text-slate-400 mt-1">{doc.updatedAt} 저장됨</div>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* 채용 요약 카드 */}
                    <Card className="border border-slate-200 shadow-sm overflow-hidden bg-white">
                        <CardHeader className="bg-slate-50/50 pb-4 border-b border-slate-100">
                            <CardTitle className="flex items-center gap-2 text-lg font-bold text-slate-800">
                                <Briefcase className="h-5 w-5 text-slate-500" />
                                채용 요약
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-5 p-6 text-sm">
                            <div className="flex justify-between items-center pb-3 border-b border-slate-100 border-dashed">
                                <span className="text-slate-500 flex items-center gap-2">
                                    <Building className="h-4 w-4" /> 기업명
                                </span>
                                <span className="font-semibold text-right text-slate-700">{recruit.company}</span>
                            </div>
                            <div className="flex flex-col gap-2 pb-3 border-b border-slate-100 border-dashed">
                                <span className="text-slate-500 flex items-center gap-2">
                                    <Calendar className="h-4 w-4" /> 채용 기간
                                </span>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-slate-400 font-medium">{recruit.startDate}</span>
                                    <span className="text-xs text-slate-300">~</span>
                                    <span className={cn(
                                        "font-bold text-right",
                                        new Date(recruit.deadline) < new Date() ? "text-slate-400 line-through" : "text-red-500"
                                    )}>{recruit.deadline}</span>
                                </div>
                            </div>
                            <div className="flex justify-between items-center pb-3 border-b border-slate-100 border-dashed">
                                <span className="text-slate-500">직무</span>
                                <span className="font-semibold text-right text-slate-700">Software Engineer</span>
                            </div>
                        </CardContent>
                        <CardFooter className="p-6 pt-0">
                            <Button
                                variant="brand"
                                size="lg"
                                className="w-full h-12 rounded-xl"
                                onClick={() => router.push(`/my/cover-letters/new?jobId=${recruit.id}`)}
                            >
                                <PenTool className="mr-2 h-4 w-4" />
                                이 공고로 자소서 작성하기
                            </Button>
                        </CardFooter>
                    </Card>

                    <p className="text-xs text-center text-slate-400 leading-relaxed px-4">
                        Pro-NLP AI가 공고 내용을 분석하여<br />
                        합격 확률을 높이는 자소서 초안을 제안합니다.
                    </p>
                </div>
            </div>
        </div>
    );
}
