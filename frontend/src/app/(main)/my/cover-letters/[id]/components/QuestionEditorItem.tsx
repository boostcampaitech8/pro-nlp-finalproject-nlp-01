"use client";

import React, { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Trash2, CheckCircle, Sparkles, Plus } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface QuestionItem {
    id: number;
    question: string;
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
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [question.question]);

    return (
        <motion.div layout initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white border-2 border-slate-100 rounded-[2rem] p-8 shadow-sm relative group hover:shadow-xl transition-all duration-300"
        >
            <div className="flex justify-between items-start mb-8">
                <div className="flex items-start gap-4 flex-1">
                    <div className="flex items-center bg-slate-900 text-white rounded-xl px-4 py-2 gap-2 shrink-0 shadow-lg shadow-slate-200 mt-1">
                        <span className="text-xs font-bold uppercase tracking-widest opacity-60">문항</span>
                        <span className="text-md font-black">{index + 1}</span>
                    </div>
                    <div className="flex-1 space-y-2">
                        <Textarea
                            ref={textareaRef}
                            value={question.question}
                            onChange={e => onUpdate('question', e.target.value)}
                            className="border-none text-xl font-black p-0 focus-visible:ring-0 w-full placeholder:text-slate-200 resize-none min-h-[30px] bg-transparent overflow-hidden leading-tight py-1"
                            placeholder="질문 문항을 입력하세요"
                            rows={1}
                        />
                        <div className="flex flex-wrap items-center justify-between gap-4 mt-2">
                            <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 px-3 py-1.5 rounded-xl text-slate-500 hover:border-slate-200 transition-all focus-within:ring-2 focus-within:ring-slate-100 focus-within:bg-white group">
                                <span className="text-[10px] font-bold text-slate-400">최대 글자수</span>
                                <input
                                    type="number"
                                    value={question.max_length || 1000}
                                    onChange={e => onUpdate('max_length', parseInt(e.target.value) || 1000)}
                                    className="bg-transparent border-none p-0 text-[11px] font-bold outline-none w-12 text-slate-600 text-right placeholder:text-slate-300"
                                />
                                <span className="text-[10px] font-bold text-slate-400">자</span>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={onGenerateHeadline}
                                className="text-xs font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 hover:text-blue-700 h-9 gap-2 rounded-xl"
                            >
                                <Sparkles className="h-4 w-4" /> 소제목 생성
                            </Button>
                        </div>
                    </div>
                </div>
                <Button variant="ghost" size="icon" onClick={onRemove} className="text-slate-200 hover:text-red-500 hover:bg-red-50 transition-colors h-10 w-10 rounded-full shrink-0"><Trash2 className="h-5 w-5" /></Button>
            </div>

            {/* Answer Section */}
            <div className="space-y-2">
                <div className="relative group/textarea">
                    <Textarea
                        value={question.answer}
                        onChange={e => onUpdate('answer', e.target.value)}
                        className="min-h-[450px] resize-none border-2 border-slate-50 bg-slate-50/30 p-8 text-lg font-medium leading-relaxed focus:bg-white focus:border-blue-100 transition-all rounded-3xl scrollbar-hide shadow-inner"
                        placeholder="답변을 입력하거나 AI 라이팅 스튜디오를 통해 초안을 생성하세요."
                    />
                </div>
            </div>

            {/* AI Insights Display */}
            {(question.key_points?.length || question.suggested_improvements?.length) ? (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="mt-8 pt-8 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-8">
                    {question.key_points && question.key_points.length > 0 && (
                        <div className="space-y-4">
                            <h4 className="text-sm font-black text-blue-700 flex items-center gap-2 px-1">
                                <CheckCircle className="h-4 w-4 bg-blue-100 text-blue-600 rounded-full p-0.5" /> 답변 핵심 역량
                            </h4>
                            <div className="flex flex-wrap gap-2">
                                {question.key_points.map((kp, i) => (
                                    <Badge key={i} className="bg-blue-50/80 text-blue-700 border-blue-100 hover:bg-blue-100 px-3 py-1.5 rounded-xl font-bold text-xs ring-1 ring-blue-200/50">
                                        #{kp}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    )}
                    {question.suggested_improvements && question.suggested_improvements.length > 0 && (
                        <div className="space-y-4">
                            <h4 className="text-sm font-black text-amber-700 flex items-center gap-2 px-1">
                                <Sparkles className="h-4 w-4 bg-amber-100 text-amber-600 rounded-full p-0.5" /> AI 개선 제안
                            </h4>
                            <div className="space-y-2">
                                {question.suggested_improvements.map((si, i) => (
                                    <div
                                        key={i}
                                        onClick={() => onApplySuggestion(si)}
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
    );
}
