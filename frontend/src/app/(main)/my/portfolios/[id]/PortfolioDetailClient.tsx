"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { usePolling } from "@/hooks/usePolling";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ExternalLink, FileText, Github, Calendar, Trash2, Edit, Sparkles, User, Code } from "lucide-react";
import Link from "next/link";
import { getApiUrl, fetchWithAuth } from "@/lib/apiUtils";
import { Portfolio } from "@/types";
import { useToast } from "@/components/ui/toast-context";

export default function PortfolioDetailClient({ params }: { params: Promise<{ id: string }> }) {
    const router = useRouter();
    const { id } = use(params);
    const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
    const [loading, setLoading] = useState(true);

    const { toast } = useToast();

    // Polling logic
    const { data: polledData } = usePolling<Portfolio>(
        portfolio?.processingStatus === 'PENDING' ? `/portfolios/${id}` : '',
        3000,
        (data) => data.processingStatus !== 'PENDING'
    );

    // Use polledData as the source of truth when available, otherwise fall back to initial fetch state
    const displayPortfolio = polledData || portfolio;

    useEffect(() => {
        fetchWithAuth(getApiUrl(`/portfolios/${id}`))
            .then(res => {
                if (!res.ok) throw new Error("Not Found");
                return res.json();
            })
            .then(data => {
                setPortfolio(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
                toast("포트폴리오를 불러오는데 실패했습니다.", "error");
            });
    }, [id, toast]);

    const handleDelete = async () => {
        if (confirm("정말로 삭제하시겠습니까?")) {
            try {
                const res = await fetchWithAuth(getApiUrl(`/portfolios/${id}`), {
                    method: 'DELETE',
                });
                if (res.ok) {
                    toast("포트폴리오가 삭제되었습니다.", "success");
                    router.push('/my/portfolios');
                } else {
                    toast("삭제에 실패했습니다.", "error");
                }
            } catch (e) {
                console.error(e);
                toast("삭제 중 오류가 발생했습니다.", "error");
            }
        }
    };

    if (loading) return <div className="flex h-[50vh] items-center justify-center">Loading...</div>;
    if (!displayPortfolio) return <div className="flex h-[50vh] items-center justify-center text-slate-500">포트폴리오를 찾을 수 없습니다.</div>;

    const formatDate = (dateString?: string) => {
        if (!dateString) return "N/A";
        const date = new Date(dateString);
        return isNaN(date.getTime()) ? "N/A" : date.toLocaleDateString();
    };

    const Icon = displayPortfolio.type === 'github' ? Github : displayPortfolio.type === 'file' ? FileText : ExternalLink;

    return (
        <div className="container max-w-4xl mx-auto py-12 px-4 animate-in fade-in zoom-in-95 duration-500">
            <Button variant="ghost" className="mb-6 hover:bg-slate-100 text-slate-500" onClick={() => router.back()}>
                <ArrowLeft className="h-4 w-4 mr-2" /> 목록으로 돌아가기
            </Button>

            <Card className="shadow-lg border-slate-200 bg-white overflow-hidden">
                <CardHeader className="bg-slate-50/50 border-b border-slate-100 p-8">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="bg-white border-slate-200 text-slate-600 px-3 py-1 text-sm font-medium shadow-sm">
                                {displayPortfolio.type === 'link' ? '웹사이트 / 링크' : displayPortfolio.type === 'github' ? 'GitHub 레포지토리' : 'PDF 문서'}
                            </Badge>
                            {displayPortfolio.processingStatus === 'PENDING' && (
                                <Badge variant="outline" className="bg-yellow-50 border-yellow-100 text-yellow-600 text-xs font-bold animate-pulse">
                                    분석 중...
                                </Badge>
                            )}
                            {displayPortfolio.processingStatus === 'COMPLETED' && (
                                <Badge variant="outline" className="bg-blue-50 border-blue-100 text-blue-600 text-xs font-bold gap-1">
                                    <Sparkles className="h-3 w-3 fill-blue-500" /> AI 분석 완료
                                </Badge>
                            )}
                        </div>
                        <span className="text-slate-400 text-sm flex items-center gap-2">
                            <Calendar className="h-4 w-4" />
                            {formatDate(displayPortfolio.createdAt)} 등록
                        </span>
                    </div>
                    <CardTitle className="text-3xl font-bold text-slate-900 leading-tight">
                        {displayPortfolio.project_name}
                    </CardTitle>
                </CardHeader>

                <CardContent className="p-8 space-y-8 min-h-[300px]">

                    {/* Project Details Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2 p-4 bg-slate-50/50 rounded-xl border border-slate-100">
                            <div className="flex items-center gap-2 text-slate-400 text-sm font-bold uppercase tracking-wider">
                                <Calendar className="h-4 w-4" /> Period
                            </div>
                            <p className="font-semibold text-slate-800">{displayPortfolio.period || "기간 정보 없음"}</p>
                        </div>
                        <div className="space-y-2 p-4 bg-slate-50/50 rounded-xl border border-slate-100">
                            <div className="flex items-center gap-2 text-slate-400 text-sm font-bold uppercase tracking-wider">
                                <User className="h-4 w-4" /> Role
                            </div>
                            <p className="font-semibold text-slate-800">{displayPortfolio.role || "역할 정보 없음"}</p>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            <FileText className="h-4 w-4" /> 프로젝트 설명
                        </h3>
                        <p className="text-lg text-slate-700 leading-relaxed whitespace-pre-wrap">
                            {displayPortfolio.description || "설명이 없습니다."}
                        </p>
                    </div>


                    <div className="space-y-3">
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            <Code className="h-4 w-4" /> 기술 스택
                        </h3>
                        {displayPortfolio.tech_stack && displayPortfolio.tech_stack.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                                {displayPortfolio.tech_stack.map((tech, i) => (
                                    <Badge key={i} variant="secondary" className="px-3 py-1 bg-slate-100 text-slate-700 hover:bg-slate-200 text-sm">
                                        {tech}
                                    </Badge>
                                ))}
                            </div>
                        ) : (
                            <p className="text-slate-500 text-sm">기술 스택 정보가 없습니다.</p>
                        )}
                    </div>

                    {/* Job Queries Section */}
                    {displayPortfolio.job_queries && displayPortfolio.job_queries.length > 0 && (
                        <div className="space-y-4 pt-6 border-t border-slate-100">
                            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                <Sparkles className="h-4 w-4 text-purple-500" /> AI 채용 검색 전략
                            </h3>
                            <div className="grid gap-4">
                                {displayPortfolio.job_queries.map((q, i) => (
                                    <div key={i} className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col gap-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <Badge variant={q.type === 'A' ? 'default' : q.type === 'B' ? 'secondary' : 'outline'}
                                                    className={q.type === 'C' ? "border-purple-200 text-purple-600 bg-purple-50" : ""}
                                                >
                                                    Type {q.type}
                                                </Badge>
                                                <span className="text-xs text-slate-500 font-medium">
                                                    {q.type === 'A' ? '핵심 포지션 (Main)' : q.type === 'B' ? '확장 포지션 (Sub)' : '도전 포지션 (Challenge)'}
                                                </span>
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-slate-800 font-bold mb-1">검색 쿼리</p>
                                            <p className="text-slate-700 bg-slate-50 p-2 rounded-md border border-slate-100 text-sm">{q.query_text}</p>
                                        </div>
                                        {q.evidence && q.evidence.length > 0 && (
                                            <div>
                                                <p className="text-xs text-slate-500 font-bold mb-1">추론 근거</p>
                                                <div className="flex flex-wrap gap-1">
                                                    {q.evidence.map((ev, j) => (
                                                        <span key={j} className="inline-block bg-slate-50 text-slate-600 text-[11px] px-2 py-1 rounded border border-slate-100">
                                                            {ev}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}


                    <div className="space-y-4 pt-6 border-t border-slate-100">
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            AI 분석 원본 데이터
                        </h3>
                        {displayPortfolio.content ? (
                            <div className="rounded-2xl border border-slate-100 bg-slate-50/30 p-6 relative group overflow-hidden">
                                <p className="text-[14px] text-slate-600 leading-7 whitespace-pre-line font-medium max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                    {displayPortfolio.content}
                                </p>
                            </div>
                        ) : (
                            <div className="rounded-2xl border border-dashed border-slate-200 p-8 text-center bg-slate-50/30">
                                <p className="text-slate-400 font-medium">상세 내용이 없습니다.</p>
                            </div>
                        )}
                    </div>

                    {(displayPortfolio.url || displayPortfolio.source_url) && (
                        <div className="space-y-3 pt-2">
                            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">연결된 리소스</h3>
                            {displayPortfolio.url && (
                                <a
                                    href={displayPortfolio.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-3 p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-blue-200 hover:text-blue-700 transition-all group w-full"
                                >
                                    <div className="p-2 bg-white rounded-lg border border-slate-200 group-hover:border-blue-200 shadow-sm">
                                        <Icon className="h-6 w-6 text-slate-500 group-hover:text-blue-600 transition-colors" />
                                    </div>
                                    <span className="font-medium truncate flex-1">{displayPortfolio.url}</span>
                                    <ExternalLink className="h-4 w-4 text-slate-400 group-hover:text-blue-400" />
                                </a>
                            )}
                            {displayPortfolio.source_url && displayPortfolio.source_url !== displayPortfolio.url && (
                                <a
                                    href={displayPortfolio.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-3 p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-blue-200 hover:text-blue-700 transition-all group w-full"
                                >
                                    <div className="p-2 bg-white rounded-lg border border-slate-200 group-hover:border-blue-200 shadow-sm">
                                        <Icon className="h-6 w-6 text-slate-500 group-hover:text-blue-600 transition-colors" />
                                    </div>
                                    <span className="font-medium truncate flex-1">{displayPortfolio.source_url}</span>
                                    <ExternalLink className="h-4 w-4 text-slate-400 group-hover:text-blue-400" />
                                </a>
                            )}
                        </div>
                    )}
                </CardContent>

                <CardFooter className="bg-slate-50/30 border-t border-slate-100 p-6 flex justify-end gap-3">
                    <Link href={`/my/portfolios/${displayPortfolio.id}/edit`}>
                        <Button variant="outline" className="border-slate-200 hover:bg-slate-50 text-slate-600">
                            <Edit className="h-4 w-4 mr-2" /> 수정
                        </Button>
                    </Link>
                    <Button variant="destructive" className="bg-red-50 text-red-600 hover:bg-red-100 border border-red-100 shadow-none hover:shadow-sm" onClick={handleDelete}>
                        <Trash2 className="h-4 w-4 mr-2" /> 삭제
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
