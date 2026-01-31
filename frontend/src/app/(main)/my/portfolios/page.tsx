"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Portfolio } from "@/types";
import { useToast } from "@/components/ui/toast-context";
import { Plus, FileText, Link as LinkIcon, Github, LayoutGrid, List } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { getApiUrl, fetchWithAuth } from "@/lib/apiUtils";

export default function PortfoliosPage() {
    const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
    const { toast } = useToast();
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

    useEffect(() => {
        fetchWithAuth(getApiUrl("/portfolios"))
            .then(res => res.json())
            .then(data => {
                if (data.items) {
                    setPortfolios(data.items);
                } else {
                    setPortfolios(data);
                }
            })
            .catch(err => {
                console.error(err);
                toast("포트폴리오 목록을 불러오는데 실패했습니다.", "error");
            });
    }, [toast]);

    const formatDate = (dateString?: string) => {
        if (!dateString) return "N/A";
        const date = new Date(dateString);
        return isNaN(date.getTime()) ? "N/A" : date.toLocaleDateString();
    };

    const getIcon = (type: string) => {
        switch (type) {
            case 'github': return <Github className="h-5 w-5" />;
            case 'link': return <LinkIcon className="h-5 w-5" />;
            default: return <FileText className="h-5 w-5" />;
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500 container max-w-screen-xl mx-auto py-8 px-4 md:px-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-8 gap-4 flex-wrap">
                <div className="flex-1">
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 leading-tight">내 포트폴리오</h1>
                    <p className="text-slate-500 mt-2 font-medium">등록된 포트폴리오를 관리하고 채용 공고에 활용하세요.</p>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 shadow-inner">
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

                    <Link href="/my/portfolios/new">
                        <Button variant="brand" className="h-11 pl-5 pr-6 rounded-xl font-bold shadow-lg shadow-blue-500/10 flex items-center justify-center gap-2">
                            <Plus className="h-5 w-5" />
                            <span>새 포트폴리오 등록</span>
                        </Button>
                    </Link>
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
                        className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
                    >
                        {portfolios.map((portfolio, index) => (
                            <motion.div
                                key={portfolio.id}
                                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                                animate={{ opacity: 1, scale: 1, y: 0 }}
                                transition={{ delay: index * 0.05 }}
                            >
                                <Card className="flex flex-col h-full hover:shadow-xl transition-all duration-500 ease-in-out border-slate-200 hover:-translate-y-1.5 bg-white group overflow-visible rounded-2xl shadow-sm ring-4 ring-transparent hover:ring-blue-500/5">
                                    <CardHeader className="pb-4 relative">
                                        <StatusBadge
                                            status={portfolio.processingStatus || portfolio.processing_status || 'PENDING'}
                                            variant="card-tag"
                                        />
                                        <CardTitle className="flex items-center gap-3 text-lg font-bold text-slate-800 group-hover:text-blue-700 transition-colors duration-300">
                                            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 group-hover:bg-blue-50 group-hover:border-blue-100 transition-colors duration-300">
                                                {getIcon(portfolio.type)}
                                            </div>
                                            <span className="line-clamp-1">{portfolio.project_name || "프로젝트"}</span>
                                        </CardTitle>
                                        <div className="text-[11px] text-slate-400 font-bold flex items-center justify-between uppercase tracking-wider mt-2">
                                            <div className="flex items-center gap-2">
                                                <span>{portfolio.role || 'N/A'}</span>
                                                <span className="text-slate-200">•</span>
                                                <span>{formatDate(portfolio.createdAt)}</span>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="flex-1 pb-6 space-y-4">
                                        <p className="text-sm text-slate-500 line-clamp-3 leading-relaxed font-medium">
                                            {portfolio.description || "설명이 없습니다."}
                                        </p>

                                        {portfolio.tech_stack && portfolio.tech_stack.length > 0 && (
                                            <div className="flex flex-wrap gap-1.5 pt-2">
                                                {portfolio.tech_stack.slice(0, 4).map((tech, i) => (
                                                    <Badge key={i} variant="secondary" className="text-[10px] bg-slate-100 text-slate-600 hover:bg-slate-200">
                                                        {tech}
                                                    </Badge>
                                                ))}
                                                {portfolio.tech_stack.length > 4 && (
                                                    <span className="text-[10px] text-slate-400 font-bold self-center">+{portfolio.tech_stack.length - 4}</span>
                                                )}
                                            </div>
                                        )}
                                    </CardContent>
                                    <CardFooter className="pt-4 border-t border-slate-50 p-6 bg-slate-50/30">
                                        <Link href={`/my/portfolios/${portfolio.id}`} className="w-full">
                                            <Button variant="outline" className="w-full border-slate-200 h-10 rounded-xl hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 text-slate-600 font-black transition-[background-color,border-color,color] duration-300" size="sm">
                                                상세 보기
                                            </Button>
                                        </Link>
                                    </CardFooter>
                                </Card>
                            </motion.div>
                        ))}
                    </motion.div>
                ) : (
                    <motion.div
                        key="list"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        transition={{ duration: 0.3 }}
                        className="space-y-3"
                    >
                        {portfolios.map((portfolio, index) => (
                            <motion.div
                                key={portfolio.id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.05 }}
                            >
                                <Link href={`/my/portfolios/${portfolio.id}`} className="block group">
                                    <div className="flex items-center justify-between p-4 rounded-xl border border-slate-100 bg-white transition-all duration-500 ease-in-out group-hover:border-blue-200 group-hover:bg-slate-50/50 group-hover:translate-x-1.5 hover:shadow-md">
                                        <div className="flex items-center gap-4 flex-1 min-w-0 pr-4">
                                            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-slate-400 group-hover:bg-white group-hover:border-blue-100 group-hover:text-blue-600 transition-[background-color,border-color,color] duration-300 shrink-0">
                                                {getIcon(portfolio.type)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-3 mb-1">
                                                    <h3 className="text-base font-bold text-slate-900 group-hover:text-blue-700 transition-colors duration-300 truncate">
                                                        {portfolio.project_name || "프로젝트"}
                                                    </h3>
                                                    {portfolio.processingStatus === 'COMPLETED' && (
                                                        <Badge variant="outline" className="bg-emerald-50 border-emerald-100 text-emerald-600 text-[9px] font-black uppercase py-0 px-2 shrink-0">
                                                            Confirmed
                                                        </Badge>
                                                    )}
                                                    {portfolio.processingStatus === 'REVIEW_REQUIRED' && (
                                                        <Badge variant="outline" className="bg-amber-500 border-amber-600 text-white text-[9px] font-black uppercase py-0 px-2 shrink-0">
                                                            Review Required
                                                        </Badge>
                                                    )}
                                                    {(portfolio.processingStatus === 'PENDING' || portfolio.processingStatus === 'PROCESSING') && (
                                                        <Badge variant="outline" className="bg-yellow-50 border-yellow-100 text-yellow-600 text-[9px] font-black uppercase py-0 px-2 shrink-0 animate-pulse">
                                                            Processing
                                                        </Badge>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
                                                    <span className="truncate max-w-[200px]">{portfolio.description || "설명이 없습니다."}</span>
                                                    <span>•</span>
                                                    <span>{formatDate(portfolio.createdAt)}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4 shrink-0">
                                            <div className="text-[10px] font-black text-slate-300 uppercase tracking-widest hidden sm:block">
                                                {portfolio.role || 'N/A'}
                                            </div>
                                            <div className="h-8 w-8 rounded-full flex items-center justify-center text-slate-300 group-hover:text-blue-600 group-hover:bg-blue-50 transition-all duration-300">
                                                <LinkIcon className="h-4 w-4" />
                                            </div>
                                        </div>
                                    </div>
                                </Link>
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
