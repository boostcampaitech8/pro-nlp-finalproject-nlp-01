"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, Clock, RotateCcw, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CoverLetterVersion } from "@/types";
import { cn } from "@/lib/utils";

interface VersionHistoryPanelProps {
    isOpen: boolean;
    onClose: () => void;
    versions: CoverLetterVersion[];
    onRestore: (version: CoverLetterVersion) => void;
}

export function VersionHistoryPanel({ isOpen, onClose, versions, onRestore }: VersionHistoryPanelProps) {
    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-[90] xl:hidden"
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ x: "100%" }}
                        animate={{ x: 0 }}
                        exit={{ x: "100%" }}
                        transition={{ type: "spring", damping: 25, stiffness: 200 }}
                        className="fixed right-0 top-0 h-screen w-full max-w-sm bg-white border-l border-slate-100 shadow-2xl z-[100] flex flex-col font-pretendard"
                    >
                        {/* Header */}
                        <div className="p-6 border-b border-slate-50 flex items-center justify-between bg-slate-50/50">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-blue-600 rounded-lg shadow-lg shadow-blue-500/20">
                                    <Clock className="h-5 w-5 text-white" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-800">버전 내역</h3>
                                    <p className="text-[10px] text-slate-400 font-medium">저장 시 마다 스냅샷이 생성됩니다</p>
                                </div>
                            </div>
                            <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-slate-200 h-8 w-8">
                                <X className="h-4 w-4 text-slate-500" />
                            </Button>
                        </div>

                        {/* Versions List */}
                        <div className="flex-1 p-4 overflow-y-auto">
                            <div className="space-y-4">
                                {versions.length === 0 ? (
                                    <div className="py-20 text-center space-y-3">
                                        <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-slate-50 text-slate-300">
                                            <Clock className="h-6 w-6" />
                                        </div>
                                        <p className="text-sm text-slate-400 font-medium tracking-tight">이전 버전이 없습니다.</p>
                                    </div>
                                ) : (
                                    versions.map((ver, idx) => (
                                        <motion.div
                                            key={ver.id}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            className="group bg-white border border-slate-100 rounded-2xl p-4 hover:border-blue-200 hover:shadow-md transition-all cursor-default relative overflow-hidden"
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <div className="space-y-1">
                                                    <div className="text-xs font-bold text-slate-800 truncate max-w-[180px]">
                                                        {ver.title || "제목 없음"}
                                                    </div>
                                                    <div className="text-[10px] text-slate-400 flex items-center gap-1">
                                                        <Clock className="h-3 w-3" />
                                                        {new Date(ver.created_at).toLocaleString('ko-KR', {
                                                            month: 'short',
                                                            day: 'numeric',
                                                            hour: '2-digit',
                                                            minute: '2-digit'
                                                        })}
                                                    </div>
                                                </div>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => onRestore(ver)}
                                                    className="h-7 px-2 text-[10px] font-bold text-blue-600 hover:bg-blue-50 hover:text-blue-700 rounded-lg gap-1"
                                                >
                                                    <RotateCcw className="h-3 w-3" /> 복원
                                                </Button>
                                            </div>
                                            <div className="flex flex-wrap gap-1 mt-3">
                                                {ver.items_snapshot.map((it, i) => (
                                                    <div key={i} className="px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md text-[9px] font-bold text-slate-400 group-hover:bg-blue-50/50 group-hover:border-blue-100 group-hover:text-blue-500 transition-colors">
                                                        문항 {i + 1}
                                                    </div>
                                                ))}
                                            </div>
                                            <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <ChevronRight className="h-4 w-4 text-blue-300" />
                                            </div>
                                        </motion.div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="p-6 bg-slate-50/50 border-t border-slate-100">
                            <p className="text-[10px] text-slate-400 leading-relaxed">
                                * 복원 시 현재 작성 중인 내용은 복원된 버전의 내용으로 교체됩니다. 중요한 내용은 미리 저장해 주세요.
                            </p>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
