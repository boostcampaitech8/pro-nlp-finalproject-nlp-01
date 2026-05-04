"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Brain, X, Zap, Wand2, LayoutList, MessageSquare, Target, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type AiMode = 'draft' | 'strategy' | 'refine';
type ToneType = 'professional' | 'passionate' | 'humble' | 'confident';

interface AiStudioModalProps {
    isOpen: boolean;
    onClose: () => void;
    aiMode: AiMode;
    setAiMode: (mode: AiMode) => void;
    aiTone: ToneType;
    setAiTone: (tone: ToneType) => void;
    aiFocus: string;
    setAiFocus: (focus: string) => void;
    isGenerating: boolean;
    onRunGeneration: () => void;
}

export function AiStudioModal({
    isOpen,
    onClose,
    aiMode,
    setAiMode,
    aiTone,
    setAiTone,
    aiFocus,
    setAiFocus,
    isGenerating,
    onRunGeneration
}: AiStudioModalProps) {
    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => !isGenerating && onClose()} className="absolute inset-0 bg-slate-900/40 backdrop-blur-3xl" />
                    <motion.div initial={{ opacity: 0, scale: 0.95, y: 30 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 30 }}
                        className="bg-white rounded-[3rem] shadow-[0_32px_64px_-12px_rgba(0,0,0,0.3)] w-full max-w-[700px] overflow-hidden relative border-none font-pretendard"
                    >
                        <div className="bg-slate-900 text-white p-10 flex flex-col items-center justify-center text-center relative overflow-hidden rounded-t-[3rem]">
                            <Sparkles className="absolute -top-10 -left-10 h-40 w-40 text-blue-500/20" />
                            <div className="h-16 w-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-3xl flex items-center justify-center shadow-2xl shadow-blue-500/40 mb-6 relative z-10"><Brain className="h-8 w-8 text-white" /></div>
                            <h2 className="text-3xl font-black tracking-tight text-white mb-2 relative z-10">AI 라이팅 스튜디오</h2>
                            <p className="text-slate-400 text-sm font-bold opacity-70 relative z-10">지원자님만의 필승 전략을 설정하세요.</p>
                            {!isGenerating && (
                                <Button
                                    variant="ghost"
                                    onClick={onClose}
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
                                        { id: 'draft', label: '기본 스타일', icon: <Wand2 className="h-6 w-6" />, desc: '풀 에피소드' },
                                        { id: 'strategy', label: '가이드라인 생성', icon: <LayoutList className="h-6 w-6" />, desc: '논리적 설계' },
                                        { id: 'refine', label: '소제목 스타일', icon: <MessageSquare className="h-6 w-6" />, desc: '어휘 최적화' }
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
                                <Button variant="default" size="lg" onClick={onRunGeneration} disabled={isGenerating} className="w-full h-20 rounded-[2rem] text-xl font-black shadow-2xl shadow-blue-500/20 transition-all hover:-translate-y-1.5 active:scale-[0.97] bg-blue-600 hover:bg-blue-700">
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
    );
}
