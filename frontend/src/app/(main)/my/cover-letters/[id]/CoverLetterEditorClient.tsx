"use client";

import { useEffect, useState, use } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, Save, Sparkles, Loader2, Briefcase, BookOpen, X, Building, Plus, Trash2, FileText, Github, Brain, CheckCircle, Target, MessageSquare, Wand2, Zap, LayoutList, Calendar } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { motion, AnimatePresence } from "framer-motion";

// --- Types ---
interface QuestionItem {
    id: number;
    question: string;
    answer: string;
}

interface Portfolio {
    id: number;
    title: string;
    type: 'link' | 'file' | 'github';
    description: string;
}

type AiMode = 'draft' | 'strategy' | 'refine';
type ToneType = 'professional' | 'passionate' | 'humble' | 'confident';

export default function CoverLetterEditorPage({ params }: { params: Promise<{ id: string }> }) {
    const router = useRouter();
    const { id } = use(params);
    const searchParams = useSearchParams();
    const jobId = searchParams.get('jobId');

    const isNew = id === 'new';
    const [title, setTitle] = useState("");
    const [questions, setQuestions] = useState<QuestionItem[]>([
        { id: 1, question: "지원동기 및 포부", answer: "" }
    ]);

    const [linkedRecruit, setLinkedRecruit] = useState<{ id: number; company: string; title: string; startDate: string; deadline: string; content?: string; tags?: string[] } | null>(null);
    const [loading, setLoading] = useState(!isNew);
    const [showRecruitPanel, setShowRecruitPanel] = useState(false);
    const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
    const [selectedPortfolioIds, setSelectedPortfolioIds] = useState<number[]>([]);
    const [panelTab, setPanelTab] = useState("recruit");

    // --- AI Studio State ---
    const [activeAiQuestionId, setActiveAiQuestionId] = useState<number | null>(null);
    const [aiMode, setAiMode] = useState<AiMode>('draft');
    const [aiTone, setAiTone] = useState<ToneType>('professional');
    const [aiFocus, setAiFocus] = useState("");
    const [isGenerating, setIsGenerating] = useState(false);

    useEffect(() => {
        const loadData = async () => {
            try {
                const pfRes = await fetch('/api/portfolios');
                if (pfRes.ok) {
                    const data = await pfRes.json();
                    setPortfolios(data.items || data || []);
                }
            } catch (e) { console.error(e); }

            if (!isNew) {
                try {
                    const res = await fetch(`/api/cover-letters/${id}`);
                    const data = await res.json();
                    setTitle(data.title);
                    if (data.questions?.length > 0) setQuestions(data.questions);
                    if (data.recruitId) {
                        const rRes = await fetch(`/api/recruits/${data.recruitId}`);
                        if (rRes.ok) { setLinkedRecruit(await rRes.json()); setShowRecruitPanel(true); }
                    }
                } catch (e) { console.error(e); }
            } else if (jobId) {
                try {
                    const rRes = await fetch(`/api/recruits/${jobId}`);
                    if (rRes.ok) {
                        const data = await rRes.json();
                        setLinkedRecruit(data);
                        setTitle(`[지원] ${data.company} - ${data.title}`);
                        setShowRecruitPanel(true);
                    }
                } catch (e) { console.error(e); }
            }
            setLoading(false);
        };
        loadData();
    }, [id, isNew, jobId]);

    const handleSave = async () => {
        try {
            const body = { title, questions, recruitId: linkedRecruit?.id };
            const res = await fetch(isNew ? '/api/cover-letters' : `/api/cover-letters/${id}`, {
                method: isNew ? 'POST' : 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (res.ok) {
                alert("성공적으로 저장되었습니다!");
                router.push('/my/cover-letters');
            }
        } catch (e) { console.error(e); }
    };

    const addQuestion = () => setQuestions([...questions, { id: Date.now(), question: "", answer: "" }]);
    const removeQuestion = (qId: number) => setQuestions(questions.filter(q => q.id !== qId));
    const updateQuestion = (qId: number, field: 'question' | 'answer', value: string) =>
        setQuestions(questions.map(q => q.id === qId ? { ...q, [field]: value } : q));

    const togglePortfolio = (pfId: number) =>
        setSelectedPortfolioIds(prev => prev.includes(pfId) ? prev.filter(id => id !== pfId) : [...prev, pfId]);

    // --- AI Studio Logic ---
    const openAiStudio = (qId: number) => {
        if (selectedPortfolioIds.length === 0) {
            alert("참고할 포트폴리오를 우측 패널에서 먼저 선택하세요!");
            setShowRecruitPanel(true);
            setPanelTab("reference");
            return;
        }
        setActiveAiQuestionId(qId);
    };

    const runAiGeneration = async () => {
        setIsGenerating(true);
        try {
            const activeQuestionContent = questions.find(q => q.id === activeAiQuestionId)?.question || "";
            const res = await fetch('/api/cover-letters/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mode: aiMode,
                    tone: aiTone,
                    focus: aiFocus,
                    portfolioIds: selectedPortfolioIds,
                    question: activeQuestionContent
                })
            });

            if (!res.ok) throw new Error("AI 생성에 실패했습니다.");

            const data = await res.json();
            setQuestions(questions.map(q => q.id === activeAiQuestionId ? { ...q, answer: data.result } : q));
            setActiveAiQuestionId(null);
        } catch (e) {
            console.error(e);
            alert("AI 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
        }
        setIsGenerating(false);
    };

    if (loading) return <div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

    return (
        <div className="flex justify-center min-h-[calc(100vh-64px)] bg-slate-50/10 overflow-x-hidden relative">
            <div className={cn("flex relative transition-all duration-500", showRecruitPanel ? "w-full max-w-[1700px]" : "w-full max-w-5xl")}>
                {/* Editor Content */}
                <div className="flex-1 p-4 md:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-6">
                        <div className="space-y-3">
                            <div className="flex items-center gap-3">
                                <Button variant="ghost" size="icon" onClick={() => router.back()} className="rounded-full hover:bg-slate-100"><ArrowLeft className="h-5 w-5" /></Button>
                                <h1 className="text-2xl font-bold tracking-tight text-slate-900">{isNew ? "새 자기소개서 작성" : "자기소개서 수정"}</h1>
                            </div>
                            <div className="flex items-center gap-2">
                                {linkedRecruit && (
                                    <Badge variant="outline" className="bg-slate-50 border-slate-200 px-2 py-1 gap-1.5 font-semibold text-slate-600">
                                        <Building className="h-3 w-3" /> {linkedRecruit.company}
                                    </Badge>
                                )}
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setShowRecruitPanel(!showRecruitPanel)}
                                    className={cn("h-8 gap-1.5 text-xs border-slate-200", showRecruitPanel && "bg-blue-50 text-blue-600 border-blue-200")}
                                >
                                    <BookOpen className="h-3.5 w-3.5" /> 패널 {showRecruitPanel ? "닫기" : "열기"}
                                </Button>
                            </div>
                        </div>
                        <div className="flex gap-2 items-center">
                            {!isNew && (
                                <Button
                                    variant="ghost"
                                    onClick={async () => {
                                        if (confirm("정말 이 자기소개서를 삭제하시겠습니까?")) {
                                            try {
                                                const res = await fetch(`/api/cover-letters/${id}`, { method: 'DELETE' });
                                                if (res.ok) {
                                                    alert("삭제되었습니다.");
                                                    router.push('/my/cover-letters');
                                                }
                                            } catch (e) { console.error(e); }
                                        }
                                    }}
                                    className="text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors h-10 px-4"
                                >
                                    <Trash2 className="h-4 w-4 mr-2" /> 삭제
                                </Button>
                            )}
                            <Button variant="outline" onClick={() => router.back()} className="border-slate-200 h-10 px-6">취소</Button>
                            <Button variant="brand" onClick={handleSave} className="rounded-md h-10 px-6">
                                <Save className="mr-2 h-4 w-4" /> 저장하기
                            </Button>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <Label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">문서 제목</Label>
                        <Input value={title} onChange={(e) => setTitle(e.target.value)} className="h-12 text-lg font-bold border-slate-200 bg-white shadow-sm focus-visible:ring-blue-500" placeholder="자소서 제목을 입력하세요" />
                    </div>

                    <div className="space-y-12 pb-40">
                        <AnimatePresence mode="popLayout">
                            {questions.map((q, idx) => (
                                <motion.div key={q.id} layout initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
                                    className="bg-white border border-slate-200 rounded-xl p-8 shadow-sm relative group hover:shadow-md transition-shadow"
                                >
                                    <div className="flex justify-between items-center mb-6">
                                        <div className="flex items-center gap-4 flex-1">
                                            <div className="flex items-center bg-slate-900 text-white rounded-md px-3 py-1.5 gap-2 shrink-0 h-9">
                                                <span className="text-xs font-bold uppercase tracking-tighter opacity-70">문항</span>
                                                <span className="text-sm font-black">{idx + 1}</span>
                                            </div>
                                            <Input
                                                value={q.question}
                                                onChange={e => updateQuestion(q.id, 'question', e.target.value)}
                                                className="border-none text-xl font-bold p-0 focus-visible:ring-0 w-full placeholder:text-slate-300"
                                                placeholder="어떤 문항인가요? (예: 지원동기)"
                                            />
                                        </div>
                                        <Button variant="ghost" size="icon" onClick={() => removeQuestion(q.id)} className="text-slate-200 hover:text-red-500 hover:bg-red-50 transition-colors"><Trash2 className="h-4 w-4" /></Button>
                                    </div>
                                    <div className="relative">
                                        <Textarea
                                            value={q.answer}
                                            onChange={e => updateQuestion(q.id, 'answer', e.target.value)}
                                            className="min-h-[400px] resize-y border-slate-100 bg-slate-50/50 p-6 text-base leading-relaxed focus:bg-white focus:border-blue-200 transition-all rounded-xl scrollbar-hide"
                                            placeholder="답변을 입력하거나 AI 라이팅 스튜디오를 실행하세요."
                                        />
                                        <div className="absolute bottom-6 right-6">
                                            <Button variant="brand" onClick={() => openAiStudio(q.id)} className="gap-2 shadow-xl shadow-blue-500/10 px-6 h-12 transition-all hover:scale-105 active:scale-95 group">
                                                <Sparkles className="h-4 w-4 group-hover:animate-pulse" /> AI 라이팅 스튜디오
                                            </Button>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        <motion.div layout>
                            <Button variant="outline" onClick={addQuestion} className="w-full h-14 border-dashed border-2 border-slate-200 bg-white/50 hover:bg-white hover:border-blue-200 hover:text-blue-600 transition-all rounded-xl">
                                <Plus className="mr-2 h-5 w-5" /> 문항 추가
                            </Button>
                        </motion.div>
                    </div>
                </div>

                {/* Info Panel */}
                <div className={cn("sticky top-0 h-screen transition-all duration-500 overflow-hidden shrink-0 hidden lg:block", showRecruitPanel ? "w-[480px] opacity-100" : "w-0 opacity-0 pointer-events-none")}>
                    <div className="w-[480px] h-full px-8 pt-20 pb-24 flex flex-col overflow-visible">
                        <div className="bg-white border border-slate-200 rounded-3xl shadow-2xl flex-1 flex flex-col overflow-hidden">
                            <Tabs value={panelTab} onValueChange={setPanelTab} className="h-full flex flex-col">
                                <div className="p-6 border-b border-slate-100 bg-slate-50/50">
                                    <div className="flex justify-between items-center mb-4">
                                        <h2 className="font-bold text-lg flex items-center gap-2 tracking-tight text-slate-800">
                                            <div className="p-2 bg-white rounded-xl border border-slate-200 shadow-sm"><Briefcase className="h-4 w-4 text-slate-400" /></div>
                                            데이터 참고소
                                        </h2>
                                        <Button variant="ghost" size="icon" onClick={() => setShowRecruitPanel(false)} className="rounded-full hover:bg-slate-200 transition-colors"><X className="h-4 w-4" /></Button>
                                    </div>
                                    <TabsList className="grid grid-cols-2 w-full h-11 bg-slate-200/50 p-1 rounded-xl">
                                        <TabsTrigger value="recruit" className="rounded-lg">공고 상세</TabsTrigger>
                                        <TabsTrigger value="reference" className="rounded-lg">내 포트폴리오</TabsTrigger>
                                    </TabsList>
                                </div>
                                <div className="flex-1 overflow-y-auto overflow-x-hidden p-6 scrollbar-hide">
                                    <TabsContent value="recruit" className="m-0 space-y-6 animate-in fade-in slide-in-from-right-4 duration-500 mt-2">
                                        {linkedRecruit ? (
                                            <div className="space-y-6">
                                                <div className="space-y-2">
                                                    <h3 className="text-2xl font-black tracking-tight text-slate-900 leading-tight">{linkedRecruit.title}</h3>
                                                    <div className="flex items-center justify-between">
                                                        <p className="text-blue-600 font-bold text-sm tracking-wide">{linkedRecruit.company}</p>
                                                        <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-100">
                                                            <Calendar className="h-3 w-3" />
                                                            {linkedRecruit.startDate} ~ {linkedRecruit.deadline}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="h-px bg-slate-100" />
                                                <p className="text-[15px] text-slate-600 leading-relaxed whitespace-pre-line">{linkedRecruit.content}</p>
                                            </div>
                                        ) : <div className="text-center py-24 text-slate-400 font-medium">연결된 공고가 없습니다.</div>}
                                    </TabsContent>
                                    <TabsContent value="reference" className="m-0 space-y-4 animate-in fade-in slide-in-from-right-4 duration-500 mt-2">
                                        <div className="bg-white border border-blue-100 p-5 rounded-2xl shadow-sm mb-2 group">
                                            <p className="text-sm font-black text-blue-600 mb-1 flex items-center gap-2">
                                                <Sparkles className="h-4 w-4 fill-blue-500 text-blue-500" /> AI 가이드
                                            </p>
                                            <p className="text-[13px] text-slate-500 leading-relaxed font-medium">선택한 데이터가 AI 초안 작성의 핵심 재료로 사용됩니다. 관련된 경험을 모두 불러오세요.</p>
                                        </div>
                                        {portfolios.map(pf => (
                                            <div
                                                key={pf.id}
                                                onClick={() => togglePortfolio(pf.id)}
                                                className={cn(
                                                    "p-5 rounded-2xl border transition-all cursor-pointer group relative overflow-hidden",
                                                    selectedPortfolioIds.includes(pf.id)
                                                        ? "bg-blue-50/40 border-slate-200 shadow-sm"
                                                        : "bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50"
                                                )}
                                            >
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-3">
                                                        <div className={cn("p-2 rounded-lg transition-colors", selectedPortfolioIds.includes(pf.id) ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-400 group-hover:bg-blue-100 group-hover:text-blue-600")}>
                                                            {pf.type === 'github' ? <Github className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                                                        </div>
                                                        <span className={cn("font-bold text-sm tracking-tight", selectedPortfolioIds.includes(pf.id) ? "text-blue-700" : "text-slate-800")}>{pf.title}</span>
                                                    </div>
                                                    <div className={cn("h-5 w-5 rounded-full border flex items-center justify-center transition-all", selectedPortfolioIds.includes(pf.id) ? "bg-blue-600 border-blue-600 shadow-sm" : "bg-white border-slate-200")}>
                                                        {selectedPortfolioIds.includes(pf.id) && <CheckCircle className="h-3 w-3 text-white" />}
                                                    </div>
                                                </div>
                                                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed pl-11">{pf.description}</p>
                                            </div>
                                        ))}
                                    </TabsContent>
                                </div>
                            </Tabs>
                        </div>
                    </div>
                </div>
            </div>

            {/* --- AI Studio OverLay Modal --- */}
            <AnimatePresence>
                {activeAiQuestionId && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => !isGenerating && setActiveAiQuestionId(null)} className="absolute inset-0 bg-slate-900/60 backdrop-blur-xl" />
                        <motion.div initial={{ opacity: 0, scale: 0.95, y: 30 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 30 }}
                            className="bg-white rounded-[1.5rem] shadow-[0_32px_64px_-12px_rgba(0,0,0,0.3)] w-full max-w-[650px] overflow-hidden relative border-none"
                        >
                            <div className="flex bg-slate-900 text-white p-7 items-center justify-between border-b border-white/5 relative z-10">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2.5">
                                        <div className="h-8 w-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20"><Sparkles className="h-5 w-5 text-white" /></div>
                                        <h2 className="text-xl font-black tracking-tight text-white">AI 라이팅 스튜디오</h2>
                                    </div>
                                    <p className="text-slate-400 text-[13px] font-medium opacity-70">전략을 설정하고 합격하는 자소서를 만드세요.</p>
                                </div>
                                {!isGenerating && (
                                    <Button
                                        variant="ghost"
                                        onClick={() => setActiveAiQuestionId(null)}
                                        className="text-slate-500 hover:text-white hover:bg-transparent transition-all group p-0 h-auto"
                                    >
                                        <X className="h-8 w-8 transition-all group-hover:scale-110 active:scale-95" />
                                    </Button>
                                )}
                            </div>

                            <div className="p-8 space-y-8">
                                {/* [Mode Selection] */}
                                <div className="space-y-4">
                                    <Label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2 ml-1">
                                        <Zap className="h-3.5 w-3.5 text-blue-500 fill-blue-500" /> 작성 모드 선택
                                    </Label>
                                    <div className="grid grid-cols-3 gap-3">
                                        {[
                                            { id: 'draft', label: '완성형 초안', icon: <Wand2 className="h-5 w-5" />, desc: '풀 스토리' },
                                            { id: 'strategy', label: '작성 전략', icon: <LayoutList className="h-5 w-5" />, desc: '개요 추출' },
                                            { id: 'refine', label: '메모 정교화', icon: <MessageSquare className="h-5 w-5" />, desc: '문장화' }
                                        ].map(mode => (
                                            <div key={mode.id} onClick={() => setAiMode(mode.id as AiMode)} className={cn("p-4 rounded-2xl border-2 transition-all cursor-pointer text-center space-y-2 group relative overflow-hidden", aiMode === mode.id ? "border-blue-600 bg-blue-50/30" : "border-slate-50 bg-slate-50/50 hover:border-slate-200 hover:bg-white")}>
                                                <div className={cn("mx-auto h-10 w-10 rounded-xl flex items-center justify-center transition-all duration-300", aiMode === mode.id ? "bg-blue-600 text-white shadow-md shadow-blue-500/20 scale-105" : "bg-white text-slate-400 group-hover:bg-slate-100")}>{mode.icon}</div>
                                                <div className="space-y-0.5">
                                                    <div className={cn("font-black text-sm tracking-tight transition-colors", aiMode === mode.id ? "text-blue-700" : "text-slate-700")}>{mode.label}</div>
                                                    <div className="text-[10px] text-slate-400 font-bold opacity-60 tracking-tighter">{mode.desc}</div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* [Detail Options] */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div className="space-y-4">
                                        <Label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2 ml-1">
                                            <Target className="h-3.5 w-3.5 text-blue-500" /> 집중 요청 사항
                                        </Label>
                                        <Textarea placeholder="예: 구체적인 수치를 넣어줘..." value={aiFocus} onChange={e => setAiFocus(e.target.value)} className="min-h-[120px] resize-none border-slate-100 bg-slate-50/50 focus:bg-white rounded-2xl px-4 py-3 text-sm leading-relaxed transition-all focus:border-blue-200 shadow-inner" />
                                    </div>
                                    <div className="space-y-4">
                                        <Label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2 ml-1">
                                            <Brain className="h-3.5 w-3.5 text-blue-500" /> 분위기 (Tone)
                                        </Label>
                                        <div className="grid grid-cols-2 gap-2">
                                            {[
                                                { id: 'professional', label: '전문적인' },
                                                { id: 'passionate', label: '열정적인' },
                                                { id: 'humble', label: '성실한' },
                                                { id: 'confident', label: '자신감' }
                                            ].map(tone => (
                                                <Button key={tone.id} variant="outline" onClick={() => setAiTone(tone.id as ToneType)} className={cn("justify-start h-11 rounded-xl border-slate-100 px-4 text-xs font-bold transition-all", aiTone === tone.id ? "border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600 shadow-sm" : "bg-slate-50/50 hover:bg-white")}>
                                                    <div className={cn("h-2 w-2 rounded-full mr-2", aiTone === tone.id ? "bg-blue-600" : "bg-slate-300")} />
                                                    {tone.label}
                                                </Button>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                <div className="pt-2">
                                    <Button variant="brand" size="lg" onClick={runAiGeneration} disabled={isGenerating} className="w-full h-16 rounded-2xl text-lg font-black shadow-lg shadow-blue-500/10 transition-all hover:-translate-y-1 active:scale-[0.98]">
                                        {isGenerating ? (
                                            <span className="flex items-center gap-3"><Loader2 className="h-5 w-5 animate-spin" /> 분석 중...</span>
                                        ) : (
                                            <span className="flex items-center gap-2"><Sparkles className="h-6 w-6" /> AI 작성 시작하기</span>
                                        )}
                                    </Button>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}
