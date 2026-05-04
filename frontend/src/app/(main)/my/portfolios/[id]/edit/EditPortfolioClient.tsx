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
import { getApiUrl, fetchWithAuth } from "@/lib/apiUtils";


export default function EditPortfolioPage({ params }: { params: Promise<{ id: string }> }) {
    const router = useRouter();
    const { id } = use(params);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [description, setDescription] = useState("");
    const [content, setContent] = useState("");
    const [url, setUrl] = useState("");
    const [type, setType] = useState<'link' | 'file' | 'github'>('link');

    // Updated Fields
    const [projectName, setProjectName] = useState("");
    const [period, setPeriod] = useState("");
    const [role, setRole] = useState("");
    const [sourceUrl, setSourceUrl] = useState(""); // Unified source_url
    const [techStack, setTechStack] = useState(""); // Comma separated string for editing

    useEffect(() => {
        fetchWithAuth(getApiUrl(`/portfolios/${id}`))
            .then(res => res.json())
            .then(data => {
                setDescription(data.description || "");
                setContent(data.content || "");
                setUrl(data.url || "");
                setType(data.type);

                // Flattened fields (Snake Case align)
                setProjectName(data.project_name || "");
                setPeriod(data.period || "");
                setRole(data.role || "");
                setSourceUrl(data.source_url || "");
                setTechStack(Array.isArray(data.tech_stack) ? data.tech_stack.join(", ") : "");

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
            const payload = {
                description,
                content,
                url,
                project_name: projectName,
                period,
                role,
                source_url: sourceUrl,
                tech_stack: techStack.split(",").map(s => s.trim()).filter(Boolean)
            };

            const res = await fetchWithAuth(getApiUrl(`/portfolios/${id}`), {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
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
                    <CardTitle className="text-2xl font-bold text-slate-900 leading-tight">
                        {projectName || "프로젝트 수정"}
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-8 space-y-8">
                    {/* Project Metadata Section */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 bg-slate-50/30 rounded-2xl border border-slate-100">
                        <div className="md:col-span-2 space-y-2">
                            <Label htmlFor="projectName" className="text-slate-500 font-bold text-xs uppercase tracking-wider">프로젝트 명</Label>
                            <Input
                                id="projectName"
                                value={projectName}
                                onChange={(e) => setProjectName(e.target.value)}
                                placeholder="실제 프로젝트 이름"
                                className="border-slate-200 focus-visible:ring-blue-500 bg-white"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="period" className="text-slate-500 font-bold text-xs uppercase tracking-wider">기간 (Period)</Label>
                            <Input
                                id="period"
                                value={period}
                                onChange={(e) => setPeriod(e.target.value)}
                                placeholder="예: 2023.01 - 2023.06"
                                className="border-slate-200 focus-visible:ring-blue-500 bg-white"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="role" className="text-slate-500 font-bold text-xs uppercase tracking-wider">역할 (Role)</Label>
                            <Input
                                id="role"
                                value={role}
                                onChange={(e) => setRole(e.target.value)}
                                placeholder="예: Backend Developer"
                                className="border-slate-200 focus-visible:ring-blue-500 bg-white"
                            />
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <Label htmlFor="techStack" className="text-slate-500 font-bold text-xs uppercase tracking-wider">기술 스택 (쉼표로 구분)</Label>
                            <Input
                                id="techStack"
                                value={techStack}
                                onChange={(e) => setTechStack(e.target.value)}
                                placeholder="Python, React, AWS..."
                                className="border-slate-200 focus-visible:ring-blue-500 bg-white"
                            />
                        </div>
                    </div>

                    <div className="space-y-2 p-6 bg-slate-50/30 rounded-2xl border border-slate-100">
                        <Label htmlFor="sourceUrl" className="text-slate-500 font-bold text-xs uppercase tracking-wider">소스 주소 (Source URL)</Label>
                        <Input
                            id="sourceUrl"
                            value={sourceUrl}
                            onChange={(e) => setSourceUrl(e.target.value)}
                            placeholder="https://github.com/..."
                            className="border-slate-200 focus-visible:ring-blue-500 bg-white"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="desc" className="text-slate-500 font-bold text-xs uppercase tracking-wider">프로젝트 설명</Label>
                        <Textarea
                            id="desc"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="이 프로젝트에 대한 핵심 요약이나 설명을 입력하세요."
                            className="min-h-[350px] border-slate-200 focus-visible:ring-blue-500 text-base leading-relaxed"
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
