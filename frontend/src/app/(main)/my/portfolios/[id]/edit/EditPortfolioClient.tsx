"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Save, Loader2 } from "lucide-react";


export default function EditPortfolioPage({ params }: { params: Promise<{ id: string }> }) {
    const router = useRouter();
    const { id } = use(params);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [content, setContent] = useState("");
    const [url, setUrl] = useState("");
    const [type, setType] = useState<'link' | 'file' | 'github'>('link');

    useEffect(() => {
        fetch(`/api/portfolios/${id}`)
            .then(res => res.json())
            .then(data => {
                setTitle(data.title);
                setDescription(data.description || "");
                setContent(data.content || "");
                setUrl(data.url || "");
                setType(data.type);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, [id]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`/api/portfolios/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, description, content, url })
            });

            if (res.ok) {
                alert("수정되었습니다.");
                router.push(`/my/portfolios/${id}`);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="flex h-[50vh] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;

    return (
        <div className="container max-w-3xl mx-auto py-12 px-4 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center space-x-2 mb-6">
                <Button variant="ghost" size="icon" onClick={() => router.back()} className="-ml-2">
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">포트폴리오 수정</h1>
                    <p className="text-sm text-slate-500 mt-1">포트폴리오 정보를 최신화하여 AI 분석 품질을 높이세요.</p>
                </div>
            </div>

            <Card className="border-slate-200 shadow-xl overflow-hidden">
                <CardHeader className="bg-slate-50/50 border-b border-slate-100 p-8">
                    <div className="flex items-center gap-3 mb-2">
                        <Badge variant="secondary" className="bg-white border-slate-200 text-slate-600">
                            {type === 'link' ? '웹사이트 / 링크' : type === 'github' ? 'GitHub 레포지토리' : 'PDF 문서'}
                        </Badge>
                    </div>
                    <CardTitle>
                        <Input
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className="text-2xl font-bold bg-transparent border-none p-0 focus-visible:ring-0 placeholder:text-slate-300"
                            placeholder="포트폴리오 제목을 입력하세요"
                        />
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-8 space-y-8">
                    <div className="space-y-2">
                        <Label htmlFor="url" className="text-slate-500 font-bold text-xs uppercase tracking-wider">연결 주소 (URL)</Label>
                        <Input
                            id="url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://example.com"
                            className="border-slate-200 focus-visible:ring-blue-500 bg-slate-50/30"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="desc" className="text-slate-500 font-bold text-xs uppercase tracking-wider">기본 설명</Label>
                        <Input
                            id="desc"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="이 포트폴리오에 대한 간단한 설명을 입력하세요."
                            className="border-slate-200 focus-visible:ring-blue-500"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="content" className="flex items-center gap-2 text-blue-600 font-bold text-xs uppercase tracking-wider">
                            상세 데이터 (AI 분석용)
                            <Badge variant="outline" className="text-[10px] bg-blue-50 border-blue-100 uppercase">Recommended</Badge>
                        </Label>
                        <Textarea
                            id="content"
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            placeholder="AI가 참고할 상세 리드미, 프로젝트 요약, 주요 성과 등을 자유롭게 입력하세요."
                            className="min-h-[300px] border-slate-200 focus-visible:ring-blue-500 bg-slate-50/30 leading-relaxed"
                        />
                    </div>
                </CardContent>
                <CardFooter className="bg-slate-50/30 border-t border-slate-100 p-6 flex justify-end gap-3">
                    <Button variant="outline" onClick={() => router.back()} disabled={saving} className="border-slate-200">취소</Button>
                    <Button variant="brand" onClick={handleSave} disabled={saving} className="px-8 font-bold">
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
                        변경사항 저장
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
