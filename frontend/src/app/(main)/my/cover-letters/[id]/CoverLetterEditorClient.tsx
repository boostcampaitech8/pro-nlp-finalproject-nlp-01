"use client";

import { useEffect, useState, use } from "react";
import { Button } from "@/components/ui/button";
import { usePolling } from "@/hooks/usePolling";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSearchParams, useRouter } from "next/navigation";
import {
    ArrowLeft, Save, Sparkles, Loader2, Building,
    Plus, Trash2
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { getApiUrl, fetchWithAuth } from "@/lib/apiUtils";
import { CoverLetterItem, GapAnalysisResult, NotificationEventDetail } from "@/types";

// --- Sub-Components ---
import { RecruitInfoPanel } from "./components/RecruitInfoPanel";
import { GapAnalysisReport } from "./components/GapAnalysisReport";
import { QuestionEditorItem } from "./components/QuestionEditorItem";

// --- Types ---
interface QuestionItem {
    id: number;
    question: string;
    answer: string;
    hint?: string;
    max_length?: number;
    key_points?: string[];
    suggested_improvements?: string[];
}

// Portfolio interface removed

interface RecruitDetail {
    id: number;
    company: string;
    title: string;
    start_date?: string;
    deadline?: string;
    content?: string;
    location?: string;
    experience?: string;
    education?: string;
    salary?: string;
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
        { id: 1, question: "1. 현재 회사에 지원한 이유와 앞으로 키워 나갈 커리어 계획을 작성해주시기 바랍니다.", answer: "" },
        { id: 2, question: "2. 지원 직무와 관련하여 어떠한 역량을(지식/기술 등) 강점으로 가지고 있는지, 그 역량을 갖추기 위해 무슨 노력과 경험을 했는지 구체적으로 작성해주시기 바랍니다.", answer: "" },
        { id: 3, question: "3. 협업을 통해 공동의 목표를 달성하기 위한 경험과 그 과정에서 갈등(문제) 상황을 해결하기 위해 어떤 역할을 했는지 구체적으로 기술하여 주십시오 (협업 기여 및 역할 / 갈등ㆍ문제 해결 능력 / 경험 기반 성장ㆍ개선 의지)", answer: "" }
    ]);

    const [linkedRecruit, setLinkedRecruit] = useState<RecruitDetail | null>(null);
    const [gapAnalysis, setGapAnalysis] = useState<GapAnalysisResult | null>(null);
    const [loading, setLoading] = useState(!isNew);
    const [showRecruitPanel, setShowRecruitPanel] = useState(false);
    // const [portfolios, setPortfolios] = useState<Portfolio[]>([]); // Unused
    // const [selectedPortfolioIds, setSelectedPortfolioIds] = useState<number[]>([]); // Unused
    const [panelTab, setPanelTab] = useState("recruit");
    const [status, setStatus] = useState<'PENDING' | 'PROCESSING' | 'REVIEW_REQUIRED' | 'COMPLETED' | 'FAILED' | null>(null);

    // --- AI Studio State ---
    const [aiMode, setAiMode] = useState<AiMode>('draft');
    const [aiTone, setAiTone] = useState<ToneType>('professional');
    const [aiFocus, setAiFocus] = useState("");
    const [subheading, setSubheading] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);

    // Polling logic for AI generation result
    const [pollingTarget, setPollingTarget] = useState<string>("");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: polledResult } = usePolling<any>(
        pollingTarget,
        3000,
        (data) => (data.processing_status || data.status) === 'REVIEW_REQUIRED' ||
            (data.processing_status || data.status) === 'COMPLETED' ||
            (data.processing_status || data.status) === 'FAILED'
    );

    const handleConfirm = async () => {
        if (isNew) {
            alert("먼저 저장해 주세요.");
            return;
        }
        try {
            const res = await fetchWithAuth(getApiUrl(`/cover-letters/${id}/confirm`), {
                method: 'PATCH',
            });
            if (res.ok) {
                const updated = await res.json();
                setStatus(updated.processing_status || updated.status);
                alert("자기소개서가 최종 확정되었습니다!");
            } else {
                alert("확정에 실패했습니다.");
            }
        } catch (e) {
            console.error(e);
            alert("처리 중 오류가 발생했습니다.");
        }
    };

    // Effect to handle polled data updates
    useEffect(() => {
        if (!polledResult) return;

        const currentStatus = polledResult.processing_status || polledResult.status;
        const isDone = ['REVIEW_REQUIRED', 'COMPLETED', 'FAILED'].includes(currentStatus);

        if (isDone) {
            setStatus(currentStatus);

            if (currentStatus !== 'FAILED') {
                if (polledResult.gap_analysis) {
                    setGapAnalysis(prev => ({ ...prev, ...polledResult.gap_analysis }));
                }

                if (polledResult.items && Array.isArray(polledResult.items) && polledResult.items.length > 0) {
                    setQuestions(polledResult.items.map((item: CoverLetterItem) => ({
                        id: item.id || Date.now() + Math.random(),
                        question: item.question,
                        answer: item.content,
                        hint: item.hint,
                        max_length: item.max_length,
                        key_points: item.key_points,
                        suggested_improvements: item.suggested_improvements
                    })));
                }
            } else {
                alert("AI 생성에 실패했습니다.");
            }

            setPollingTarget("");
            setIsGenerating(false);
        }
    }, [polledResult]);



    useEffect(() => {
        const loadData = async () => {
            if (!isNew) {
                try {
                    const res = await fetchWithAuth(getApiUrl(`/cover-letters/${id}`));
                    const data = await res.json();
                    setTitle(data.title);
                    if (data.items && Array.isArray(data.items) && data.items.length > 0) {
                        setQuestions(data.items.map((item: CoverLetterItem) => ({
                            id: item.id || Date.now() + Math.random(),
                            question: item.question,
                            answer: item.content,
                            hint: item.hint,
                            max_length: item.max_length,
                            key_points: item.key_points,
                            suggested_improvements: item.suggested_improvements
                        })));
                    } else if (data.questions && Array.isArray(data.questions) && data.questions.length > 0) {
                        setQuestions(data.questions);
                    }

                    if (data.gap_analysis) setGapAnalysis(data.gap_analysis);
                    setStatus(data.processing_status || data.status);

                    console.log("[CoverLetterEditor] Loaded data:", data); // Debug Log

                    if (data.recruitment_id || data.recruit_id) {
                        const rId = data.recruitment_id || data.recruit_id;
                        console.log("[CoverLetterEditor] Fetching recruit info for:", rId); // Debug Log
                        const rRes = await fetchWithAuth(getApiUrl(`/recruits/${rId}`));
                        if (rRes.ok) {
                            const rData = await rRes.json();
                            setLinkedRecruit(rData);
                            setShowRecruitPanel(true);
                        } else {
                            console.error("[CoverLetterEditor] Failed to fetch recruit info");
                        }
                    } else {
                        console.warn("[CoverLetterEditor] No recruit_id found in cover letter data");
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
                questions: questions.map(q => ({
                    question: q.question,
                    content: q.answer,
                    hint: q.hint,
                    max_length: q.max_length
                })),
                recruit_id: linkedRecruit?.id
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
    const updateQuestion = (qId: number, field: 'question' | 'answer' | 'hint', value: string) =>
        setQuestions(questions.map(q => q.id === qId ? { ...q, [field]: value } : q));

    // Unused togglePortfolio removed

    // --- AI Studio Logic ---
    const runAiGeneration = async () => {
        if (!linkedRecruit?.id) {
            alert("연결된 채용 공고 정보를 불러오지 못했습니다. 페이지를 새로고침하거나 잠시 후 다시 시도해주세요.");
            return;
        }

        setIsGenerating(true);
        try {
            const allQuestions = questions.map(q => q.question).filter(q => q.trim() !== "");
            const res = await fetchWithAuth(getApiUrl('/cover-letters/generate'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mode: aiMode === 'strategy' ? 'outline' : 'full',
                    tone: aiTone,
                    recruit_id: linkedRecruit?.id,
                    cover_letter_id: isNew ? undefined : parseInt(id),
                    portfolio_ids: [],
                    questions: allQuestions,
                    subheading: subheading
                })
            });

            if (!res.ok) throw new Error("AI 생성 요청에 실패했습니다.");

            const data = await res.json();
            // Start polling for this specific cover letter
            if (data.id) {
                setPollingTarget(`/cover-letters/${data.id}`);
                // Fix: Redirect to the real ID so subsequent actions (like Confirm) work
                if (isNew) {
                    router.replace(`/my/cover-letters/${data.id}`);
                }
                setStatus('PENDING');
            } else {
                throw new Error("Invalid response from server");
            }

        } catch (e) {
            console.error(e);
            alert("AI 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            setIsGenerating(false);
        }
    };

    // Real-time update listener
    useEffect(() => {
        const handleNotification = (e: Event) => {
            const customEvent = e as CustomEvent<NotificationEventDetail>;
            const { type, data } = customEvent.detail;
            if (type === 'COVER_LETTER_READY' || type === 'COVER_LETTER_COMPLETED') {
                if (data.target_id === parseInt(id) || (isNew && status === 'PENDING')) {
                    console.log("Real-time cover letter update triggered in Editor");
                    // Force refresh data
                    fetchWithAuth(getApiUrl(`/cover-letters/${data.target_id || id}`))
                        .then(res => res.json())
                        .then(updated => {
                            setStatus(updated.processing_status || updated.status);
                            if (updated.items) {
                                setQuestions(updated.items.map((item: CoverLetterItem) => ({
                                    id: item.id || Date.now() + Math.random(),
                                    question: item.question,
                                    answer: item.content,
                                    hint: item.hint,
                                    max_length: item.max_length,
                                    key_points: item.key_points,
                                    suggested_improvements: item.suggested_improvements
                                })));
                            }
                            if (updated.gap_analysis) setGapAnalysis(updated.gap_analysis);
                            setIsGenerating(false);
                            setPollingTarget("");
                        });
                }
            }
        };

        window.addEventListener('notification_event', handleNotification);
        return () => window.removeEventListener('notification_event', handleNotification);
    }, [id, isNew, status]);

    const applySuggestion = (qId: number, suggestion: string) => {
        const q = questions.find(item => item.id === qId);
        if (q) {
            updateQuestion(qId, 'answer', q.answer + "\n\n(참고 제안): " + suggestion);
        }
    };

    if (loading) return <div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

    return (
        <div className="flex justify-center h-[calc(100vh-64px)] bg-slate-50/10 overflow-hidden relative">
            <div className={cn("flex relative h-full w-full transition-all duration-500", showRecruitPanel ? "max-w-[1700px]" : "max-w-5xl")}>
                {/* Editor Content */}
                <div className="flex-1 overflow-y-auto h-full p-4 md:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 scrollbar-hide">
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
                                <StatusBadge
                                    status={status || 'PENDING'}
                                />
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setShowRecruitPanel(!showRecruitPanel)}
                                    className={cn("h-8 gap-1.5 text-xs border-slate-200 transition-all", showRecruitPanel && "bg-slate-900 text-white border-slate-900 shadow-md")}
                                >
                                    <Sparkles className="h-3.5 w-3.5" /> 스튜디오 {showRecruitPanel ? "닫기" : "열기"}
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

                            {status === 'REVIEW_REQUIRED' ? (
                                <>
                                    <Button variant="outline" onClick={() => router.back()} className="border-slate-200 h-10 px-6 font-semibold">취소</Button>
                                    <Button variant="brand" onClick={handleConfirm} className="rounded-md h-10 px-8 font-black shadow-lg shadow-blue-500/20 animate-bounce">
                                        <Sparkles className="mr-2 h-4 w-4 fill-white" /> 이 내용으로 최종 확정
                                    </Button>
                                </>
                            ) : (
                                <>
                                    <Button variant="outline" onClick={() => router.back()} className="border-slate-200 h-10 px-6 font-semibold">취소</Button>
                                    <Button variant="default" onClick={handleSave} className="rounded-md h-10 px-6 font-bold shadow-lg shadow-blue-500/20 bg-blue-600 hover:bg-blue-700">
                                        <Save className="mr-2 h-4 w-4" /> 저장하기
                                    </Button>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Gap Analysis Dashboard */}
                    <GapAnalysisReport gapAnalysis={gapAnalysis} />

                    <div className="space-y-4">
                        <Label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">문서 제목</Label>
                        <Input value={title} onChange={(e) => setTitle(e.target.value)} className="h-14 text-xl font-black border-2 border-slate-100 bg-white shadow-sm focus-visible:ring-blue-500 focus:border-blue-500 transition-all rounded-2xl" placeholder="자소서 제목을 입력하세요" />
                    </div>

                    <div className="space-y-12 pb-40">
                        <AnimatePresence mode="popLayout">
                            {questions.map((q, idx) => (
                                <QuestionEditorItem
                                    key={q.id}
                                    question={q}
                                    index={idx}
                                    onUpdate={(field, value) => updateQuestion(q.id, field, value)}
                                    onRemove={() => removeQuestion(q.id)}
                                    onApplySuggestion={(si) => applySuggestion(q.id, si)}
                                />
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
                <RecruitInfoPanel
                    isOpen={showRecruitPanel}
                    onClose={() => setShowRecruitPanel(false)}
                    recruit={linkedRecruit}
                    panelTab={panelTab}
                    setPanelTab={setPanelTab}

                    aiMode={aiMode}
                    setAiMode={setAiMode}
                    aiTone={aiTone}
                    setAiTone={setAiTone}
                    aiFocus={aiFocus}
                    setAiFocus={setAiFocus}
                    subheading={subheading}
                    setSubheading={setSubheading}
                    isGenerating={isGenerating}
                    onRunGeneration={runAiGeneration}
                />
            </div>
        </div>
    );
}
