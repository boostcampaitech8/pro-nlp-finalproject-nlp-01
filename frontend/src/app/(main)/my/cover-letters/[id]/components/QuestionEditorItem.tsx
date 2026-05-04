"use client";

import React, { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Trash2, CheckCircle, Sparkles, Plus } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface QuestionItem {
    id: number;
    question: string;
    // Title input removed
    answer: string;
    hint?: string;
    max_length?: number;
    key_points?: string[];
    suggested_improvements?: string[];
}

interface QuestionEditorItemProps {
    question: QuestionItem;
    index: number;
    onUpdate: (field: keyof QuestionItem, value: string | number) => void;
    onRemove: () => void;
    onApplySuggestion: (suggestion: string) => void;
    onGenerateHeadline: () => void;
}

export function QuestionEditorItem({
    question,
    index,
    onUpdate,
    onRemove,
    onApplySuggestion,
    onGenerateHeadline
}: QuestionEditorItemProps) {
    const questionRef = useRef<HTMLTextAreaElement>(null);
    const answerRef = useRef<HTMLTextAreaElement>(null);

    const autoResize = (elem: HTMLTextAreaElement) => {
        elem.style.height = 'auto';
        elem.style.height = `${elem.scrollHeight}px`;
    };

    useEffect(() => {
        if (questionRef.current) autoResize(questionRef.current);
    }, [question.question]);

    useEffect(() => {
        if (answerRef.current) autoResize(answerRef.current);
    }, [question.answer]);

    return (
        <motion.div layout initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
            className="bg-card border-2 border-border rounded-[2rem] p-8 shadow-sm relative group hover:shadow-xl transition-all duration-300"
        >
            <div className="flex justify-between items-start mb-8">
                <div className="flex items-start gap-4 flex-1">
                    <div className="flex items-center bg-foreground text-background rounded-xl px-4 py-2 gap-2 shrink-0 shadow-lg shadow-black/5 mt-1">
                        <span className="text-xs font-bold uppercase tracking-widest opacity-60">문항</span>
                        <span className="text-md font-black">{index + 1}</span>
                    </div>
                    <div className="flex-1 space-y-2">
                        <Textarea
                            ref={questionRef}
                            value={question.question}
                            onChange={(e) => {
                                onUpdate('question', e.target.value);
                                autoResize(e.target);
                            }}
                            className="border-none text-xl font-black p-0 focus-visible:ring-0 w-full placeholder:text-muted-foreground/40 resize-none min-h-[30px] bg-transparent overflow-hidden leading-tight py-1 text-foreground"
                            placeholder="질문 문항을 입력하세요"
                            rows={1}
                        />
                        <div className="flex flex-wrap items-center justify-between gap-4 mt-2">
                            <div className="flex items-center gap-2 bg-muted border border-border px-3 py-1.5 rounded-xl text-muted-foreground hover:border-slate-400 dark:hover:border-slate-600 transition-all focus-within:ring-2 focus-within:ring-primary/20 focus-within:bg-card group">
                                <span className="text-[10px] font-bold text-muted-foreground">최대 글자수</span>
                                <input
                                    type="number"
                                    value={question.max_length || 1000}
                                    onChange={e => onUpdate('max_length', parseInt(e.target.value) || 1000)}
                                    className="bg-transparent border-none p-0 text-[11px] font-bold outline-none w-12 text-foreground text-right placeholder:text-muted-foreground"
                                />
                                <span className="text-[10px] font-bold text-muted-foreground">자</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2 ml-4 self-start">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onGenerateHeadline}
                        className="text-xs font-bold text-blue-600 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50 hover:text-blue-700 h-9 gap-1.5 rounded-xl px-3 transition-colors"
                    >
                        <Sparkles className="h-3.5 w-3.5" /> 소제목 생성
                    </Button>
                    <Button variant="ghost" size="icon" onClick={onRemove} className="text-muted-foreground hover:text-red-500 hover:bg-red-50/10 transition-colors h-9 w-9 rounded-full shrink-0"><Trash2 className="h-4 w-4" /></Button>
                </div>
            </div>

            {/* Answer Section */}
            <div className="space-y-3">



                <div className="relative group/textarea">
                    <Textarea
                        ref={answerRef}
                        value={question.answer}
                        onChange={(e) => {
                            onUpdate('answer', e.target.value);
                            autoResize(e.target);
                        }}
                        className="resize-none border-2 border-border bg-muted/30 p-8 text-lg font-medium leading-relaxed focus:bg-card focus:border-primary/50 transition-colors rounded-3xl scrollbar-hide shadow-inner text-foreground placeholder:text-muted-foreground/50"
                        placeholder="답변을 입력하거나 AI 라이팅 스튜디오를 통해 초안을 생성하세요."
                    />
                    <div className="absolute bottom-6 right-6 pointer-events-none transition-opacity duration-300 opacity-50 group-hover/textarea:opacity-100">
                        <span className={cn(
                            "text-xs font-bold px-2 py-1 rounded-md backdrop-blur-sm transition-colors",
                            (question.answer?.length || 0) > (question.max_length || 1000)
                                ? "text-red-500 bg-red-50/80 dark:bg-red-950/50"
                                : "text-muted-foreground/60 bg-background/50"
                        )}>
                            {question.answer?.length || 0} / {question.max_length || 1000}자
                        </span>
                    </div>
                </div>
            </div>

            {/* AI Insights Display */}
            {(question.key_points?.length || question.suggested_improvements?.length) ? (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="mt-8 pt-8 border-t border-border grid grid-cols-1 md:grid-cols-2 gap-8">
                    {question.key_points && question.key_points.length > 0 && (
                        <div className="space-y-4">
                            <h4 className="text-sm font-black text-blue-600 dark:text-blue-400 flex items-center gap-2 px-1">
                                <CheckCircle className="h-4 w-4 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-full p-0.5" /> 답변 핵심 역량
                            </h4>
                            <div className="flex flex-wrap gap-2">
                                {question.key_points.map((kp, i) => (
                                    <Badge key={i} className="bg-blue-50/80 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-100 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/40 px-3 py-1.5 rounded-xl font-bold text-xs ring-1 ring-blue-200/50 dark:ring-blue-800/50">
                                        #{kp}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    )}
                    {question.suggested_improvements && question.suggested_improvements.length > 0 && (
                        <div className="space-y-4">
                            <h4 className="text-sm font-black text-amber-700 dark:text-amber-500 flex items-center gap-2 px-1">
                                <Sparkles className="h-4 w-4 bg-amber-100 dark:bg-amber-900/50 text-amber-600 dark:text-amber-500 rounded-full p-0.5" /> AI 개선 제안
                            </h4>
                            <div className="space-y-2">
                                {question.suggested_improvements.map((si, i) => (
                                    <div
                                        key={i}
                                        onClick={() => onApplySuggestion(si)}
                                        className="text-xs text-muted-foreground bg-amber-50/30 dark:bg-amber-950/20 border border-amber-100/50 dark:border-amber-900/30 rounded-xl p-3 flex items-center justify-between cursor-pointer hover:bg-amber-50 dark:hover:bg-amber-900/30 transition-all group/suggest"
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
    );
}
