"use client";

import { useEffect, useState, use } from "react";
import { Button } from "@/components/ui/button";
import { usePolling } from "@/hooks/usePolling";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useSearchParams, useRouter } from "next/navigation";
import {
    ArrowLeft, Save, Sparkles, Loader2, X, Building,
    Plus, Trash2, FileText, Github, Brain, CheckCircle, Target,
    MessageSquare, Wand2, Zap, LayoutList, MapPin,
    GraduationCap, Coins, AlertCircle, Search
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { motion, AnimatePresence } from "framer-motion";
import { getApiUrl, fetchWithAuth } from "@/lib/apiUtils";
import { CoverLetterItem, GapAnalysisResult } from "@/types";

// --- Types ---
interface QuestionItem {
    id: number;
    question: string;
    answer: string;
    key_points?: string[];
    suggested_improvements?: string[];
}

interface Portfolio {
    id: number;
    title: string;
    type: 'link' | 'file' | 'github';
    description: string;
    project_name?: string;
    role?: string;
}

interface RecruitDetail {
    id: number;
    company: string;
    title: string;
    startDate: string;
    deadline: string;
    content?: string;
    location?: string;
    experience?: string;
    education?: string;
    salary?: string;
    job_sector?: string;
    category?: string;
    key_responsibilities?: string;
    required_qualifications?: string;
    preferred_qualifications?: string;
    tags?: string[];
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

    const [linkedRecruit, setLinkedRecruit] = useState<RecruitDetail | null>(null);
    const [gapAnalysis, setGapAnalysis] = useState<GapAnalysisResult | null>(null);
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

    // Polling logic for AI generation result
    const [pollingTarget, setPollingTarget] = useState<string>("");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: polledResult } = usePolling<any>(
        pollingTarget,
        3000,
        (data) => data.processingStatus === 'COMPLETED' || data.processingStatus === 'FAILED'
    );

    // Effect to handle polled data updates
    useEffect(() => {
        if (!polledResult || !activeAiQuestionId) return;

        if (polledResult.processingStatus === 'COMPLETED') {
            // Backend returns full CoverLetter object
            if (polledResult.gap_analysis) {
                setGapAnalysis(prev => ({ ...prev, ...polledResult.gap_analysis }));
            }

            // Find the updated question text to match
            const targetQuestion = questions.find(q => q.id === activeAiQuestionId);
            const activeQuestionContent = targetQuestion?.question || "";
            const generatedItem = polledResult.items?.find((i: CoverLetterItem) => i.question === activeQuestionContent);

            if (generatedItem) {
                setQuestions(prev => prev.map(q => q.id === activeAiQuestionId ? {
                    ...q,
                    answer: generatedItem.content || "",
                    key_points: generatedItem.key_points,
                    suggested_improvements: generatedItem.suggested_improvements
                } : q));

                // Clear polling and loading state
                setPollingTarget("");
                setIsGenerating(false);
                setActiveAiQuestionId(null);

            } else if (polledResult.content && polledResult.items?.length === 0) {
                // Fallback if no items (legacy or simple update)
                setQuestions(prev => prev.map(q => q.id === activeAiQuestionId ? { ...q, answer: polledResult.content } : q));
                setPollingTarget("");
                setIsGenerating(false);
                setActiveAiQuestionId(null);
            }
        } else if (polledResult.processingStatus === 'FAILED') {
            alert("AI 생성에 실패했습니다.");
            setPollingTarget("");
            setIsGenerating(false);
            setActiveAiQuestionId(null);
        }
    }, [polledResult, activeAiQuestionId, questions]);



    useEffect(() => {
        const loadData = async () => {
            try {
                const pfRes = await fetchWithAuth(getApiUrl('/portfolios'));
                if (pfRes.ok) {
                    const data = await pfRes.json();
                    setPortfolios(data.items || data || []);
                }
            } catch (e) { console.error(e); }

            if (!isNew) {
                try {
                    const res = await fetchWithAuth(getApiUrl(`/cover-letters/${id}`));
                    const data = await res.json();
                    setTitle(data.title);
                    if (data.items?.length > 0) {
                        setQuestions(data.items.map((item: CoverLetterItem) => ({
                            id: item.id || Date.now() + Math.random(),
                            question: item.question,
                            answer: item.content,
                            key_points: item.key_points,
                            suggested_improvements: item.suggested_improvements
                        })));
                    } else if (data.questions?.length > 0) {
                        setQuestions(data.questions);
                    }

                    if (data.gap_analysis) setGapAnalysis(data.gap_analysis);

                    if (data.recruitment_id || data.recruitId) {
                        const rId = data.recruitment_id || data.recruitId;
                        const rRes = await fetchWithAuth(getApiUrl(`/recruits/${rId}`));
                        if (rRes.ok) {
                            const rData = await rRes.json();
                            setLinkedRecruit(rData);
                            setShowRecruitPanel(true);
                        }
                    }
                } catch (e) { console.error(e); }
            } else if (jobId) {
                try {
                    const rRes = await fetchWithAuth(getApiUrl(`/recruits/${jobId}`));
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
            const body = {
                title,
                questions: questions.map(q => ({ question: q.question, content: q.answer })),
                recruitId: linkedRecruit?.id
            };
            const res = await fetchWithAuth(isNew ? getApiUrl('/cover-letters') : getApiUrl(`/cover-letters/${id}`), {
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
    const runAiGeneration = async () => {
        setIsGenerating(true);
        try {
            const activeQuestionContent = questions.find(q => q.id === activeAiQuestionId)?.question || "";
            const res = await fetchWithAuth(getApiUrl('/cover-letters/generate'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mode: aiMode,
                    tone: aiTone,
                    focus: aiFocus,
                    portfolioIds: selectedPortfolioIds, // Can be empty now, backend will auto-retrieve
                    recruitId: linkedRecruit?.id,
                    question: activeQuestionContent
                })
            });

            if (!res.ok) throw new Error("AI 생성 요청에 실패했습니다.");

            const data = await res.json();
            // Start polling for this specific cover letter
            // Assuming data contains the cover letter ID
            if (data.id) {
                setPollingTarget(`/cover-letters/${data.id}`);
            } else {
                throw new Error("Invalid response from server");
            }

        } catch (e) {
            console.error(e);
            alert("AI 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            setIsGenerating(false);
        }
    };

    const applySuggestion = (qId: number, suggestion: string) => {
        const q = questions.find(item => item.id === qId);
        if (q) {
            updateQuestion(qId, 'answer', q.answer + "\n\n(참고 제안): " + suggestion);
        }
    };

    if (loading) return <div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

    return (
        <div className="flex justify-center min-h-[calc(100vh-64px)] bg-slate-50/10 overflow-x-hidden relative">
            <div className={cn("flex relative transition-all duration-500", showRecruitPanel ? "w-full max-w-[1700px]" : "w-full max-w-5xl")}>
                {/* Editor Content */}
                <div className="flex-1 p-4 md:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-6">
                        <div className="space-y-3 font-pretendard">
                            <div className="flex items-center gap-3">
                                <Button variant="ghost" size="icon" onClick={() => router.back()} className="rounded-full hover:bg-slate-100"><ArrowLeft className="h-5 w-5" /></Button>
                                <h1 className="text-2xl font-bold tracking-tight text-slate-900">{isNew ? "새 자기소개서 작성" : "자기소개서 수정"}</h1>
                            </div>
                            <div className="flex items-center gap-2">
                                {linkedRecruit && (
                                    <Badge variant="outline" className="bg-blue-50 border-blue-100 px-2 py-1 gap-1.5 font-semibold text-blue-700">
                                        <Building className="h-3 w-3" /> {linkedRecruit.company}
                                    </Badge>
                                )}
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setShowRecruitPanel(!showRecruitPanel)}
                                    className={cn("h-8 gap-1.5 text-xs border-slate-200 transition-all", showRecruitPanel && "bg-slate-900 text-white border-slate-900 shadow-md")}
                                >
                                    <LayoutList className="h-3.5 w-3.5" /> 분석 패널 {showRecruitPanel ? "닫기" : "열기"}
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
                                                const res = await fetchWithAuth(getApiUrl(`/cover-letters/${id}`), { method: 'DELETE' });
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
                            <Button variant="outline" onClick={() => router.back()} className="border-slate-200 h-10 px-6 font-semibold">취소</Button>
                            <Button variant="default" onClick={handleSave} className="rounded-md h-10 px-6 font-bold shadow-lg shadow-blue-500/20 bg-blue-600 hover:bg-blue-700">
                                <Save className="mr-2 h-4 w-4" /> 저장하기
                            </Button>
                        </div>
                    </div>

                    {/* Gap Analysis Dashboard */}
                    {gapAnalysis && (
                        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="bg-white border-2 border-slate-100 rounded-3xl p-8 shadow-sm">
                            <div className="flex items-center justify-between mb-8">
                                <div className="space-y-1">
                                    <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
                                        <Zap className="h-5 w-5 text-blue-500 fill-blue-500" /> 직무 적합성 분석 리포트
                                    </h2>
                                    <p className="text-sm text-slate-500 font-medium">AI가 분석한 지원자님의 강점과 보완점입니다.</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="text-sm font-bold text-slate-400">종합 적합도</span>
                                    <Badge className={cn(
                                        "px-4 py-1.5 text-sm font-black rounded-lg",
                                        gapAnalysis.overall_fit === '상' ? "bg-green-500 text-white" :
                                            gapAnalysis.overall_fit === '중' ? "bg-blue-500 text-white" : "bg-amber-500 text-white"
                                    )}>
                                        {gapAnalysis.overall_fit}
                                    </Badge>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-4">
                                    <h3 className="text-sm font-black text-green-700 flex items-center gap-2 ml-1">
                                        <CheckCircle className="h-4 w-4" /> Strong Points
                                    </h3>
                                    <div className="space-y-3">
                                        {gapAnalysis.matching_points.map((point, i) => (
                                            <div key={i} className="bg-green-50/50 border border-green-100 p-4 rounded-2xl flex items-start gap-3 group transition-all hover:bg-green-50">
                                                <div className="h-5 w-5 bg-green-500 text-white rounded-full flex items-center justify-center shrink-0 mt-0.5"><span className="text-[10px] font-bold">{i + 1}</span></div>
                                                <p className="text-sm font-bold text-green-900 leading-snug">{point}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <h3 className="text-sm font-black text-amber-700 flex items-center gap-2 ml-1">
                                        <AlertCircle className="h-4 w-4" /> Areas to Focus
                                    </h3>
                                    <div className="space-y-3">
                                        {gapAnalysis.missing_elements.map((point, i) => (
                                            <div key={i} className="bg-amber-50/50 border border-amber-100 p-4 rounded-2xl flex items-start gap-3 group transition-all hover:bg-amber-50">
                                                <div className="h-5 w-5 bg-amber-500 text-white rounded-full flex items-center justify-center shrink-0 mt-0.5"><span className="text-[10px] font-bold">{i + 1}</span></div>
                                                <p className="text-sm font-bold text-amber-900 leading-snug">{point}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}

                    <div className="space-y-4">
                        <Label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">문서 제목</Label>
                        <Input value={title} onChange={(e) => setTitle(e.target.value)} className="h-14 text-xl font-black border-2 border-slate-100 bg-white shadow-sm focus-visible:ring-blue-500 focus:border-blue-500 transition-all rounded-2xl" placeholder="자소서 제목을 입력하세요" />
                    </div>

                    <div className="space-y-12 pb-40">
                        <AnimatePresence mode="popLayout">
                            {questions.map((q, idx) => (
                                <motion.div key={q.id} layout initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
                                    className="bg-white border-2 border-slate-100 rounded-[2rem] p-8 shadow-sm relative group hover:shadow-xl transition-all duration-300"
                                >
                                    <div className="flex justify-between items-center mb-8">
                                        <div className="flex items-center gap-4 flex-1">
                                            <div className="flex items-center bg-slate-900 text-white rounded-xl px-4 py-2 gap-2 shrink-0 shadow-lg shadow-slate-200">
                                                <span className="text-xs font-bold uppercase tracking-widest opacity-60">ITEM</span>
                                                <span className="text-md font-black">{idx + 1}</span>
                                            </div>
                                            <Input
                                                value={q.question}
                                                onChange={e => updateQuestion(q.id, 'question', e.target.value)}
                                                className="border-none text-2xl font-black p-0 focus-visible:ring-0 w-full placeholder:text-slate-200"
                                                placeholder="질문 문항을 입력하세요"
                                            />
                                        </div>
                                        <Button variant="ghost" size="icon" onClick={() => removeQuestion(q.id)} className="text-slate-200 hover:text-red-500 hover:bg-red-50 transition-colors h-10 w-10 rounded-full"><Trash2 className="h-5 w-5" /></Button>
                                    </div>
                                    <div className="relative group/textarea">
                                        <Textarea
                                            value={q.answer}
                                            onChange={e => updateQuestion(q.id, 'answer', e.target.value)}
                                            className="min-h-[450px] resize-none border-2 border-slate-50 bg-slate-50/30 p-8 text-lg font-medium leading-relaxed focus:bg-white focus:border-blue-100 transition-all rounded-3xl scrollbar-hide shadow-inner"
                                            placeholder="답변을 입력하거나 AI 라이팅 스튜디오를 통해 초안을 생성하세요."
                                        />
                                        <div className="absolute bottom-8 right-8">
                                            <Button variant="default" onClick={() => setActiveAiQuestionId(q.id)} className="gap-2 shadow-2xl shadow-blue-500/20 px-8 h-14 rounded-2xl transition-all hover:scale-105 active:scale-95 group font-bold bg-blue-600 hover:bg-blue-700">
                                                <Brain className="h-5 w-5 group-hover:animate-bounce" /> AI 라이팅 스튜디오
                                            </Button>
                                        </div>
                                    </div>

                                    {/* AI Insights Display */}
                                    {(q.key_points?.length || q.suggested_improvements?.length) ? (
                                        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="mt-8 pt-8 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-8">
                                            {q.key_points && q.key_points.length > 0 && (
                                                <div className="space-y-4">
                                                    <h4 className="text-sm font-black text-blue-700 flex items-center gap-2 px-1">
                                                        <CheckCircle className="h-4 w-4 bg-blue-100 text-blue-600 rounded-full p-0.5" /> 답변 핵심 역량
                                                    </h4>
                                                    <div className="flex flex-wrap gap-2">
                                                        {q.key_points.map((kp, i) => (
                                                            <Badge key={i} className="bg-blue-50/80 text-blue-700 border-blue-100 hover:bg-blue-100 px-3 py-1.5 rounded-xl font-bold text-xs ring-1 ring-blue-200/50">
                                                                #{kp}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                            {q.suggested_improvements && q.suggested_improvements.length > 0 && (
                                                <div className="space-y-4">
                                                    <h4 className="text-sm font-black text-amber-700 flex items-center gap-2 px-1">
                                                        <Sparkles className="h-4 w-4 bg-amber-100 text-amber-600 rounded-full p-0.5" /> AI 개선 제안
                                                    </h4>
                                                    <div className="space-y-2">
                                                        {q.suggested_improvements.map((si, i) => (
                                                            <div
                                                                key={i}
                                                                onClick={() => applySuggestion(q.id, si)}
                                                                className="text-xs text-slate-500 bg-amber-50/30 border border-amber-100/50 rounded-xl p-3 flex items-center justify-between cursor-pointer hover:bg-amber-50 transition-all group/suggest"
                                                            >
                                                                <span className="font-semibold leading-relaxed line-clamp-1">{si}</span>
                                                                <Plus className="h-3 w-3 text-amber-400 opacity-0 group-hover/suggest:opacity-100 transition-opacity" />
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </motion.div>
                                    ) : null}
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        <motion.div layout>
                            <Button variant="outline" onClick={addQuestion} className="w-full h-16 border-dashed border-2 border-slate-200 bg-white/50 hover:bg-white hover:border-blue-200 hover:text-blue-600 transition-all rounded-[2rem] font-bold text-slate-400">
                                <Plus className="mr-2 h-6 w-6" /> 문항 추가
                            </Button>
                        </motion.div>
                    </div>
                </div>

                {/* Info Panel */}
                <div className={cn("sticky top-0 h-screen transition-all duration-700 overflow-hidden shrink-0 hidden xl:block", showRecruitPanel ? "w-[580px] opacity-100" : "w-0 opacity-0 pointer-events-none")}>
                    <div className="w-[580px] h-full px-8 pt-20 pb-24 flex flex-col overflow-visible">
                        <div className="bg-white border-2 border-slate-100 rounded-[2.5rem] shadow-2xl flex-1 flex flex-col overflow-hidden">
                            <Tabs value={panelTab} onValueChange={setPanelTab} className="h-full flex flex-col">
                                <div className="p-8 pb-4 bg-white">
                                    <div className="flex justify-between items-center mb-6">
                                        <div className="flex items-center gap-3">
                                            <div className="p-3 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/20 text-white"><Search className="h-5 w-5" /></div>
                                            <div className="space-y-0.5">
                                                <h2 className="font-black text-xl tracking-tight text-slate-900">공고 분석 패널</h2>
                                                <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">AI Context Studio</p>
                                            </div>
                                        </div>
                                        <Button variant="ghost" size="icon" onClick={() => setShowRecruitPanel(false)} className="rounded-full hover:bg-slate-100 trasition-all"><X className="h-5 w-5 text-slate-400" /></Button>
                                    </div>
                                    <TabsList className="grid grid-cols-2 w-full h-12 bg-slate-100 p-1.5 rounded-[1.25rem] mb-2 font-pretendard">
                                        <TabsTrigger value="recruit" className="rounded-[0.9rem] font-black text-xs">공고 원문</TabsTrigger>
                                        <TabsTrigger value="reference" className="rounded-[0.9rem] font-black text-xs">포트폴리오</TabsTrigger>
                                    </TabsList>
                                </div>
                                <div className="flex-1 overflow-y-auto overflow-x-hidden p-8 pt-4 scrollbar-hide font-pretendard">
                                    <TabsContent value="recruit" className="m-0 space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">
                                        {linkedRecruit ? (
                                            <div className="space-y-8 pb-8">
                                                <div className="space-y-4">
                                                    <h3 className="text-2xl font-black tracking-tight text-slate-900 leading-tight">{linkedRecruit.title}</h3>
                                                    <div className="flex flex-wrap gap-2">
                                                        <Badge variant="default" className="px-3 py-1 font-bold rounded-lg bg-blue-600 hover:bg-blue-700 text-white border-none">{linkedRecruit.company}</Badge>
                                                        {linkedRecruit.experience && <Badge variant="outline" className="border-slate-200 text-slate-600 rounded-lg px-3 py-1 font-bold">{linkedRecruit.experience}</Badge>}
                                                        {linkedRecruit.location && <Badge variant="outline" className="border-slate-200 text-slate-600 rounded-lg px-3 py-1 font-bold"><MapPin className="h-3 w-3 mr-1" />{linkedRecruit.location}</Badge>}
                                                        {linkedRecruit.salary && <Badge variant="outline" className="border-slate-200 text-slate-600 rounded-lg px-3 py-1 font-bold"><Coins className="h-3 w-3 mr-1" />{linkedRecruit.salary}</Badge>}
                                                        {linkedRecruit.education && <Badge variant="outline" className="border-slate-200 text-slate-600 rounded-lg px-3 py-1 font-bold"><GraduationCap className="h-3 w-3 mr-1" />{linkedRecruit.education}</Badge>}
                                                    </div>
                                                </div>

                                                <div className="grid grid-cols-2 gap-3">
                                                    <div className="bg-slate-50 border border-slate-100 p-4 rounded-2xl">
                                                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">공고 등록</div>
                                                        <div className="text-sm font-bold text-slate-700">{linkedRecruit.startDate || 'N/A'}</div>
                                                    </div>
                                                    <div className="bg-slate-50 border border-slate-100 p-4 rounded-2xl">
                                                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">마감 기한</div>
                                                        <div className="text-sm font-bold text-red-600">{linkedRecruit.deadline || 'N/A'}</div>
                                                    </div>
                                                </div>

                                                <div className="space-y-8">
                                                    {linkedRecruit.key_responsibilities && (
                                                        <div className="space-y-3">
                                                            <div className="flex items-center gap-2 text-sm font-black text-slate-900"><div className="h-1.5 w-1.5 bg-blue-600 rounded-full" /> 주요 업무</div>
                                                            <p className="text-[14px] text-slate-600 leading-relaxed bg-slate-50/50 p-4 rounded-2xl border border-slate-100 whitespace-pre-wrap font-medium">{linkedRecruit.key_responsibilities}</p>
                                                        </div>
                                                    )}
                                                    {linkedRecruit.required_qualifications && (
                                                        <div className="space-y-3">
                                                            <div className="flex items-center gap-2 text-sm font-black text-slate-900"><div className="h-1.5 w-1.5 bg-green-600 rounded-full" /> 자격 요건</div>
                                                            <p className="text-[14px] text-slate-600 leading-relaxed bg-slate-50/50 p-4 rounded-2xl border border-slate-100 whitespace-pre-wrap font-medium">{linkedRecruit.required_qualifications}</p>
                                                        </div>
                                                    )}
                                                    {linkedRecruit.preferred_qualifications && (
                                                        <div className="space-y-3">
                                                            <div className="flex items-center gap-2 text-sm font-black text-slate-900"><div className="h-1.5 w-1.5 bg-amber-600 rounded-full" /> 우대 사항</div>
                                                            <p className="text-[14px] text-slate-600 leading-relaxed bg-slate-50/50 p-4 rounded-2xl border border-slate-100 whitespace-pre-wrap font-medium">{linkedRecruit.preferred_qualifications}</p>
                                                        </div>
                                                    )}
                                                </div>

                                                {linkedRecruit.tags && linkedRecruit.tags.length > 0 && (
                                                    <div className="flex flex-wrap gap-2 pt-4">
                                                        {linkedRecruit.tags.map((tag, i) => (
                                                            <Badge key={i} variant="secondary" className="bg-slate-100 text-slate-500 hover:bg-slate-200 border-none px-3 py-1 font-bold text-[11px] rounded-lg">#{tag}</Badge>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ) : <div className="text-center py-24 text-slate-400 font-medium">연결된 공고가 없습니다.</div>}
                                    </TabsContent>
                                    <TabsContent value="reference" className="m-0 space-y-4 animate-in fade-in slide-in-from-right-4 duration-500">
                                        <div className="bg-blue-600 p-6 rounded-3xl shadow-xl shadow-blue-500/20 mb-4 group relative overflow-hidden">
                                            <Sparkles className="absolute -top-4 -right-4 h-24 w-24 text-white/10 rotate-12" />
                                            <p className="text-white text-md font-black mb-1 flex items-center gap-2 relative z-10">
                                                AI 자동 컨텍스트 매칭
                                            </p>
                                            <p className="text-blue-100 text-[13px] leading-relaxed font-semibold relative z-10">
                                                이제 AI가 지원자님의 포트폴리오에서 최적의 경험을 스스로 찾아 답변을 구성합니다.
                                                <span className="block mt-2 opacity-80 font-normal">필요한 경우만 수동으로 선택해 주세요.</span>
                                            </p>
                                        </div>
                                        <div className="space-y-3">
                                            {portfolios.map(pf => (
                                                <div
                                                    key={pf.id}
                                                    onClick={() => togglePortfolio(pf.id)}
                                                    className={cn(
                                                        "p-5 rounded-3xl border-2 transition-all cursor-pointer group relative overflow-hidden",
                                                        selectedPortfolioIds.includes(pf.id)
                                                            ? "bg-blue-50/50 border-blue-500 shadow-sm"
                                                            : "bg-white border-slate-50 hover:border-slate-100 hover:bg-slate-50/50 shadow-sm"
                                                    )}
                                                >
                                                    <div className="flex items-center justify-between mb-2">
                                                        <div className="flex items-center gap-3">
                                                            <div className={cn("p-2.5 rounded-xl transition-colors", selectedPortfolioIds.includes(pf.id) ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-400 group-hover:bg-white group-hover:text-blue-600")}>
                                                                {pf.type === 'github' ? <Github className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                                                            </div>
                                                            <div className="space-y-0.5">
                                                                <span className={cn("font-black text-sm tracking-tight", selectedPortfolioIds.includes(pf.id) ? "text-blue-900" : "text-slate-800")}>{pf.title}</span>
                                                                {pf.project_name && <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{pf.project_name}</p>}
                                                            </div>
                                                        </div>
                                                        <div className={cn("h-6 w-6 rounded-full border-2 flex items-center justify-center transition-all", selectedPortfolioIds.includes(pf.id) ? "bg-blue-600 border-blue-600 shadow-inner" : "bg-white border-slate-100")}>
                                                            {selectedPortfolioIds.includes(pf.id) && <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}><CheckCircle className="h-3.5 w-3.5 text-white" /></motion.div>}
                                                        </div>
                                                    </div>
                                                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed pl-[44px] font-medium">{pf.description}</p>
                                                </div>
                                            ))}
                                        </div>
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
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => !isGenerating && setActiveAiQuestionId(null)} className="absolute inset-0 bg-slate-900/40 backdrop-blur-3xl" />
                        <motion.div initial={{ opacity: 0, scale: 0.95, y: 30 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 30 }}
                            className="bg-white rounded-[3rem] shadow-[0_32px_64px_-12px_rgba(0,0,0,0.3)] w-full max-w-[700px] overflow-hidden relative border-none font-pretendard"
                        >
                            <div className="bg-slate-900 text-white p-10 flex flex-col items-center justify-center text-center relative overflow-hidden">
                                <Sparkles className="absolute -top-10 -left-10 h-40 w-40 text-blue-500/20" />
                                <div className="h-16 w-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-3xl flex items-center justify-center shadow-2xl shadow-blue-500/40 mb-6 relative z-10"><Brain className="h-8 w-8 text-white" /></div>
                                <h2 className="text-3xl font-black tracking-tight text-white mb-2 relative z-10">AI 라이팅 스튜디오</h2>
                                <p className="text-slate-400 text-sm font-bold opacity-70 relative z-10">지원자님만의 필승 전략을 설정하세요.</p>
                                {!isGenerating && (
                                    <Button
                                        variant="ghost"
                                        onClick={() => setActiveAiQuestionId(null)}
                                        className="absolute top-8 right-8 text-slate-500 hover:text-white hover:bg-white/10 rounded-full h-12 w-12 p-0"
                                    >
                                        <X className="h-6 w-6" />
                                    </Button>
                                )}
                            </div>

                            <div className="p-10 space-y-10">
                                {/* [Mode Selection] */}
                                <div className="space-y-5">
                                    <Label className="text-[11px] font-black text-slate-400 uppercase tracking-[0.25em] flex items-center gap-2 ml-1">
                                        <Zap className="h-4 w-4 text-blue-500 fill-blue-500" /> 답변 구성 모드
                                    </Label>
                                    <div className="grid grid-cols-3 gap-4">
                                        {[
                                            { id: 'draft', label: '완성형 초안', icon: <Wand2 className="h-6 w-6" />, desc: '풀 에피소드' },
                                            { id: 'strategy', label: '뼈대 개요', icon: <LayoutList className="h-6 w-6" />, desc: '논리적 설계' },
                                            { id: 'refine', label: '문장 정교화', icon: <MessageSquare className="h-6 w-6" />, desc: '어휘 최적화' }
                                        ].map(mode => (
                                            <div key={mode.id} onClick={() => setAiMode(mode.id as AiMode)} className={cn("p-6 rounded-[2rem] border-4 transition-all cursor-pointer text-center space-y-3 group relative overflow-hidden", aiMode === mode.id ? "border-blue-600 bg-blue-50/50 shadow-lg shadow-blue-500/10" : "border-slate-50 bg-slate-50/50 hover:border-slate-100 hover:bg-white")}>
                                                <div className={cn("mx-auto h-12 w-12 rounded-2xl flex items-center justify-center transition-all duration-300", aiMode === mode.id ? "bg-blue-600 text-white shadow-xl shadow-blue-500/20 scale-110" : "bg-white text-slate-300 group-hover:bg-slate-100 group-hover:text-blue-500")}>{mode.icon}</div>
                                                <div className="space-y-1">
                                                    <div className={cn("font-black text-md tracking-tight transition-colors", aiMode === mode.id ? "text-blue-900" : "text-slate-600")}>{mode.label}</div>
                                                    <div className="text-[10px] text-slate-400 font-bold opacity-60 tracking-widest">{mode.desc}</div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* [Detail Options] */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                                    <div className="space-y-4">
                                        <Label className="text-[11px] font-black text-slate-400 uppercase tracking-[0.25em] flex items-center gap-2 ml-1">
                                            <Target className="h-4 w-4 text-blue-500" /> 커스텀 요청
                                        </Label>
                                        <Textarea placeholder="예: 구체적인 프로젝트 이름과 수치를 포함해줘..." value={aiFocus} onChange={e => setAiFocus(e.target.value)} className="min-h-[140px] resize-none border-2 border-slate-50 bg-slate-50/50 focus:bg-white rounded-[1.5rem] px-5 py-4 text-[15px] font-medium leading-relaxed transition-all focus:border-blue-100 shadow-inner" />
                                    </div>
                                    <div className="space-y-4">
                                        <Label className="text-[11px] font-black text-slate-400 uppercase tracking-[0.25em] flex items-center gap-2 ml-1">
                                            <Brain className="h-4 w-4 text-blue-500" /> 말투 (Tone)
                                        </Label>
                                        <div className="grid grid-cols-1 gap-2.5">
                                            {[
                                                { id: 'professional', label: '이성적이고 전문적인' },
                                                { id: 'passionate', label: '열정이 느껴지는' },
                                                { id: 'humble', label: '겸손하고 성실한' },
                                                { id: 'confident', label: '당당하고 매력적인' }
                                            ].map(tone => (
                                                <Button key={tone.id} variant="outline" onClick={() => setAiTone(tone.id as ToneType)} className={cn("justify-start h-14 rounded-2xl border-2 px-5 text-sm font-bold transition-all", aiTone === tone.id ? "border-blue-600 bg-blue-50/50 text-blue-900 shadow-sm" : "bg-slate-50/30 border-slate-50 hover:bg-white")}>
                                                    <div className={cn("h-2.5 w-2.5 rounded-full mr-3 shadow-inner", aiTone === tone.id ? "bg-blue-600 scale-125" : "bg-slate-200")} />
                                                    {tone.label}
                                                </Button>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                <div className="pt-4">
                                    <Button variant="default" size="lg" onClick={runAiGeneration} disabled={isGenerating} className="w-full h-20 rounded-[2rem] text-xl font-black shadow-2xl shadow-blue-500/20 transition-all hover:-translate-y-1.5 active:scale-[0.97] bg-blue-600 hover:bg-blue-700">
                                        {isGenerating ? (
                                            <span className="flex items-center gap-4"><Loader2 className="h-6 w-6 animate-spin" /> 유저 데이터 분석 및 최적화 중...</span>
                                        ) : (
                                            <span className="flex items-center gap-2"><Sparkles className="h-8 w-8" /> 대소동 시작하기</span>
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
