"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ExternalLink, FileText, Github, Calendar, Trash2, Edit } from "lucide-react";
import Link from "next/link";

interface Portfolio {
    id: number;
    title: string;
    type: 'link' | 'file' | 'github';
    url?: string;
    createdAt: string;
    description: string;
    content?: string;
}

export default function PortfolioDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const router = useRouter();
    const { id } = use(params);
    const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`/api/portfolios/${id}`)
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
            });
    }, [id]);

    const handleDelete = () => {
        if (confirm("정말로 삭제하시겠습니까?")) {
            alert("삭제되었습니다. (Mock)");
            router.push('/my/portfolios');
        }
    };

    if (loading) return <div className="flex h-[50vh] items-center justify-center">Loading...</div>;
    if (!portfolio) return <div className="flex h-[50vh] items-center justify-center text-slate-500">포트폴리오를 찾을 수 없습니다.</div>;

    const Icon = portfolio.type === 'github' ? Github : portfolio.type === 'file' ? FileText : ExternalLink;

    return (
        <div className="container max-w-4xl mx-auto py-12 px-4 animate-in fade-in zoom-in-95 duration-500">
            <Button variant="ghost" className="mb-6 hover:bg-slate-100 text-slate-500" onClick={() => router.back()}>
                <ArrowLeft className="h-4 w-4 mr-2" /> 목록으로 돌아가기
            </Button>

            <Card className="shadow-lg border-slate-200 bg-white overflow-hidden">
                <CardHeader className="bg-slate-50/50 border-b border-slate-100 p-8">
                    <div className="flex items-center justify-between mb-4">
                        <Badge variant="secondary" className="bg-white border-slate-200 text-slate-600 px-3 py-1 text-sm font-medium shadow-sm">
                            {portfolio.type === 'link' ? '웹사이트 / 링크' : portfolio.type === 'github' ? 'GitHub 레포지토리' : 'PDF 문서'}
                        </Badge>
                        <span className="text-slate-400 text-sm flex items-center gap-2">
                            <Calendar className="h-4 w-4" />
                            {portfolio.createdAt} 등록
                        </span>
                    </div>
                    <CardTitle className="text-3xl font-bold text-slate-900 leading-tight">
                        {portfolio.title}
                    </CardTitle>
                </CardHeader>

                <CardContent className="p-8 space-y-10 min-h-[300px]">
                    <div className="space-y-3">
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            기본 설명
                        </h3>
                        <p className="text-lg text-slate-700 leading-relaxed whitespace-pre-wrap">
                            {portfolio.description}
                        </p>
                    </div>

                    <div className="space-y-4">
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            AI 분석용 상세 데이터
                        </h3>
                        {portfolio.content ? (
                            <div className="rounded-2xl border border-blue-100 bg-blue-50/20 p-6 relative group overflow-hidden">
                                <div className="absolute top-0 right-0 p-3 bg-blue-100/50 rounded-bl-xl opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Badge variant="outline" className="bg-white border-blue-200 text-blue-600 text-[10px] font-bold">AI 최적화 완료</Badge>
                                </div>
                                <p className="text-[15px] text-slate-800 leading-8 whitespace-pre-line font-medium">
                                    {portfolio.content}
                                </p>
                            </div>
                        ) : (
                            <div className="rounded-2xl border border-dashed border-slate-200 p-12 text-center bg-slate-50/30">
                                <p className="text-slate-400 font-medium">상세 내용이 등록되지 않았습니다.</p>
                                <Button variant="link" className="text-blue-500 mt-2">지금 추가하기</Button>
                            </div>
                        )}
                    </div>

                    {portfolio.url && (
                        <div className="space-y-3 pt-2">
                            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">연결된 리소스</h3>
                            <a
                                href={portfolio.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-3 p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-blue-200 hover:text-blue-700 transition-all group w-full"
                            >
                                <div className="p-2 bg-white rounded-lg border border-slate-200 group-hover:border-blue-200 shadow-sm">
                                    <Icon className="h-6 w-6 text-slate-500 group-hover:text-blue-600 transition-colors" />
                                </div>
                                <span className="font-medium truncate flex-1">{portfolio.url}</span>
                                <ExternalLink className="h-4 w-4 text-slate-400 group-hover:text-blue-400" />
                            </a>
                        </div>
                    )}
                </CardContent>

                <CardFooter className="bg-slate-50/30 border-t border-slate-100 p-6 flex justify-end gap-3">
                    <Link href={`/my/portfolios/${portfolio.id}/edit`}>
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
