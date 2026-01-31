"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Github, Upload, Loader2 } from "lucide-react";
import { portfolioApi } from "@/lib/portfolioApi";
import { useToast } from "@/components/ui/toast-context";

export default function NewPortfolioPage() {
    const router = useRouter();
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const { toast } = useToast();

    // Form States
    const [githubUrl, setGithubUrl] = useState("");

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleGithubAnalyze = async (url: string) => {
        if (!url) {
            toast("GitHub URL을 입력해주세요.", "warning");
            return;
        }
        setIsAnalyzing(true);
        try {
            const initialResult = await portfolioApi.analyzePortfolio(url, "github");
            if (!initialResult.success || !initialResult.portfolio_id) {
                throw new Error(initialResult.error || "분석 요청에 실패했습니다.");
            }

            toast("분석이 시작되었습니다. 완료되면 알림으로 알려드릴게요!", "success");
            router.push('/my/portfolios');
        } catch (err) {
            console.error(err);
            toast(`분석 실패: ${err instanceof Error ? err.message : "Unknown error"}`, "error");
            setIsAnalyzing(false);
        }
    };

    const handleFileAnalyze = async (file: File) => {
        if (!file) return;
        setIsAnalyzing(true);
        try {
            const initialResult = await portfolioApi.analyzePortfolioFile(file);
            if (!initialResult.success || !initialResult.portfolio_id) {
                throw new Error(initialResult.error || "파일 분석 요청에 실패했습니다.");
            }

            toast("파일 분석이 시작되었습니다. 리스트에서 확인하실 수 있습니다.", "success");
            router.push('/my/portfolios');
        } catch (err) {
            console.error(err);
            toast(`파일 분석 실패: ${err instanceof Error ? err.message : "Unknown error"}`, "error");
            setIsAnalyzing(false);
        }
    };


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
                                        <Button
                                            onClick={() => handleGithubAnalyze(githubUrl)}
                                            disabled={isAnalyzing}
                                            className="bg-blue-600 hover:bg-blue-700 text-white font-bold h-11 px-6 rounded-xl transition-all"
                                        >
                                            {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
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
                        <div
                            className="border-2 border-dashed border-slate-200 rounded-3xl p-16 text-center hover:border-blue-400 transition-all cursor-pointer bg-white group"
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                className="hidden"
                                accept=".pdf,.txt,.md"
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) handleFileAnalyze(file);
                                }}
                            />
                            <div className="flex flex-col items-center">
                                <div className="h-20 w-20 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-300">
                                    <Upload className="h-10 w-10 text-slate-400 group-hover:text-blue-500" />
                                </div>
                                <h3 className="mt-6 text-xl font-bold text-slate-900">파일 업로드 (PDF, TXT, MD)</h3>
                                <p className="mt-2 text-slate-500 font-medium">포트폴리오 파일을 선택하거나 이 영역으로 드래그하세요.</p>
                                <div className="mt-8 flex gap-2">
                                    <Badge variant="outline" className="text-slate-400 border-slate-200">PDF</Badge>
                                    <Badge variant="outline" className="text-slate-400 border-slate-200">TXT</Badge>
                                    <Badge variant="outline" className="text-slate-400 border-slate-200">Markdown</Badge>
                                </div>
                            </div>
                        </div>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
}
