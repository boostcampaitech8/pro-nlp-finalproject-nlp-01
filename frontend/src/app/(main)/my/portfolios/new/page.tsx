"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Upload, Github, Sparkles, ExternalLink, Plus, Check, FileText } from "lucide-react";

interface AnalyzedPortfolio {
    id: number;
    title: string;
    type: string;
    description: string;
    content: string;
}

export default function NewPortfolioPage() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analyzedItems, setAnalyzedItems] = useState<AnalyzedPortfolio[]>([]);

    // [Wait, I need to keep the other states too...]
    const [step, setStep] = useState<'upload' | 'review'>('upload');
    const [isCustomAnalysisOpen, setIsCustomAnalysisOpen] = useState(false);
    const [customPrompt, setCustomPrompt] = useState("");
    const [isNotionConnectOpen, setIsNotionConnectOpen] = useState(false);
    const [notionStep, setNotionStep] = useState<'auth' | 'select'>('auth');
    const [selectedNotionPages, setSelectedNotionPages] = useState<string[]>([]);

    const mockNotionPages = [
        "2024 Project Archive",
        "Personal Resume Database",
        "Engineering Wiki",
        "Team Collaboration Space",
        "Side Projects"
    ];

    const toggleNotionPage = (page: string) => {
        setSelectedNotionPages(prev =>
            prev.includes(page) ? prev.filter(p => p !== page) : [...prev, page]
        );
    };

    const handleAnalyze = async (source: string, type: string, prompt?: string) => {
        setIsAnalyzing(true);
        setIsCustomAnalysisOpen(false);
        try {
            const res = await fetch('/api/portfolios/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source, type, customPrompt: prompt })
            });
            const data = await res.json();
            // API 응답 규격({items: []})에 맞춰 데이터 추출
            const newItems = Array.isArray(data) ? data : (data.items || []);
            setAnalyzedItems(prev => [...prev, ...newItems]);
            setStep('review');
        } catch (e) {
            console.error(e);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            handleAnalyze(`${e.target.files.length} Files`, 'file');
        }
    };

    const handleFinalConfirm = () => {
        alert(`${analyzedItems.length}개의 포트폴리오가 등록되었습니다!`);
        router.push('/my/portfolios');
    };

    if (isAnalyzing) {
        return (
            <div className="flex flex-col h-[70vh] items-center justify-center space-y-10 animate-in fade-in duration-700">
                <div className="relative">
                    <div className="h-28 w-28 rounded-full border-[6px] border-slate-100 border-t-blue-500 animate-spin" />
                    <Sparkles className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-10 w-10 text-blue-500 fill-blue-500 animate-pulse" />
                </div>
                <div className="text-center space-y-4 max-w-lg">
                    <h2 className="text-3xl font-bold text-slate-900 tracking-tight">
                        {customPrompt ? "요청하신 관점으로 재분석 중" : "AI 데이터 정밀 분석 중"}
                    </h2>
                    <p className="text-slate-500 leading-relaxed font-medium">
                        {customPrompt
                            ? `"${customPrompt}" 관점에 집중하여\n원본 데이터를 다시 해석하고 있습니다.`
                            : "README, 소스 코드, 문서 지표를 기반으로\n당신의 핵심 역량을 추출하여 포트폴리오를 구성하고 있습니다."
                        }
                    </p>
                </div>
                <div className="flex gap-3">
                    <Badge variant="outline" className="bg-blue-50 border-blue-100 text-blue-600 animate-bounce delay-75">데이터 리스캔</Badge>
                    <Badge variant="outline" className="bg-blue-50 border-blue-100 text-blue-600 animate-bounce delay-150">관점 지표 적용</Badge>
                    <Badge variant="outline" className="bg-blue-50 border-blue-100 text-blue-600 animate-bounce delay-300">새 요약 생성</Badge>
                </div>
            </div>
        );
    }

    if (step === 'review') {
        return (
            <div className="container max-w-5xl mx-auto py-12 px-4 space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-slate-100 pb-8">
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="bg-blue-50 text-blue-600 border-none px-3 font-bold">AI 분석 완료</Badge>
                            <span className="text-xs text-slate-400 font-bold uppercase tracking-widest">Step 02. Review & Confirm</span>
                        </div>
                        <h1 className="text-3xl font-bold tracking-tight text-slate-900">생성된 포트폴리오 확인</h1>
                        <p className="text-slate-500 font-medium">AI가 분석한 내용이 내 경험과 일치하는지 확인 후 최종 등록을 진행하세요.</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                        <Button
                            variant="outline"
                            onClick={() => setIsCustomAnalysisOpen(true)}
                            className="h-12 px-5 rounded-xl border-blue-100 bg-blue-50/30 text-blue-600 hover:bg-blue-50 hover:border-blue-200 font-bold gap-2 group transition-all"
                        >
                            <Sparkles className="h-4 w-4 fill-blue-500 group-hover:scale-110 transition-transform" />
                            다른 시각 분석
                        </Button>
                        <Button variant="outline" onClick={() => { setStep('upload'); setCustomPrompt(""); }} className="h-12 px-5 rounded-xl border-slate-200 font-bold text-slate-600 hover:bg-slate-50 transition-colors">소스 다시 선택</Button>
                        <Button onClick={handleFinalConfirm} className="bg-blue-600 hover:bg-blue-700 h-12 px-8 rounded-xl font-bold text-white shadow-lg shadow-blue-500/20 group">
                            최종 등록 완료 <Check className="ml-2 h-4 w-4 group-hover:scale-125 transition-transform" />
                        </Button>
                    </div>
                </div>

                <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-2 relative mb-12">
                    {analyzedItems.map((item, idx) => (
                        <Card key={`${item.id}-${idx}`} className="flex flex-col border-slate-200 hover:shadow-xl transition-all duration-500 ease-in-out hover:-translate-y-1.5 cursor-pointer bg-white group overflow-hidden ring-4 ring-transparent hover:ring-blue-500/5 shadow-sm">
                            <CardHeader className="pb-4 relative">
                                <div className="flex justify-between items-start mb-2">
                                    <Badge variant="outline" className="bg-slate-50 text-slate-400 border-slate-100 text-[10px] font-black uppercase tracking-widest px-2 py-0.5">
                                        PRO-AI READY
                                    </Badge>
                                </div>
                                <CardTitle className="flex items-center gap-3 text-xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors duration-300 mb-1">
                                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-slate-400 group-hover:bg-blue-50 group-hover:border-blue-100 group-hover:text-blue-600 transition-colors shrink-0">
                                        <FileText className="h-5 w-5" />
                                    </div>
                                    <Input
                                        className="text-xl font-bold border-none p-0 focus-visible:ring-0 bg-transparent h-auto"
                                        defaultValue={item.title}
                                    />
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="flex-1 space-y-6">
                                <div className="space-y-2">
                                    <Label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">AI 한줄 요약</Label>
                                    <Input
                                        className="text-sm border-slate-100 bg-slate-50/50 focus-visible:ring-blue-500 h-10 font-bold text-slate-600"
                                        defaultValue={item.description}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">AI 분석 상세 데이터</Label>
                                    <Textarea
                                        className="min-h-[140px] text-sm border-slate-100 bg-blue-50/10 focus-visible:ring-blue-500 leading-relaxed font-medium"
                                        defaultValue={item.content}
                                    />
                                </div>
                            </CardContent>
                            <CardFooter className="bg-slate-50/50 border-t border-slate-50 p-4 flex justify-end gap-3 rounded-b-xl group-hover:bg-blue-50/30 transition-colors duration-300">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-red-400 hover:text-red-500 hover:bg-red-50 font-bold"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        setAnalyzedItems(items => items.filter((_, i) => i !== idx));
                                    }}
                                >
                                    항목 제외
                                </Button>
                            </CardFooter>
                        </Card>
                    ))}
                </div>

                {/* 커스텀 프롬프트 입력 모달 레이어 */}
                {isCustomAnalysisOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-300 p-4">
                        <Card className="w-full max-w-md shadow-2xl border-none rounded-3xl overflow-hidden animate-in zoom-in-95 duration-300">
                            <CardHeader className="bg-white border-b border-slate-50 p-8 pt-10">
                                <div className="flex items-center gap-2 mb-2">
                                    <Sparkles className="h-4 w-4 text-blue-600 fill-blue-600" />
                                    <span className="text-[10px] font-black text-blue-600 uppercase tracking-widest">AI Custom Analysis</span>
                                </div>
                                <CardTitle className="text-2xl font-bold text-slate-900">어떤 관점을 강조할까요?</CardTitle>
                                <CardDescription className="text-slate-500 font-medium pt-1">요청하신 시각에 맞춰 포트폴리오를 새롭게 구성합니다.</CardDescription>
                            </CardHeader>
                            <CardContent className="p-8 space-y-6">
                                <div className="space-y-3">
                                    <Label className="text-xs font-black text-slate-400 uppercase tracking-wider">주요 요청 사항</Label>
                                    <Textarea
                                        placeholder="예) 협업 및 리더십 역량 위주로 요약해줘, Rust 기술 스택 전문성 강조 등"
                                        className="min-h-[120px] rounded-2xl border-slate-200 focus:ring-blue-500 bg-slate-50/50 p-4"
                                        value={customPrompt}
                                        onChange={(e) => setCustomPrompt(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-3">
                                    <Label className="text-xs font-black text-slate-400 uppercase tracking-wider">추천 태그</Label>
                                    <div className="flex flex-wrap gap-2">
                                        {["기술 스택 전문성", "문제 해결 능력", "협업 및 커뮤니케이션", "데이터 분석 역량", "리더십 및 기획"].map(tag => (
                                            <Badge
                                                key={tag}
                                                variant="outline"
                                                className="cursor-pointer hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600 transition-colors font-bold px-3 py-1 bg-white border-slate-100 text-slate-500"
                                                onClick={() => setCustomPrompt(tag)}
                                            >
                                                {tag}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            </CardContent>
                            <CardFooter className="p-8 bg-slate-50/50 flex gap-3">
                                <Button variant="ghost" onClick={() => setIsCustomAnalysisOpen(false)} className="flex-1 h-12 rounded-xl font-bold text-slate-500">취소</Button>
                                <Button
                                    onClick={() => handleAnalyze('Previous Source', 'custom', customPrompt)}
                                    disabled={!customPrompt.trim()}
                                    className="flex-1 bg-blue-600 hover:bg-blue-700 h-12 rounded-xl font-bold shadow-lg shadow-blue-500/20"
                                >
                                    분석 시작
                                </Button>
                            </CardFooter>
                        </Card>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="container max-w-4xl mx-auto py-12 px-4 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* [Existing Header Code...] */}
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
                    <TabsTrigger value="notion" className="rounded-xl data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all font-bold">Notion</TabsTrigger>
                    <TabsTrigger value="file" className="rounded-xl data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all font-bold">Files / PDF</TabsTrigger>
                    <TabsTrigger value="link" className="rounded-xl data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all font-bold">Etc.</TabsTrigger>
                </TabsList>

                <div className="grid gap-6">
                    {/* [GitHub Content - skipped for brevity but preserved in real file] */}
                    <TabsContent value="github" className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        {/* ... GitHub content items ... */}
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
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="flex-1 p-6 rounded-2xl border border-slate-100 bg-slate-50/50 space-y-4">
                                        <div className="flex items-center justify-between">
                                            <Label className="font-bold text-slate-700">프로필 전체 동기화</Label>
                                            <Badge className="bg-blue-600 text-white font-bold px-2 py-0">PRO</Badge>
                                        </div>
                                        <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                            GitHub ID만 입력하면 공개된 모든 레포지토리를 분석하여 경력 기간별로 포트폴리오를 자동 그룹화합니다.
                                        </p>
                                        <div className="flex gap-2">
                                            <Input placeholder="GitHub ID" className="border-slate-200 bg-white focus-visible:ring-blue-500 h-11" />
                                            <Button onClick={() => handleAnalyze('GitHub Profile', 'github')} className="bg-blue-600 hover:bg-blue-700 text-white font-bold h-11 px-4 rounded-xl transition-all">스캔</Button>
                                        </div>
                                    </div>
                                    <div className="flex-1 p-6 rounded-2xl border border-slate-100 bg-slate-50/50 space-y-4">
                                        <Label className="font-bold text-slate-700">개별 레포지토리 연동</Label>
                                        <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                            특정 프로젝트의 README, 전체 소스 코드를 정밀 분석하여 기술 스택 중심의 상세 데이터를 구성합니다.
                                        </p>
                                        <div className="flex gap-2">
                                            <Input placeholder="Repository URL" className="border-slate-200 bg-white focus-visible:ring-blue-500 h-11" />
                                            <Button onClick={() => handleAnalyze('GitHub Repo', 'github')} variant="outline" className="border-slate-200 font-bold h-11 px-4 rounded-xl transition-all hover:bg-white">연동</Button>
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                            <CardFooter className="bg-slate-50/50 border-t border-slate-100 p-6 flex justify-end">
                                <Button onClick={() => handleAnalyze('GitHub Profile', 'github')} className="bg-slate-900 hover:bg-slate-800 text-white h-12 px-8 rounded-xl font-bold shadow-lg shadow-slate-200 animate-in fade-in slide-in-from-right-2 duration-500">
                                    AI 프로필 동기화 시작
                                </Button>
                            </CardFooter>
                        </Card>
                    </TabsContent>

                    {/* [Notion] */}
                    <TabsContent value="notion" className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <Card className="border-slate-200 shadow-sm border-2 overflow-hidden bg-white">
                            <CardContent className="p-16 text-center space-y-8">
                                <div className="mx-auto w-24 h-24 bg-slate-50 rounded-3xl flex items-center justify-center border border-slate-100 shadow-inner group">
                                    <div className="text-4xl font-black text-slate-800 group-hover:scale-110 transition-transform">N</div>
                                </div>
                                <div className="space-y-3">
                                    <h3 className="text-2xl font-bold text-slate-900 tracking-tight">Notion Workspace 연결</h3>
                                    <p className="text-slate-500 max-w-sm mx-auto leading-relaxed font-medium">
                                        워크스페이스의 페이지를 분석하여 경력 경험과<br />성과 지표를 AI가 자동으로 추출해 드립니다.
                                    </p>
                                </div>
                                <Button
                                    onClick={() => setIsNotionConnectOpen(true)}
                                    className="bg-blue-600 hover:bg-blue-700 text-white h-14 px-10 rounded-2xl font-bold inline-flex items-center gap-3 shadow-xl shadow-blue-500/10 transition-all hover:-translate-y-1"
                                >
                                    노션 계정 연결 및 데이터 스캔 <ExternalLink className="h-5 w-5" />
                                </Button>
                            </CardContent>
                        </Card>

                        {/* Notion 연결 모달 */}
                        {isNotionConnectOpen && (
                            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-300 p-4">
                                <Card className="w-full max-w-lg shadow-2xl border-none rounded-3xl overflow-hidden animate-in zoom-in-95 duration-300">
                                    {notionStep === 'auth' ? (
                                        <div className="p-10 space-y-8 text-center bg-white">
                                            <div className="flex justify-center items-center gap-4 mb-2">
                                                <div className="w-12 h-12 rounded-xl bg-slate-900 text-white flex items-center justify-center font-black text-xl">N</div>
                                                <div className="h-px w-8 bg-slate-200" />
                                                <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center">
                                                    <Sparkles className="h-6 w-6 fill-white" />
                                                </div>
                                            </div>
                                            <div className="space-y-2">
                                                <h2 className="text-2xl font-bold text-slate-900">Notion 권한 요청</h2>
                                                <p className="text-slate-500 font-medium leading-relaxed">
                                                    Pro-NLP가 회원의 노션 워크스페이스에<br />접근하여 페이지 내용을 읽을 수 있도록 허용하시겠습니까?
                                                </p>
                                            </div>
                                            <div className="bg-slate-50 rounded-2xl p-6 text-left space-y-4">
                                                <div className="flex items-start gap-3">
                                                    <div className="p-1 mt-0.5 bg-green-100 rounded-full"><Check className="h-3 w-3 text-green-600" /></div>
                                                    <p className="text-sm font-bold text-slate-700">페이지 콘텐츠 및 메타데이터 읽기</p>
                                                </div>
                                                <div className="flex items-start gap-3">
                                                    <div className="p-1 mt-0.5 bg-green-100 rounded-full"><Check className="h-3 w-3 text-green-600" /></div>
                                                    <p className="text-sm font-bold text-slate-700">워크스페이스 내 정보 스캔</p>
                                                </div>
                                            </div>
                                            <div className="flex gap-3 pt-4">
                                                <Button variant="ghost" onClick={() => setIsNotionConnectOpen(false)} className="flex-1 h-12 rounded-xl font-bold text-slate-500">취소</Button>
                                                <Button onClick={() => setNotionStep('select')} className="flex-1 bg-slate-900 hover:bg-slate-800 h-12 rounded-xl font-bold text-white shadow-lg">허용 및 계속</Button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="bg-white">
                                            <CardHeader className="p-8 pb-4">
                                                <CardTitle className="text-xl font-bold">분석할 페이지 선택</CardTitle>
                                                <CardDescription className="font-medium">포트폴리오로 생성할 데이터가 포함된 페이지를 모두 선택하세요.</CardDescription>
                                            </CardHeader>
                                            <CardContent className="p-8 pt-0 space-y-3">
                                                {mockNotionPages.map(page => (
                                                    <div
                                                        key={page}
                                                        onClick={() => toggleNotionPage(page)}
                                                        className={`flex items-center justify-between p-4 rounded-2xl border-2 transition-all cursor-pointer ${selectedNotionPages.includes(page)
                                                            ? "border-blue-500 bg-blue-50 text-blue-700"
                                                            : "border-slate-100 hover:border-slate-200 bg-slate-50/50 text-slate-600"
                                                            }`}
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-8 h-8 rounded-lg bg-white border border-slate-100 flex items-center justify-center font-bold text-slate-400">
                                                                <FileText className="h-4 w-4" />
                                                            </div>
                                                            <span className="font-bold">{page}</span>
                                                        </div>
                                                        {selectedNotionPages.includes(page) && <Check className="h-5 w-5 text-blue-500" />}
                                                    </div>
                                                ))}
                                            </CardContent>
                                            <CardFooter className="p-8 pt-4 bg-slate-50/50 flex gap-3">
                                                <Button variant="ghost" onClick={() => setNotionStep('auth')} className="h-12 rounded-xl font-bold text-slate-500">뒤로</Button>
                                                <Button
                                                    disabled={selectedNotionPages.length === 0}
                                                    onClick={() => handleAnalyze(selectedNotionPages.join(', '), 'notion')}
                                                    className="flex-1 bg-blue-600 hover:bg-blue-700 h-12 rounded-xl font-bold text-white shadow-lg shadow-blue-500/20"
                                                >
                                                    {selectedNotionPages.length}개 페이지 분석 시작
                                                </Button>
                                            </CardFooter>
                                        </div>
                                    )}
                                </Card>
                            </div>
                        )}
                    </TabsContent>

                    {/* [File] */}
                    <TabsContent value="file" className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <Card className="border-slate-200 shadow-sm border-2 overflow-hidden bg-white">
                            <CardContent className="p-8">
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    onChange={handleFileChange}
                                    multiple
                                    accept=".pdf,.doc,.docx,.hwp"
                                    className="hidden"
                                />
                                <div
                                    onClick={() => fileInputRef.current?.click()}
                                    className="border-2 border-dashed border-slate-100 rounded-[2rem] p-20 flex flex-col items-center justify-center text-slate-400 hover:bg-blue-50/30 hover:border-blue-200 transition-all cursor-pointer group"
                                >
                                    <div className="relative mb-6">
                                        <div className="p-6 rounded-3xl bg-slate-50 group-hover:bg-white group-hover:shadow-lg transition-all duration-500">
                                            <Upload className="h-16 w-16 text-slate-300 group-hover:text-blue-500 group-hover:scale-110 transition-all duration-500" />
                                        </div>
                                        <div className="absolute -bottom-2 -right-2 bg-blue-600 h-8 w-8 rounded-full flex items-center justify-center text-white shadow-lg animate-bounce">
                                            <Plus className="h-5 w-5" />
                                        </div>
                                    </div>
                                    <p className="font-bold text-slate-800 text-2xl tracking-tight">파일 뭉치를 드래그하여 업로드</p>
                                    <p className="text-slate-500 mt-3 font-medium text-center">
                                        AI가 여러 파일을 한꺼번에 분석하여<br />
                                        개별 프로젝트 항목으로 자동 분리해 드립니다.
                                    </p>
                                    <div className="flex gap-2 mt-8">
                                        {["PDF", "DOCX", "HWP", "TXT"].map(ext => (
                                            <Badge key={ext} variant="outline" className="border-slate-200 text-slate-400 font-bold bg-white px-3 py-1">
                                                {ext}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* [Etc Link] */}
                    <TabsContent value="link" className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <Card className="border-slate-200 shadow-sm border-2 bg-white">
                            <CardContent className="p-10 space-y-8">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div className="space-y-3">
                                        <Label htmlFor="url" className="text-slate-700 font-bold block">사이트 / 블로그 URL</Label>
                                        <Input id="url" placeholder="https://example.com" className="border-slate-200 focus-visible:ring-blue-500 h-12 bg-slate-50/50 rounded-xl" />
                                    </div>
                                    <div className="space-y-3">
                                        <Label htmlFor="desc" className="text-slate-700 font-bold block">설명 (선택)</Label>
                                        <Input id="desc" placeholder="이 포트폴리오에 대한 요약을 적어주세요." className="border-slate-200 focus-visible:ring-blue-500 h-12 bg-slate-50/50 rounded-xl" />
                                    </div>
                                </div>
                                <div className="space-y-3">
                                    <Label htmlFor="content" className="flex items-center gap-2 text-blue-600 font-bold">
                                        상세 데이터 (AI 분석용)
                                        <Badge variant="outline" className="text-[10px] bg-blue-50 border-blue-100 uppercase font-black">Recommended</Badge>
                                    </Label>
                                    <Textarea id="content" placeholder="AI가 참고할 상세 리드미, 프로젝트 성과 등을 입력하세요." className="min-h-[200px] border-slate-200 focus-visible:ring-blue-500 bg-slate-50/30 rounded-2xl p-6 leading-relaxed" />
                                </div>
                                <Button className="w-full h-14 rounded-2xl font-bold bg-slate-900 text-white hover:bg-slate-800 shadow-xl shadow-slate-200 transition-all hover:-translate-y-1">
                                    단일 포트폴리오 즉시 등록
                                </Button>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
}
