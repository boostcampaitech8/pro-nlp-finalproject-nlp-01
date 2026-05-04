"use client";

import { useEffect, useState, use } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Recruit } from "@/types";
import { useRouter } from "next/navigation";
import { Calendar, Building, Briefcase, PenTool, Info, AlignLeft, Flame } from "lucide-react";
import { useAuthStore } from "@/stores/useAuthStore";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { getApiUrl, fetchWithAuth } from "@/lib/apiUtils";

interface RecruitDetail extends Recruit {
    content: string;
}

interface ExistingDoc {
    id: number;
    title: string;
    updated_at: string;
}

export default function RecruitDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const router = useRouter();
    const { id } = use(params);
    const { isAuthenticated } = useAuthStore();
    const [recruit, setRecruit] = useState<RecruitDetail | null>(null);
    const [existingDocs, setExistingDocs] = useState<ExistingDoc[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchWithAuth(getApiUrl(`/recruits/${id}`))
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
            fetchWithAuth(getApiUrl(`/cover-letters?recruit_id=${id}`), { cache: 'no-store' })
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
                <h1 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight mb-4">
                    {recruit.title}
                </h1>
                <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="px-3 py-1 text-sm font-medium bg-white border-slate-200 text-slate-600 gap-1.5 shadow-sm">
                        <Building className="h-3.5 w-3.5" />
                        {recruit.company}
                    </Badge>
                    {recruit.tags?.map(tag => (
                        <Badge key={tag} variant="secondary" className="px-3 py-1 text-sm font-medium bg-slate-100 text-slate-600">
                            {tag}
                        </Badge>
                    )) || null}
                </div>
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
                            {/* Key Responsibilities */}
                            {recruit.key_responsibilities && (
                                <div className="mb-8">
                                    <h3 className="text-xl font-bold text-slate-900 mb-3 flex items-center gap-2">
                                        <Briefcase className="h-5 w-5 text-blue-600" />
                                        주요 업무
                                    </h3>
                                    <div className="bg-slate-50 p-5 rounded-xl border border-slate-100 text-base">
                                        {recruit.key_responsibilities}
                                    </div>
                                </div>
                            )}

                            {/* Qualifications Section */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                                {recruit.required_qualifications && (
                                    <div className="space-y-3">
                                        <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                                            자격 요건
                                        </h3>
                                        <div className="bg-red-50/50 p-4 rounded-lg border border-red-100 text-sm md:text-base text-slate-700">
                                            {recruit.required_qualifications}
                                        </div>
                                    </div>
                                )}
                                {recruit.preferred_qualifications && (
                                    <div className="space-y-3">
                                        <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                                            우대 사항
                                        </h3>
                                        <div className="bg-blue-50/50 p-4 rounded-lg border border-blue-100 text-sm md:text-base text-slate-700">
                                            {recruit.preferred_qualifications}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Original Content / Misc */}
                            {recruit.content && (
                                <div className="mt-8 pt-8 border-t border-slate-100">
                                    <h3 className="text-lg font-bold text-slate-900 mb-4">상세 내용</h3>
                                    <div className="text-base text-slate-600">
                                        {recruit.content}
                                    </div>
                                </div>
                            )}
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
                                {existingDocs?.map((doc) => (
                                    <li key={doc.id}>
                                        <Link href={`/my/cover-letters/${doc.id}`} className="block bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-200 transition-all group shadow-sm hover:shadow-md">
                                            <div className="font-medium text-sm text-slate-900 group-hover:text-blue-600 truncate transition-colors">{doc.title}</div>
                                            <div className="text-xs text-slate-400 mt-1">{doc.updated_at} 저장됨</div>
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
                        <CardContent className="space-y-6 p-6 text-sm">
                            <div className="flex justify-between items-start pb-3 border-b border-slate-100 border-dashed gap-4">
                                <span className="text-slate-500 flex items-center gap-2 whitespace-nowrap shrink-0">
                                    <Building className="h-4 w-4" /> 기업명
                                </span>
                                <span className="font-semibold text-right text-slate-700">{recruit.company}</span>
                            </div>

                            <div className="flex flex-col gap-2 pb-3 border-b border-slate-100 border-dashed">
                                <span className="text-slate-500 flex items-center gap-2 whitespace-nowrap shrink-0">
                                    <Calendar className="h-4 w-4" /> 채용 기간
                                </span>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-slate-400 font-medium">{recruit.start_date || "정보 없음"}</span>
                                    <span className="text-xs text-slate-300">~</span>
                                    <span className={cn(
                                        "font-bold text-right",
                                        recruit.deadline && new Date(recruit.deadline) < new Date() ? "text-slate-400 line-through" : "text-red-500"
                                    )}>{recruit.deadline || "채용 시 마감"}</span>
                                </div>
                            </div>

                            {/* New Detailed Fields in Sidebar */}
                            {recruit.experience && (
                                <div className="flex justify-between items-start pb-3 border-b border-slate-100 border-dashed">
                                    <span className="text-slate-500 whitespace-nowrap shrink-0">경력</span>
                                    <span className="font-semibold text-right text-slate-700 break-keep">{recruit.experience}</span>
                                </div>
                            )}
                            {recruit.education && (
                                <div className="flex justify-between items-start pb-3 border-b border-slate-100 border-dashed">
                                    <span className="text-slate-500 whitespace-nowrap shrink-0">학력</span>
                                    <span className="font-semibold text-right text-slate-700 break-keep">{recruit.education}</span>
                                </div>
                            )}
                            {recruit.employment_type && (
                                <div className="flex justify-between items-start pb-3 border-b border-slate-100 border-dashed">
                                    <span className="text-slate-500 whitespace-nowrap shrink-0">고용 형태</span>
                                    <span className="font-semibold text-right text-slate-700 break-keep">{recruit.employment_type}</span>
                                </div>
                            )}
                            {recruit.salary && (
                                <div className="flex justify-between items-start pb-3 border-b border-slate-100 border-dashed">
                                    <span className="text-slate-500 whitespace-nowrap shrink-0">급여</span>
                                    <span className="font-semibold text-right text-slate-700 break-keep">{recruit.salary}</span>
                                </div>
                            )}
                            {recruit.category && (
                                <div className="flex justify-between items-start pb-3 border-b border-slate-100 border-dashed">
                                    <span className="text-slate-500 whitespace-nowrap shrink-0">분야</span>
                                    <span className="font-semibold text-right text-slate-700 break-keep">{recruit.category}</span>
                                </div>
                            )}
                            {recruit.location && (
                                <div className="flex justify-between items-start pb-3 border-b border-slate-100 border-dashed">
                                    <span className="text-slate-500 whitespace-nowrap shrink-0">근무지</span>
                                    <span className="font-semibold text-right text-slate-700 break-keep">{recruit.location}</span>
                                </div>
                            )}

                            <div className="flex justify-between items-center pb-3 border-b border-slate-100 border-dashed gap-4">
                                <span className="text-slate-500 flex items-center gap-2 whitespace-nowrap shrink-0">
                                    <Flame className="h-4 w-4 text-orange-500" /> 총 조회수
                                </span>
                                <span className="font-bold text-right text-orange-600">{(recruit.view_count || 0).toLocaleString()}회</span>
                            </div>

                            {recruit.link && (
                                <div className="pt-2">
                                    <a href={recruit.link} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs flex items-center justify-end gap-1">
                                        원문 공고 보러가기 →
                                    </a>
                                </div>
                            )}
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
                        <span className="font-pretendard font-black text-slate-500">모두취업</span> AI가 공고 내용을 분석하여<br />
                        합격 확률을 높이는 자소서 초안을 제안합니다.
                    </p>
                </div>
            </div>
        </div>
    );
}
