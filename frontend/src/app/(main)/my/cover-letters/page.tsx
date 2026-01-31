"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { CoverLetter } from "@/types";
import { PenTool, FileText, Calendar, Trash2, X, LayoutList, Check, LayoutGrid, List, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { getApiUrl, fetchWithAuth } from "@/lib/apiUtils";

export default function CoverLettersPage() {
    const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([]);
    const [isSelectionMode, setIsSelectionMode] = useState(false);
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

    const fetchLetters = () => {
        fetchWithAuth(getApiUrl("/cover-letters"), { cache: 'no-store' })
            .then(res => res.json())
            .then(data => {
                if (data.items) {
                    setCoverLetters(data.items);
                } else {
                    setCoverLetters(data);
                }
            })
            .catch(err => console.error(err));
    };

    useEffect(() => {
        fetchLetters();
    }, []);

    const isExpired = (deadline?: string) => {
        if (!deadline) return false;
        return new Date(deadline) < new Date();
    };

    const toggleSelection = (id: number) => {
        setSelectedIds(prev => prev.includes(id) ? prev.filter(sid => sid !== id) : [...prev, id]);
    };

    const handleBulkDelete = async () => {
        if (selectedIds.length === 0) return;
        if (!confirm(`선택한 ${selectedIds.length}개의 자기소개서를 정말 삭제하시겠습니까?`)) return;

        try {
            await Promise.all(selectedIds.map(id => fetchWithAuth(getApiUrl(`/cover-letters/${id}`), { method: 'DELETE' })));
            alert("삭제되었습니다.");
            setSelectedIds([]);
            setIsSelectionMode(false);
            fetchLetters();
        } catch (e) {
            console.error(e);
            alert("일부 항목 삭제 중 오류가 발생했습니다.");
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500 container max-w-screen-xl mx-auto py-8 px-4 md:px-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-8 flex-wrap gap-4">
                <div className="min-w-[200px]">
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 leading-tight">내 자기소개서</h1>
                    <p className="text-slate-500 mt-2 font-medium">작성 중인 자소서와 완료된 자소서를 한눈에 관리하세요.</p>
                </div>
                <div className="flex items-center gap-3 ml-auto">
                    {/* View Toggle */}
                    <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 shadow-inner mr-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setViewMode('grid')}
                            className={cn("h-8 w-10 px-0 rounded-lg transition-all", viewMode === 'grid' ? "bg-white text-blue-600 shadow-sm" : "text-slate-400 hover:text-slate-600")}
                        >
                            <LayoutGrid className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setViewMode('list')}
                            className={cn("h-8 w-10 px-0 rounded-lg transition-all", viewMode === 'list' ? "bg-white text-blue-600 shadow-sm" : "text-slate-400 hover:text-slate-600")}
                        >
                            <List className="h-4 w-4" />
                        </Button>
                    </div>

                    <div className="flex gap-2">
                        {isSelectionMode ? (
                            <>
                                <Button
                                    variant="destructive"
                                    onClick={handleBulkDelete}
                                    disabled={selectedIds.length === 0}
                                    className="h-11 pl-5 pr-6 rounded-xl font-bold shadow-lg shadow-red-500/10 flex items-center justify-center gap-2"
                                >
                                    <Trash2 className="h-4 w-4" />
                                    <span>{selectedIds.length}개 삭제</span>
                                </Button>
                                <Button
                                    variant="outline"
                                    onClick={() => { setIsSelectionMode(false); setSelectedIds([]); }}
                                    className="h-11 pl-5 pr-6 rounded-xl border-slate-200 font-bold flex items-center justify-center gap-2"
                                >
                                    <X className="h-4 w-4" />
                                    <span>취소</span>
                                </Button>
                            </>
                        ) : (
                            <Button
                                variant="outline"
                                onClick={() => setIsSelectionMode(true)}
                                className="h-11 pl-5 pr-6 rounded-xl border-slate-200 font-bold hover:bg-slate-50 flex items-center justify-center gap-2"
                            >
                                <LayoutList className="h-4 w-4" />
                                <span>일괄 관리</span>
                            </Button>
                        )}
                    </div>
                </div>
            </div>

            <AnimatePresence mode="wait">
                {viewMode === 'grid' ? (
                    <motion.div
                        key="grid"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 1.02 }}
                        transition={{ duration: 0.3 }}
                        className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3"
                    >
                        {coverLetters.map((cl, index) => {
                            const expired = isExpired(cl.recruitDeadline);
                            const isSelected = selectedIds.includes(cl.id);

                            return (
                                <motion.div
                                    key={cl.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                >
                                    <Card className={cn(
                                        "relative flex flex-col transition-all duration-500 ease-in-out group border-slate-200 bg-white h-full min-h-[300px] overflow-visible rounded-2xl ring-4 ring-transparent hover:ring-blue-500/5 shadow-sm",
                                        expired && "opacity-75 grayscale-[0.3]",
                                        isSelectionMode ? "cursor-pointer border-blue-100 shadow-sm" : "hover:shadow-xl hover:-translate-y-1.5",
                                        isSelected && "ring-2 ring-blue-500 border-blue-500 bg-blue-50/10 shadow-lg shadow-blue-500/5 hover:ring-blue-500/20"
                                    )} onClick={() => isSelectionMode && toggleSelection(cl.id)}>

                                        {/* Status Tag */}
                                        <StatusBadge
                                            status={cl.processing_status || cl.processingStatus || cl.status || 'COMPLETED'}
                                            variant="card-tag"
                                        />

                                        {/* Whole Card Link (Active only in normal mode) */}
                                        {!isSelectionMode && (
                                            <Link href={`/my/cover-letters/${cl.id}`} className="absolute inset-0 z-30 rounded-xl" />
                                        )}

                                        {/* Selection Checkbox (Active only in selection mode) */}
                                        {isSelectionMode && (
                                            <div className="absolute top-5 right-5 z-40">
                                                <div className={cn(
                                                    "h-8 w-8 rounded-full border-2 flex items-center justify-center transition-all duration-300",
                                                    isSelected
                                                        ? "bg-blue-600 border-blue-600 shadow-[0_0_15px_rgba(37,99,235,0.4)] scale-110"
                                                        : "bg-white/90 border-slate-200 backdrop-blur-md hover:border-blue-400"
                                                )}>
                                                    {isSelected && <Check className="h-4.5 w-4.5 text-white stroke-[3px]" />}
                                                </div>
                                            </div>
                                        )}

                                        <CardHeader className={cn("pb-3 space-y-4 relative z-10 transition-[padding,background-color] duration-500", isSelectionMode && "pt-10")}>
                                            <div className="flex justify-between items-start">
                                                <div className={cn("p-2.5 rounded-xl border transition-colors duration-300",
                                                    expired ? "bg-slate-100 border-slate-200 shadow-none" : (isSelected ? "bg-blue-600 border-blue-600 shadow-none" : "bg-orange-50 border-orange-100 shadow-sm")
                                                )}>
                                                    <FileText className={cn("h-5 w-5", expired ? "text-slate-400" : (isSelected ? "text-white" : "text-orange-500"))} />
                                                </div>
                                                <div className="flex flex-col items-end gap-1.5 pt-1">
                                                    {expired && (
                                                        <Badge variant="outline" className="bg-slate-200 text-slate-500 border-slate-300 text-[10px] font-black py-0.5">
                                                            마감됨
                                                        </Badge>
                                                    )}
                                                    {cl.recruitDeadline && !expired && !isSelectionMode && (
                                                        <span className="text-[10px] font-black text-red-500 animate-pulse bg-red-50 px-1.5 py-0.5 rounded border border-red-100">
                                                            D-DAY 임박
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            <div>
                                                <CardTitle className={cn(
                                                    "text-xl font-bold transition-colors duration-300 line-clamp-1 mb-1",
                                                    expired ? "text-slate-500" : (isSelected ? "text-blue-700 font-black" : "text-slate-900 group-hover:text-blue-600")
                                                )}>
                                                    {cl.title}
                                                </CardTitle>

                                                {cl.recruitTitle && (
                                                    <div className="relative z-50 flex items-center gap-2 text-sm text-slate-500 flex-wrap">
                                                        <span className={cn("font-bold", expired ? "text-slate-400" : "text-slate-700")}>{cl.recruitCompany}</span>
                                                        <span className="text-slate-200">|</span>
                                                        {!isSelectionMode ? (
                                                            <Link
                                                                href={`/recruit/${cl.recruitId}`}
                                                                className={cn("transition-colors duration-300 truncate max-w-[180px] hover:text-blue-600 hover:underline")}
                                                                onClick={(e) => { if (expired) e.preventDefault(); e.stopPropagation(); }}
                                                            >
                                                                {cl.recruitTitle}
                                                            </Link>
                                                        ) : (
                                                            <span className="truncate max-w-[180px] opacity-70 font-medium">{cl.recruitTitle}</span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </CardHeader>

                                        <CardContent className="flex-1 pb-6 relative z-10">
                                            <p className={cn("text-sm line-clamp-3 leading-relaxed", expired ? "text-slate-400" : "text-slate-500 font-medium")}>
                                                {cl.content || "작성된 내용이 없습니다."}
                                            </p>
                                        </CardContent>

                                        <CardFooter className="pt-4 border-t border-slate-50 bg-slate-50/30 p-5 mt-auto relative z-10 group-hover:bg-blue-50/40 transition-all duration-500 ease-in-out rounded-b-xl flex justify-between items-center whitespace-nowrap overflow-hidden">
                                            <div className="flex flex-col gap-1 w-full flex-1">
                                                <div className="flex items-center text-[10px] text-slate-400 font-black uppercase tracking-widest opacity-70">
                                                    <Calendar className="h-3 w-3 mr-1.5 opacity-60" />
                                                    {cl.updatedAt}
                                                </div>
                                                {cl.recruitDeadline && (
                                                    <div className={cn("text-[10px] font-black", expired ? "text-slate-400" : "text-blue-500")}>
                                                        DUE: {cl.recruitDeadline}
                                                    </div>
                                                )}
                                            </div>
                                            {!isSelectionMode && (
                                                <div className="flex items-center gap-1.5 text-blue-600 font-black text-[10px] uppercase tracking-wider group-hover:translate-x-1.5 transition-all duration-500 ease-in-out">
                                                    EDIT <ArrowRight className="h-3.5 w-3.5" />
                                                </div>
                                            )}
                                        </CardFooter>
                                    </Card>
                                </motion.div>
                            );
                        })}
                    </motion.div>
                ) : (
                    <motion.div
                        key="list"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        transition={{ duration: 0.3 }}
                        className="space-y-3 p-0"
                    >
                        {coverLetters.map((cl, index) => {
                            const expired = isExpired(cl.recruitDeadline);
                            const isSelected = selectedIds.includes(cl.id);

                            return (
                                <motion.div
                                    key={cl.id}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                >
                                    <div
                                        onClick={() => isSelectionMode && toggleSelection(cl.id)}
                                        className={cn(
                                            "relative flex items-center justify-between p-5 rounded-xl border transition-all duration-500 ease-in-out group",
                                            isSelectionMode ? "cursor-pointer" : "hover:border-blue-200 hover:bg-slate-50/50 hover:translate-x-1.5 hover:shadow-md",
                                            isSelected ? "bg-blue-50/50 border-blue-500 shadow-sm" : "bg-white border-slate-100",
                                            expired && "opacity-60"
                                        )}
                                    >
                                        {!isSelectionMode && (
                                            <Link href={`/my/cover-letters/${cl.id}`} className="absolute inset-0 z-10" />
                                        )}

                                        <div className="flex items-center gap-6 flex-1 min-w-0 pr-4">
                                            {isSelectionMode ? (
                                                <div className={cn(
                                                    "h-6 w-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-300",
                                                    isSelected ? "bg-blue-600 border-blue-600 shadow-md" : "bg-white border-slate-300"
                                                )}>
                                                    {isSelected && <Check className="h-3.5 w-3.5 text-white stroke-[3px]" />}
                                                </div>
                                            ) : (
                                                <div className={cn("hidden sm:flex p-3 rounded-xl border shrink-0 transition-colors duration-300",
                                                    expired ? "bg-slate-100 border-slate-200 text-slate-400" : "bg-orange-50 border-orange-100 text-orange-500"
                                                )}>
                                                    <FileText className="h-6 w-6" />
                                                </div>
                                            )}

                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-3 mb-1.5">
                                                    <h3 className={cn("text-lg font-bold truncate group-hover:text-blue-600 transition-colors duration-300", expired ? "text-slate-500" : "text-slate-900")}>
                                                        {cl.title}
                                                    </h3>
                                                    <div className="flex gap-1">
                                                        <StatusBadge
                                                            status={cl.processing_status || cl.processingStatus || cl.status || 'PENDING'}
                                                            variant="card-tag"
                                                        />
                                                        {expired && (
                                                            <Badge variant="outline" className="bg-slate-200 text-slate-500 border-slate-300 text-[9px] font-black uppercase py-0 px-2">
                                                                Expired
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    {cl.recruitDeadline && !expired && !isSelectionMode && (
                                                        <span className="text-[9px] font-black text-red-500 animate-pulse bg-red-50 px-1.5 py-0 rounded border border-red-100">
                                                            D-DAY 임박
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-3 text-xs text-slate-400 font-medium whitespace-nowrap overflow-hidden">
                                                    <span className="font-bold text-slate-600 shrink-0">{cl.recruitCompany}</span>
                                                    <span className="opacity-30">|</span>
                                                    <span className="truncate">{cl.recruitTitle}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-8 shrink-0">
                                            <div className="hidden md:flex flex-col items-end gap-1 shrink-0 text-right">
                                                <div className="text-[11px] font-black text-slate-300 uppercase tracking-widest flex items-center gap-1.5 opacity-60">
                                                    <Calendar className="h-3 w-3" /> {cl.updatedAt}
                                                </div>
                                                {cl.recruitDeadline && (
                                                    <div className={cn("text-[10px] font-black", expired ? "text-slate-300" : "text-blue-500")}>
                                                        DUE: {cl.recruitDeadline}
                                                    </div>
                                                )}
                                            </div>
                                            {!isSelectionMode && (
                                                <Button size="sm" variant="outline" className="rounded-lg h-9 font-black text-[11px] border-slate-200 hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all duration-500 ease-in-out uppercase tracking-widest hidden sm:flex">
                                                    View Detail
                                                </Button>
                                            )}
                                            <div className="ml-2 h-8 w-8 rounded-full flex items-center justify-center text-slate-300 group-hover:text-blue-600 group-hover:bg-blue-50 transition-all duration-300 sm:hidden">
                                                <PenTool className="h-4 w-4" />
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
