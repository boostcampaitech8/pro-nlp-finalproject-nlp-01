"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Github, Upload, Loader2, BookOpen, Settings, Database, Library, ExternalLink, RefreshCw, Sparkles } from "lucide-react";
import { portfolioApi } from "@/lib/portfolioApi";
import { integrationApi, IntegrationRepo, UserIntegration, NotionPage } from "@/lib/integrationApi";
import { useToast } from "@/components/ui/toast-context";
import { useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";

export default function NewPortfolioPage() {
    const router = useRouter();
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const { toast } = useToast();

    // Form States
    const [githubUrl, setGithubUrl] = useState("");
    const [blogUrl, setBlogUrl] = useState("");
    const [notionUrl, setNotionUrl] = useState("");

    // Integration States
    const [integrations, setIntegrations] = useState<UserIntegration[]>([]);
    const [githubRepos, setGithubRepos] = useState<IntegrationRepo[]>([]);
    const [notionPages, setNotionPages] = useState<NotionPage[]>([]);
    const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);

    const loadGithubRepos = useCallback(async () => {
        setIsLoadingIntegrations(true);
        try {
            const repos = await integrationApi.fetchGithubRepos();
            setGithubRepos(repos);
        } catch (err) {
            console.error(err);
        } finally {
            setIsLoadingIntegrations(false);
        }
    }, []);

    const loadNotionPages = useCallback(async () => {
        setIsLoadingIntegrations(true);
        try {
            const pages = await integrationApi.fetchNotionPages();
            setNotionPages(pages);
        } catch (err) {
            console.error(err);
        } finally {
            setIsLoadingIntegrations(false);
        }
    }, []);

    const loadIntegrations = useCallback(async () => {
        try {
            const data = await integrationApi.fetchIntegrations();
            setIntegrations(data);
            if (data.find(i => i.provider === 'github')) {
                loadGithubRepos();
            }
            if (data.find(i => i.provider === 'notion')) {
                loadNotionPages();
            }
        } catch (err) {
            console.error("Failed to load integrations", err);
        }
    }, [loadGithubRepos, loadNotionPages]);

    useEffect(() => {
        loadIntegrations();
    }, [loadIntegrations]);

    const handleGithubConnect = async () => {
        try {
            const url = await integrationApi.getGithubAuthUrl();
            window.location.href = url;
        } catch (err) {
            console.error("Failed to get GitHub auth URL:", err);
            toast("GitHub 연동 URL을 가져오는데 실패했습니다.", "error");
        }
    };

    const githubIntegration = integrations.find(i => i.provider === 'github');
    const notionIntegration = integrations.find(i => i.provider === 'notion');

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleGithubAnalyze = async (url: string) => {
        if (!url) {
            toast("GitHub URL을 입력해주세요.", "warning");
            return;
        }
        setIsAnalyzing(true);
        try {
            // Use importGithub which triggers the background job directly
            await portfolioApi.importGithub(url, "GitHub Project");
            toast("분석이 시작되었습니다. 소스 코드까지 꼼꼼히 훑어볼게요!", "success");
            router.push('/my/portfolios');
        } catch (err) {
            console.error(err);
            toast(`분석 실패: ${err instanceof Error ? err.message : "Unknown error"}`, "error");
            setIsAnalyzing(false);
        }
    };

    const handleBlogAnalyze = async (url: string) => {
        if (!url) {
            toast("블로그 URL을 입력해주세요.", "warning");
            return;
        }
        setIsAnalyzing(true);
        try {
            await portfolioApi.importBlog(url, "Blog Projects");
            toast("블로그 분석이 시작되었습니다. 개별 포스팅들을 가져올게요!", "success");
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

    const handleNotionConnect = async () => {
        try {
            const url = await integrationApi.getNotionAuthUrl();
            window.location.href = url;
        } catch (err) {
            console.error("Failed to get Notion auth URL:", err);
            toast("Notion 연동 URL을 가져오는데 실패했습니다.", "error");
        }
    };

    const handleNotionAnalyze = async (url: string = "all") => {
        // Check if Notion is connected
        const notionIntegration = integrations.find(i => i.provider === 'notion');

        if (!notionIntegration) {
            // Trigger OAuth if not connected
            toast("먼저 Notion 워크스페이스를 연동해주세요.", "warning");
            await handleNotionConnect();
            return;
        }

        setIsAnalyzing(true);
        try {
            // "all" means workspace search
            await portfolioApi.importNotion(url, url === "all" ? "Notion Workspace" : "Notion Page");
            toast(url === "all" ? "워크스페이스 전체 분석이 시작되었습니다." : "노션 페이지 분석이 시작되었습니다.", "success");
            router.push('/my/portfolios');
        } catch (err) {
            console.error(err);
            toast(`분석 실패: ${err instanceof Error ? err.message : "Unknown error"}`, "error");
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
                <TabsList className="grid w-full grid-cols-4 mb-10 bg-slate-100 p-1 rounded-2xl">
                    <TabsTrigger value="github" className="rounded-xl data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all font-bold">GitHub</TabsTrigger>
                    <TabsTrigger value="blog" className="rounded-xl data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all font-bold">Blog</TabsTrigger>
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
                                    <div className="flex justify-between items-center mb-1">
                                        <Label className="font-bold text-slate-700">리포지토리 또는 프로필 URL</Label>
                                    </div>
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
                                            URL 분석 및 등록
                                        </Button>
                                    </div>

                                    {!githubIntegration && (
                                        <div className="p-4 mt-2 bg-blue-50/50 border border-blue-100 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
                                            <div className="text-sm text-blue-700 font-medium">
                                                <Sparkles className="h-4 w-4 inline mr-2 text-blue-500" />
                                                GitHub 계정을 연동하면 **모든 Repository(Private 포함)**를 한눈에 보고 선택할 수 있습니다.
                                            </div>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="rounded-xl border-blue-500 text-blue-600 hover:bg-blue-50 h-10 w-full sm:w-auto shrink-0 font-bold bg-white"
                                                onClick={handleGithubConnect}
                                            >
                                                <Github className="h-4 w-4 mr-2" />
                                                GitHub 연동하기
                                            </Button>
                                        </div>
                                    )}
                                </div>

                                {githubIntegration && githubRepos.length > 0 && (
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <Label className="font-bold text-slate-700 flex items-center gap-2">
                                                <Library className="h-4 w-4" /> 내 저장소 목록 (분석 선택)
                                            </Label>
                                            <Button variant="ghost" size="sm" onClick={loadGithubRepos} className="h-8 text-xs text-slate-400 hover:text-blue-600">
                                                <RefreshCw className={cn("h-3 w-3 mr-1", isLoadingIntegrations && "animate-spin")} /> 새로고침
                                            </Button>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-200">
                                            {githubRepos.map(repo => (
                                                <div
                                                    key={repo.url}
                                                    className="p-4 rounded-xl border border-slate-100 bg-white hover:border-blue-400 cursor-pointer transition-all group relative"
                                                    onClick={() => handleGithubAnalyze(repo.url)}
                                                >
                                                    <div className="flex items-start justify-between">
                                                        <div className="font-medium text-slate-900 group-hover:text-blue-600 truncate mr-2">{repo.name}</div>
                                                        {repo.private && <Badge variant="secondary" className="bg-slate-100 text-[10px] h-4">Private</Badge>}
                                                    </div>
                                                    <div className="text-xs text-slate-400 mt-1 truncate pr-6">{repo.description || "설명 없음"}</div>
                                                    <ExternalLink className="absolute bottom-4 right-4 h-3 w-3 text-slate-200 group-hover:text-blue-400 transition-colors" />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {githubIntegration && isLoadingIntegrations && githubRepos.length === 0 && (
                                    <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-slate-100 rounded-3xl">
                                        <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-4" />
                                        <p className="text-sm font-bold text-slate-400">레포지토리 목록을 불러오는 중...</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="blog">
                        <Card className="border-slate-200 shadow-sm border-2 overflow-hidden hover:border-blue-200 transition-colors bg-white">
                            <CardHeader className="p-8">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 bg-emerald-500 rounded-2xl">
                                        <BookOpen className="h-8 w-8 text-white" />
                                    </div>
                                    <div className="flex-1">
                                        <CardTitle className="text-xl font-bold text-slate-900">기술 블로그 분석 (Velog, Tistory)</CardTitle>
                                        <CardDescription className="text-slate-500">블로그 주소를 입력하면 포스팅별로 성과를 정리해 드립니다.</CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="px-8 pb-8 space-y-6">
                                <div className="p-6 rounded-2xl border border-slate-100 bg-slate-50/50 space-y-4">
                                    <Label className="font-bold text-slate-700">블로그 주소 또는 포스팅 URL</Label>
                                    <div className="flex gap-2">
                                        <Input
                                            placeholder="https://velog.io/@username"
                                            className="border-slate-200 bg-white focus-visible:ring-blue-500 h-11"
                                            value={blogUrl}
                                            onChange={(e) => setBlogUrl(e.target.value)}
                                        />
                                        <Button
                                            onClick={() => handleBlogAnalyze(blogUrl)}
                                            disabled={isAnalyzing}
                                            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold h-11 px-6 rounded-xl transition-all"
                                        >
                                            {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                            분석 시작
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                    {/* Placeholder for others */}
                    <TabsContent value="notion">
                        <Card className="border-slate-200 shadow-sm border-2 overflow-hidden hover:border-blue-200 transition-colors bg-white">
                            <CardHeader className="p-8">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 bg-slate-100 rounded-2xl">
                                        <Settings className="h-8 w-8 text-slate-900" />
                                    </div>
                                    <div className="flex-1">
                                        <CardTitle className="text-xl font-bold text-slate-900">Notion 데이터 연동</CardTitle>
                                        <CardDescription className="text-slate-500">Notion 페이지 또는 워크스페이스 전체를 분석합니다.</CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="px-8 pb-8 space-y-6">
                                <div className="p-6 rounded-2xl border border-slate-100 bg-slate-50/50 space-y-4">
                                    <div className="max-w-md mx-auto space-y-6 py-4">
                                        {notionIntegration ? (
                                            <div className="flex flex-col items-center gap-4">
                                                <div className="flex flex-col items-center gap-2 mb-2">
                                                    <Database className="h-10 w-10 text-slate-900" />
                                                    <h3 className="font-bold text-lg text-slate-900">워크스페이스 전체 분석</h3>
                                                    <p className="text-sm text-slate-500">연동된 모든 페이지를 재귀적으로 탐색하여 포트폴리오 데이터를 추출합니다.</p>
                                                    <div className="flex gap-2 items-center mt-1">
                                                        <Badge className="bg-emerald-50 text-emerald-600 border-emerald-100 hover:bg-emerald-50">Notion 연동됨</Badge>
                                                        <Button variant="ghost" size="sm" onClick={handleNotionConnect} className="text-xs text-slate-400 hover:text-blue-600 h-7 px-2">
                                                            워크스페이스 재선택
                                                        </Button>
                                                    </div>
                                                </div>
                                                <Button
                                                    size="lg"
                                                    onClick={() => handleNotionAnalyze("all")}
                                                    className="w-full bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold h-12 shadow-lg shadow-slate-200"
                                                    disabled={isAnalyzing}
                                                >
                                                    {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                                    워크스페이스 전체 동기화 시작
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col items-center gap-6 py-4">
                                                <div className="flex flex-col items-center gap-2 text-center">
                                                    <Settings className="h-10 w-10 text-slate-300 mb-2" />
                                                    <h3 className="font-bold text-lg text-slate-900">Notion 계정 연동 필요</h3>
                                                    <p className="text-sm text-slate-500">계정을 연동하면 워크스페이스의 페이지들을 불러오거나<br />한 번에 모든 데이터를 가져올 수 있습니다.</p>
                                                </div>
                                                <Button
                                                    size="lg"
                                                    onClick={handleNotionConnect}
                                                    className="w-full bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold h-12"
                                                >
                                                    <Settings className="h-5 w-5 mr-2" />
                                                    Notion 워크스페이스 연동하기
                                                </Button>
                                            </div>
                                        )}
                                    </div>

                                    {notionIntegration && (
                                        <>
                                            <div className="relative py-4">
                                                <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-slate-200"></span></div>
                                                <div className="relative flex justify-center text-xs uppercase"><span className="bg-slate-50 px-2 text-slate-400 font-bold">또는 특정 페이지 목록</span></div>
                                            </div>

                                            <div className="space-y-3">
                                                <div className="flex items-center justify-between">
                                                    <Label className="font-bold text-slate-700 flex items-center gap-2">
                                                        <BookOpen className="h-4 w-4" /> 연동된 페이지 목록 (추천)
                                                    </Label>
                                                    <Button variant="ghost" size="sm" onClick={loadNotionPages} className="h-8 text-xs text-slate-400 hover:text-blue-600">
                                                        <RefreshCw className={cn("h-3 w-3 mr-1", isLoadingIntegrations && "animate-spin")} /> 새로고침
                                                    </Button>
                                                </div>

                                                {isLoadingIntegrations && notionPages.length === 0 ? (
                                                    <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-slate-100 rounded-3xl">
                                                        <Loader2 className="h-8 w-8 animate-spin text-slate-300 mb-4" />
                                                        <p className="text-sm font-bold text-slate-400">Notion 페이지 목록을 불러오는 중...</p>
                                                    </div>
                                                ) : notionPages.length > 0 ? (
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-200">
                                                        {notionPages.map(page => (
                                                            <div
                                                                key={page.id}
                                                                className="p-4 rounded-xl border border-slate-100 bg-white hover:border-blue-400 cursor-pointer transition-all group relative"
                                                                onClick={() => handleNotionAnalyze(page.id)}
                                                            >
                                                                <div className="flex items-start justify-between">
                                                                    <div className="font-medium text-slate-900 group-hover:text-blue-600 truncate mr-2">{page.title}</div>
                                                                </div>
                                                                <div className="text-[10px] text-slate-400 mt-1 truncate pr-6 uppercase underline decoration-slate-200">View in Notion</div>
                                                                <ExternalLink className="absolute bottom-4 right-4 h-3 w-3 text-slate-200 group-hover:text-blue-400 transition-colors" />
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div className="p-4 bg-slate-100/50 rounded-xl text-center text-xs text-slate-400 border border-dashed">
                                                        워크스페이스에 연동된 페이지가 없거나 불러오지 못했습니다. <br />
                                                        워크스페이스 재선택을 통해 페이지 권한을 다시 설정해보세요.
                                                    </div>
                                                )}
                                            </div>

                                            <div className="relative py-4 mt-4">
                                                <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-slate-100 border-dashed"></span></div>
                                                <div className="relative flex justify-center text-xs uppercase"><span className="bg-slate-50 px-2 text-slate-300 font-bold italic">직접 URL 입력</span></div>
                                            </div>

                                            <div className="flex gap-2">
                                                <Input
                                                    placeholder="https://www.notion.so/..."
                                                    className="border-slate-200 bg-white focus-visible:ring-blue-500 h-11"
                                                    value={notionUrl}
                                                    onChange={(e) => setNotionUrl(e.target.value)}
                                                />
                                                <Button
                                                    onClick={() => handleNotionAnalyze(notionUrl)}
                                                    disabled={isAnalyzing || !notionUrl}
                                                    variant="outline"
                                                    className="border-slate-200 hover:bg-slate-100 text-slate-700 font-bold h-11 px-6 rounded-xl transition-all"
                                                >
                                                    분석
                                                </Button>
                                            </div>
                                        </>
                                    )}
                                </div>
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
