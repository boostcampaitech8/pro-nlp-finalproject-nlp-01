"use client";

import { motion } from "framer-motion";
import { Zap, CheckCircle, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { GapAnalysisResult } from "@/types";

interface GapAnalysisReportProps {
    gapAnalysis: GapAnalysisResult | null;
}

export function GapAnalysisReport({ gapAnalysis }: GapAnalysisReportProps) {
    if (!gapAnalysis) return null;

    return (
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
                        {gapAnalysis.matching_points?.map((point, i) => (
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
                        {gapAnalysis.missing_elements?.map((point, i) => (
                            <div key={i} className="bg-amber-50/50 border border-amber-100 p-4 rounded-2xl flex items-start gap-3 group transition-all hover:bg-amber-50">
                                <div className="h-5 w-5 bg-amber-500 text-white rounded-full flex items-center justify-center shrink-0 mt-0.5"><span className="text-[10px] font-bold">{i + 1}</span></div>
                                <p className="text-sm font-bold text-amber-900 leading-snug">{point}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
