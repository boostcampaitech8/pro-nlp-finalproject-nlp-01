import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Upload, Github, Sparkles, ExternalLink, Plus, Loader2, Save, Briefcase, Calendar, Code, User, FileText } from "lucide-react";
import { portfolioApi } from "@/lib/portfolioApi";
import { Portfolio } from "@/types";

export default function NewPortfolioPage() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // Form States
    const [githubUrl, setGithubUrl] = useState("");
    const [notionUrl, setNotionUrl] = useState("");

    // Preview State
    const [previewData, setPreviewData] = useState<Partial<Portfolio> | null>(null);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setIsAnalyzing(true);
            try {
                await portfolioApi.uploadFile(e.target.files[0]);
                alert("파일이 업로드되었습니다. AI가 배경에서 분석을 시작했습니다.");
                router.push('/my/portfolios');
            } catch (err) {
                console.error(err);
                alert(`업로드 실패: ${err instanceof Error ? err.message : "Unknown error"}`);
            } finally {
                setIsAnalyzing(false);
            }
        }
    };

    const handleGithubAnalyze = async (url: string) => {
        if (!url) {
            alert("GitHub URL을 입력해주세요.");
            return;
        }
        setIsAnalyzing(true);
        try {
            const result = await portfolioApi.analyzePortfolio(url, "github");
            // Map LLM result to Portfolio structure
            const user_data = result.user_data;
            const p0 = user_data.projects[0] || {};
            setPreviewData({
                title: `${githubUrl.split('/').pop()} Analysis`,
                type: 'github',
                source_url: githubUrl,
                extracted_summary: user_data.profile.summary,
                extracted_job_title: user_data.profile.job_title,
                project_name: p0.project_name,
                period: p0.period,
                role: p0.role,
                description: p0.description_for_embedding,
                tech_stack: p0.tech_stack,
                content: result.raw_text // If backend provides it
            });
        } catch (err) {
            console.error(err);
            alert(`분석 실패: ${err instanceof Error ? err.message : "Unknown error"}`);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleFinalSave = async () => {
        if (!previewData) return;
        setIsSaving(true);
        try {
            await portfolioApi.createPortfolio(previewData);
            alert("포트폴리오가 성공적으로 저장되었습니다.");
            router.push('/my/portfolios');
        } catch (err) {
            console.error(err);
            alert(`저장 실패: ${err instanceof Error ? err.message : "Unknown error"}`);
        } finally {
            setIsSaving(false);
        }
    };

    if (isAnalyzing) {
        return (
            <div className="flex flex-col h-[70vh] items-center justify-center space-y-10 animate-in fade-in duration-700">
                <div className="relative">
                    <div className="h-28 w-28 rounded-full border-[6px] border-slate-100 border-t-blue-500 animate-spin" />
                    <Sparkles className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-10 w-10 text-blue-500 fill-blue-500 animate-pulse" />
                </div>
                <div className="text-center space-y-4 max-w-lg">
                    <h2 className="text-3xl font-bold text-slate-900 tracking-tight">AI 데이터 정제 중...</h2>
                    <p className="text-slate-500 leading-relaxed font-medium">GitHub에서 데이터를 가져와 AI가 프로젝트를 추출하고 있습니다.</p>
                </div>
            </div>
        );
    }

    if (previewData) {
        return (
            <div className="container max-w-4xl mx-auto py-12 px-4 space-y-8 animate-in fade-in zoom-in-95 duration-500">
                <div className="flex items-center justify-between">
                    <Button variant="ghost" onClick={() => setPreviewData(null)} className="text-slate-500">
                        <ArrowLeft className="h-4 w-4 mr-2" /> 다시 입력하기
                    </Button>
                    <Badge variant="outline" className="bg-blue-50 border-blue-100 text-blue-600 font-bold">AI PREVIEW MODE</Badge>
                </div>

                <div className="space-y-6">
                    <Card className="shadow-2xl border-blue-100 ring-4 ring-blue-500/5">
                        <CardHeader className="bg-slate-50/50 border-b border-slate-100 p-8">
                            <CardTitle className="text-2xl font-bold text-slate-900">분석 결과 검토</CardTitle>
                            <CardDescription>AI가 추출한 내용을 확인하고 수정하세요. 저장 버튼을 눌러야 최종 반영됩니다.</CardDescription>
                        </CardHeader>
                        <CardContent className="p-8 space-y-8">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 bg-blue-50/30 rounded-2xl border border-blue-100">
                                <div className="md:col-span-2 space-y-2">
                                    <Label className="font-bold text-blue-700 text-xs uppercase">프로젝트 명</Label>
                                    <Input
                                        value={previewData.project_name || ""}
                                        onChange={e => setPreviewData({ ...previewData, project_name: e.target.value })}
                                        className="bg-white border-blue-100"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="font-bold text-slate-500 text-xs uppercase">기간</Label>
                                    <Input
                                        value={previewData.period || ""}
                                        onChange={e => setPreviewData({ ...previewData, period: e.target.value })}
                                        className="bg-white"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="font-bold text-slate-500 text-xs uppercase">역할</Label>
                                    <Input
                                        value={previewData.role || ""}
                                        onChange={e => setPreviewData({ ...previewData, role: e.target.value })}
                                        className="bg-white"
                                    />
                                </div>
                            </div>

                            <div className="space-y-3">
                                <Label className="font-bold text-slate-500 text-xs uppercase flex items-center gap-2">
                                    <Sparkles className="h-3 w-3" /> 프로젝트 상세 설명 (임베딩용)
                                </Label>
                                <Textarea
                                    className="min-h-[200px] leading-relaxed"
                                    value={previewData.description || ""}
                                    onChange={e => setPreviewData({ ...previewData, description: e.target.value })}
                                />
                            </div>

                            <div className="space-y-3">
                                <Label className="font-bold text-slate-500 text-xs uppercase">기술 스택 (쉼표 구분)</Label>
                                <Input
                                    value={previewData.tech_stack?.join(", ") || ""}
                                    onChange={e => setPreviewData({ ...previewData, tech_stack: e.target.value.split(",").map(s => s.trim()) })}
                                />
                            </div>
                        </CardContent>
                        <CardFooter className="bg-slate-50/50 border-t border-slate-100 p-6 flex justify-end gap-3">
                            <Button variant="outline" onClick={() => setPreviewData(null)} disabled={isSaving}>취소</Button>
                            <Button variant="brand" onClick={handleFinalSave} disabled={isSaving} className="px-10 font-bold shadow-lg shadow-blue-500/20">
                                {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
                                최종 확인 및 저장
                            </Button>
                        </CardFooter>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="container max-w-4xl mx-auto py-12 px-4 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center space-x-2 mb-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()} className="-ml-3 hover:bg-slate-100 text-slate-400">
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">포트폴리오 신규 등록</h1>
                    <p className="text-sm text-slate-500">데이터를 연결하면 AI가 자동으로 경험을 분석하고 최적화해 드립니다.</p>
                </div>
            </div>

            <Tabs defaultValue="github" className="w-full">
                <TabsList className="grid w-full grid-cols-3 mb-10 bg-slate-100 p-1 rounded-2xl">
                    <TabsTrigger value="github" className="rounded-xl data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all font-bold">GitHub</TabsTrigger>
                    <TabsTrigger value="notion" className="rounded-xl data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all font-bold">Notion</TabsTrigger>
                    <TabsTrigger value="file" className="rounded-xl data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all font-bold">PDF / Files</TabsTrigger>
                </TabsList>

                <div className="grid gap-6">
                    <TabsContent value="github">
                        <Card className="border-slate-200 shadow-sm border-2 overflow-hidden hover:border-blue-200 transition-colors bg-white">
                            <CardHeader className="p-8">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 bg-slate-900 rounded-2xl">
                                        <Github className="h-8 w-8 text-white" />
                                    </div>
                                    <div className="flex-1">
                                        <CardTitle className="text-xl font-bold text-slate-900">GitHub 리포지토리 분석</CardTitle>
                                        <CardDescription className="text-slate-500">전체 프로필 또는 특정 레포를 분석하여 포트폴리오를 생성합니다.</CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="px-8 pb-8 space-y-6">
                                <div className="p-6 rounded-2xl border border-slate-100 bg-slate-50/50 space-y-4">
                                    <Label className="font-bold text-slate-700">리포지토리 또는 프로필 URL</Label>
                                    <div className="flex gap-2">
                                        <Input
                                            placeholder="https://github.com/..."
                                            className="border-slate-200 bg-white focus-visible:ring-blue-500 h-11"
                                            value={githubUrl}
                                            onChange={(e) => setGithubUrl(e.target.value)}
                                        />
                                        <Button onClick={() => handleGithubAnalyze(githubUrl)} className="bg-blue-600 hover:bg-blue-700 text-white font-bold h-11 px-6 rounded-xl transition-all">
                                            연동 및 분석
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                    {/* Placeholder for others */}
                    <TabsContent value="notion">
                        <Card className="border-slate-200 shadow-sm border-2 overflow-hidden bg-white">
                            <CardContent className="p-16 text-center">
                                <p className="text-slate-500">노션 연동은 준비 중입니다. 위 탭에서 GitHub을 먼저 이용해 보세요!</p>
                            </CardContent>
                        </Card>
                    </TabsContent>
                    <TabsContent value="file">
                        <Card className="border-slate-200 shadow-sm border-2 overflow-hidden bg-white">
                            <CardContent className="p-16 text-center">
                                <p className="text-slate-500">파일 업로드는 준비 중입니다. 위 탭에서 GitHub을 먼저 이용해 보세요!</p>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
}
