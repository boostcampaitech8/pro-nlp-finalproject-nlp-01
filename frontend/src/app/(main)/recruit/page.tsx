"use client";

import { useEffect, useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Recruit } from "@/types";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { useAuthStore } from "@/stores/useAuthStore";
import { Sparkles, Flame, LayoutGrid, List, ArrowRight, Building, Calendar, MoreHorizontal, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

export default function RecruitPage() {
    const { isAuthenticated } = useAuthStore();
    const [recruits, setRecruits] = useState<Recruit[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [itemsPerPage] = useState(9);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [activeTab, setActiveTab] = useState("all");

    // 필터 상태
    const [selectedCategory, setSelectedCategory] = useState("all");
    const [selectedTechs, setSelectedTechs] = useState<string[]>([]);
    const [searchQuery, setSearchQuery] = useState("");

    const JOB_CATEGORIES = [
        { label: "전체", value: "all" },
        { label: "프론트엔드", value: "frontend" },
        { label: "서버/백엔드", value: "backend" },
        { label: "웹 풀스택", value: "fullstack" },
        { label: "AI/ML/NLP", value: "ai" },
        { label: "데이터", value: "data" },
        { label: "모바일", value: "mobile" },
        { label: "DevOps", value: "devops" },
    ];

    const TECH_STACKS = ["React", "TypeScript", "Next.js", "Java", "Spring", "Python", "PyTorch", "Node.js", "Go", "Swift", "AWS", "Kubernetes"];

    const fetchRecruits = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: currentPage.toString(),
                limit: itemsPerPage.toString(),
                category: selectedCategory,
                techStack: selectedTechs.join(','),
                keyword: searchQuery,
            });

            if (activeTab === 'popular') {
                params.append('sort', 'popular');
            }

            const endpoint = activeTab === 'recommend' ? '/api/recruits/recommend' : '/api/recruits';
            const res = await fetch(`${endpoint}?${params.toString()}`);
            const data = await res.json();

            setRecruits(data.items || []);
            setTotalPages(data.meta?.totalPages || 1);
        } catch (err) {
            console.error("Failed to fetch recruits", err);
        } finally {
            setLoading(false);
        }
    }, [activeTab, currentPage, itemsPerPage, selectedCategory, selectedTechs, searchQuery]);

    useEffect(() => {
        fetchRecruits();
    }, [fetchRecruits, isAuthenticated]);

    const toggleTech = (tech: string) => {
        setSelectedTechs(prev =>
            prev.includes(tech) ? prev.filter(t => t !== tech) : [...prev, tech]
        );
        setCurrentPage(1); // 필터 변경 시 첫 페이지로
    };

    // 공통 카드 렌더링 함수
    const renderRecruitList = (items: Recruit[]) => {
        return (
            <div className="space-y-12">
                <AnimatePresence mode="wait">
                    {viewMode === 'grid' ? (
                        <motion.div
                            key={`grid-${currentPage}-${activeTab}`}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.3 }}
                            className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
                        >
                            {items.map((recruit, index) => (
                                <motion.div
                                    key={recruit.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                >
                                    <Link href={`/recruit/${recruit.id}`} className="block h-full group">
                                        <Card className="flex flex-col h-full hover:shadow-xl transition-all duration-500 ease-in-out hover:-translate-y-1.5 cursor-pointer border-slate-200 bg-white rounded-2xl overflow-hidden ring-4 ring-transparent hover:ring-blue-500/5 shadow-sm">
                                            <CardHeader className="pb-4">
                                                <div className="flex justify-between items-start mb-2">
                                                    <Badge variant="outline" className="bg-slate-50 text-slate-400 border-slate-100 text-[10px] font-black uppercase tracking-widest px-2 py-0.5">
                                                        JOB OPENING
                                                    </Badge>
                                                </div>
                                                <CardTitle className="line-clamp-1 text-xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors duration-300 mb-1">{recruit.title}</CardTitle>
                                                <CardDescription className="text-sm font-bold text-slate-500 flex items-center gap-1.5 antialiased">
                                                    <Building className="h-3.5 w-3.5 opacity-50" /> {recruit.company}
                                                </CardDescription>
                                            </CardHeader>
                                            <CardContent className="flex-1 pb-6">
                                                <div className="flex flex-wrap gap-2">
                                                    {recruit.tags.map((tag) => (
                                                        <Badge key={tag} variant="secondary" className="font-bold bg-slate-100/80 text-slate-600 border-none px-2.5 py-0.5 text-[11px]">
                                                            {tag}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </CardContent>
                                            <CardFooter className="border-t border-slate-50 pt-5 pb-5 px-6 text-[11px] font-black text-slate-400 flex justify-between items-center bg-slate-50/30 group-hover:bg-blue-50/30 transition-colors duration-300 rounded-b-xl uppercase tracking-wider">
                                                <div className="flex items-center gap-2">
                                                    <Calendar className="h-3.5 w-3.5 opacity-40 text-blue-500" />
                                                    <span>마감일: {recruit.deadline}</span>
                                                </div>
                                                <div className="flex items-center gap-1 text-blue-600 font-black group-hover:translate-x-1.5 transition-all duration-500 ease-in-out">
                                                    APPLY <ArrowRight className="h-3.5 w-3.5" />
                                                </div>
                                            </CardFooter>
                                        </Card>
                                    </Link>
                                </motion.div>
                            ))}
                        </motion.div>
                    ) : (
                        <motion.div
                            key={`list-${currentPage}-${activeTab}`}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            transition={{ duration: 0.3 }}
                            className="space-y-4 p-0"
                        >
                            {items.map((recruit, index) => (
                                <motion.div
                                    key={recruit.id}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                >
                                    <Link href={`/recruit/${recruit.id}`} className="block group">
                                        <div className="flex flex-col md:flex-row md:items-center justify-between p-5 rounded-xl border border-slate-100 bg-white transition-all duration-500 ease-in-out group-hover:border-blue-200 group-hover:bg-slate-50/50 group-hover:translate-x-1.5 hover:shadow-md">
                                            <div className="flex flex-col md:flex-row md:items-center gap-6 flex-1 min-w-0 pr-4">
                                                <div className="h-14 w-14 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-white group-hover:border-blue-100 group-hover:text-blue-600 transition-[background-color,border-color,color] duration-300 shrink-0">
                                                    <Building className="h-6 w-6" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-3 mb-1.5">
                                                        <h3 className="text-lg font-bold text-slate-900 group-hover:text-blue-700 transition-colors duration-300 truncate">
                                                            {recruit.title}
                                                        </h3>
                                                        <span className="text-xs font-black text-slate-300 uppercase tracking-widest hidden sm:block">|</span>
                                                        <span className="text-sm font-bold text-slate-500">{recruit.company}</span>
                                                    </div>
                                                    <div className="flex flex-wrap gap-2">
                                                        {recruit.tags.map((tag) => (
                                                            <span key={tag} className="text-[10px] font-bold text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-100 group-hover:bg-white group-hover:border-blue-100 group-hover:text-blue-500 transition-colors duration-300">
                                                                #{tag}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center justify-between md:justify-end gap-8 mt-4 md:mt-0 shrink-0 border-t md:border-t-0 pt-4 md:pt-0">
                                                <div className="text-[11px] font-black text-slate-300 uppercase tracking-widest flex items-center gap-2">
                                                    <Calendar className="h-3.5 w-3.5 opacity-40" />
                                                    마감: {recruit.deadline}
                                                </div>
                                                <Button size="sm" variant="outline" className="rounded-lg h-9 font-black text-[11px] border-slate-200 hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all duration-500 ease-in-out uppercase tracking-widest flex items-center justify-center gap-2">
                                                    View Detail
                                                </Button>
                                            </div>
                                        </div>
                                    </Link>
                                </motion.div>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Smart Pagination UI */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-2 pt-8">
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={currentPage === 1}
                            onClick={() => { setCurrentPage(prev => Math.max(1, prev - 1)); window.scrollTo({ top: 400, behavior: 'smooth' }); }}
                            className="rounded-xl h-10 px-4 border-slate-200 font-bold hover:bg-blue-50 hover:text-blue-600 transition-all shrink-0"
                        >
                            이전
                        </Button>
                        <div className="flex items-center gap-1 mx-2">
                            {(() => {
                                const pages = [];
                                const delta = 1; // Number of pages to show around current page

                                for (let i = 1; i <= totalPages; i++) {
                                    if (
                                        i === 1 ||
                                        i === totalPages ||
                                        (i >= currentPage - delta && i <= currentPage + delta)
                                    ) {
                                        pages.push(i);
                                    } else if (
                                        i === currentPage - delta - 1 ||
                                        i === currentPage + delta + 1
                                    ) {
                                        pages.push('...');
                                    }
                                }

                                return pages.map((page, index) => {
                                    if (page === '...') {
                                        return (
                                            <div key={`ellipsis-${index}`} className="flex items-center justify-center w-10 h-10 text-slate-300">
                                                <MoreHorizontal className="h-4 w-4" />
                                            </div>
                                        );
                                    }

                                    const pageNum = page as number;
                                    return (
                                        <Button
                                            key={pageNum}
                                            variant={currentPage === pageNum ? "default" : "ghost"}
                                            size="sm"
                                            onClick={() => { setCurrentPage(pageNum); window.scrollTo({ top: 400, behavior: 'smooth' }); }}
                                            className={cn(
                                                "h-10 w-10 p-0 rounded-xl font-bold transition-all",
                                                currentPage === pageNum ? "bg-blue-600 text-white shadow-md shadow-blue-500/20" : "text-slate-500 hover:bg-slate-100"
                                            )}
                                        >
                                            {pageNum}
                                        </Button>
                                    );
                                });
                            })()}
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={currentPage === totalPages}
                            onClick={() => { setCurrentPage(prev => Math.min(totalPages, prev + 1)); window.scrollTo({ top: 400, behavior: 'smooth' }); }}
                            className="rounded-xl h-10 px-4 border-slate-200 font-bold hover:bg-blue-50 hover:text-blue-600 transition-all shrink-0"
                        >
                            다음
                        </Button>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="container max-w-screen-xl mx-auto py-12 px-4 md:px-8 animate-in fade-in duration-500">
            {/* 히어로 섹션 + 통합 검색 */}
            <div className="mb-16 text-center space-y-8">
                <div className="space-y-4">
                    <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
                        당신의 커리어를 <span className="text-blue-600 drop-shadow-sm">Boost</span>하세요
                    </h1>
                    <p className="text-lg text-slate-500 max-w-2xl mx-auto leading-relaxed font-medium">
                        Pro-NLP는 당신의 포트폴리오를 분석하여 가장 적합한 기업을 추천하고,<br />
                        자소서 초안까지 작성해주는 최첨단 채용 서비스입니다.
                    </p>
                </div>

                <div className="max-w-2xl mx-auto relative group">
                    <div className="absolute inset-0 bg-blue-500/5 blur-2xl rounded-full -z-10 group-focus-within:bg-blue-500/10 transition-colors"></div>
                    <Search className="absolute left-6 top-1/2 -translate-y-1/2 h-6 w-6 text-slate-400 group-focus-within:text-blue-600 transition-colors" />
                    <Input
                        placeholder="찾으시는 회사나 직무, 기술 스택을 검색해보세요"
                        className="pl-16 h-16 rounded-3xl border-slate-200 focus-visible:ring-blue-500 bg-white shadow-xl shadow-slate-200/50 hover:shadow-2xl hover:shadow-slate-200/60 transition-all text-lg font-medium"
                        value={searchQuery}
                        onChange={(e) => {
                            setSearchQuery(e.target.value);
                            setCurrentPage(1);
                        }}
                    />
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery("")}
                            className="absolute right-6 top-1/2 -translate-y-1/2 text-[11px] font-black text-slate-300 hover:text-slate-600 uppercase tracking-widest bg-slate-50 px-3 py-1.5 rounded-full"
                        >
                            CLEAR
                        </button>
                    )}
                </div>
            </div>

            {/* 메인 콘텐츠 섹션 */}
            <div className="w-full max-w-6xl mx-auto px-4">
                <Tabs defaultValue="all" className="w-full" onValueChange={(value) => { setActiveTab(value); setCurrentPage(1); }}>
                    {/* 상단 탭 + 뷰 모드 설정 */}
                    <div className="flex flex-col md:flex-row items-center justify-between mb-8 gap-6 border-b border-slate-100 pb-2">
                        <TabsList className="grid h-10 w-full max-w-[400px] grid-cols-3 bg-slate-100 p-1 rounded-xl border border-slate-200/50 shadow-inner">
                            <TabsTrigger value="all" className="rounded-lg font-bold py-1.5 text-[13px] data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all duration-200">전체 공고</TabsTrigger>
                            <TabsTrigger value="recommend" className="flex items-center gap-1.5 rounded-lg font-bold py-1.5 text-[13px] data-[state=active]:bg-white data-[state=active]:text-blue-600 data-[state=active]:shadow-sm transition-all duration-200">
                                <Sparkles className="h-3.5 w-3.5 text-blue-500 fill-blue-500/10" /> 맞춤 추천
                            </TabsTrigger>
                            <TabsTrigger value="popular" className="flex items-center gap-1.5 rounded-lg font-bold py-1.5 text-[13px] data-[state=active]:bg-white data-[state=active]:text-orange-600 data-[state=active]:shadow-sm transition-all duration-200">
                                <Flame className="h-3.5 w-3.5 text-orange-500 fill-orange-500/10" /> 인기 순
                            </TabsTrigger>
                        </TabsList>

                        <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200/50 shadow-inner">
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
                    </div>

                    {/* 카테고리 & 기술 필터 바 (Tabs 바로 아래 위치) */}
                    <div className="space-y-6 mb-12 animate-in slide-in-from-top-4 fade-in duration-700">
                        <div className="flex flex-wrap gap-2.5 items-center justify-start">
                            <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest mr-2 border-r border-slate-200 pr-4">직무</span>
                            {JOB_CATEGORIES.map((cat) => (
                                <Button
                                    key={cat.value}
                                    variant={selectedCategory === cat.value ? "default" : "outline"}
                                    onClick={() => {
                                        setSelectedCategory(cat.value);
                                        setCurrentPage(1);
                                    }}
                                    className={cn(
                                        "rounded-full h-10 px-5 font-bold transition-all duration-300 transform",
                                        selectedCategory === cat.value
                                            ? "bg-slate-900 border-slate-900 text-white shadow-xl scale-105"
                                            : "bg-white border-slate-200 text-slate-500 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50/20"
                                    )}
                                >
                                    {cat.label}
                                </Button>
                            ))}
                        </div>

                        <div className="flex flex-wrap gap-2.5 items-center justify-start">
                            <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest mr-2 border-r border-slate-200 pr-4">기술</span>
                            {TECH_STACKS.map((tech) => (
                                <Badge
                                    key={tech}
                                    variant={selectedTechs.includes(tech) ? "default" : "outline"}
                                    onClick={() => toggleTech(tech)}
                                    className={cn(
                                        "cursor-pointer px-4 py-2 rounded-xl font-bold transition-all duration-300 border-2 select-none",
                                        selectedTechs.includes(tech)
                                            ? "bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/20"
                                            : "bg-white text-slate-400 border-slate-100 hover:border-slate-300 hover:text-slate-600"
                                    )}
                                >
                                    {tech}
                                </Badge>
                            ))}
                        </div>
                    </div>

                    {loading ? (
                        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
                            {[1, 2, 3, 4, 5, 6].map((i) => (
                                <div key={i} className="h-[280px] w-full animate-pulse rounded-3xl bg-slate-100/80 border border-slate-200/50" />
                            ))}
                        </div>
                    ) : (
                        <div className="mt-4">
                            <TabsContent value="all" className="mt-0 outline-none">
                                {renderRecruitList(recruits)}
                            </TabsContent>
                            <TabsContent value="recommend" className="mt-0 outline-none">
                                {isAuthenticated ? (
                                    recruits.length > 0 ? (
                                        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-700">
                                            <div className="flex items-start gap-4 p-6 bg-gradient-to-r from-blue-500/5 to-transparent border border-blue-500/10 rounded-3xl text-blue-800 shadow-sm antialiased font-semibold">
                                                <div className="p-3 bg-white rounded-2xl shadow-sm">
                                                    <Sparkles className="h-5 w-5 text-blue-600 fill-blue-500" />
                                                </div>
                                                <div className="space-y-1">
                                                    <p className="font-bold text-base">맞춤형 인텔리전스 추천</p>
                                                    <p className="text-[13px] text-blue-600/70 font-medium leading-relaxed">회원님의 포트폴리오를 기반으로 AI가 분석한 추천 공고입니다. 현재 기술 스택 매칭률이 높은 순서대로 정렬되었습니다.</p>
                                                </div>
                                            </div>
                                            {renderRecruitList(recruits)}
                                        </div>
                                    ) : (
                                        <div className="text-center py-32 bg-slate-50/50 rounded-3xl border-2 border-dashed border-slate-200 text-slate-400 font-bold italic">
                                            조건에 맞는 추천 공고가 없습니다.
                                        </div>
                                    )
                                ) : (
                                    <div className="text-center py-24 px-12 border-2 border-dashed border-slate-200 rounded-[40px] animate-in fade-in slide-in-from-bottom-8 duration-700 bg-white shadow-2xl shadow-slate-100">
                                        <div className="w-20 h-20 bg-blue-50 rounded-3xl flex items-center justify-center mx-auto mb-8">
                                            <Sparkles className="h-10 w-10 text-blue-500 fill-blue-500/20" />
                                        </div>
                                        <h3 className="text-3xl font-black text-slate-900 mb-4">로그인이 필요합니다</h3>
                                        <p className="text-slate-500 font-medium mb-10 max-w-sm mx-auto leading-relaxed">내 포트폴리오를 등록하면 AI가 1,000만 개 이상의 데이터셋을 분석하여 딱 맞는 공고를 추천해 드려요!</p>
                                        <Link href="/login">
                                            <Button className="h-14 px-12 rounded-2xl font-bold text-lg shadow-xl shadow-blue-500/20 hover:scale-105 transition-all">
                                                지금 바로 로그인하기
                                            </Button>
                                        </Link>
                                    </div>
                                )}
                            </TabsContent>
                            <TabsContent value="popular" className="mt-0 outline-none">
                                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-700">
                                    <div className="flex items-start gap-4 p-6 bg-gradient-to-r from-orange-500/5 to-transparent border border-orange-500/10 rounded-3xl text-orange-800 shadow-sm antialiased font-semibold">
                                        <div className="p-3 bg-white rounded-2xl shadow-sm">
                                            <Flame className="h-5 w-5 text-orange-600 fill-orange-500" />
                                        </div>
                                        <div className="space-y-1">
                                            <p className="font-bold text-base">트렌딩 핫 공고</p>
                                            <p className="text-[13px] text-orange-600/70 font-medium">실시간 지원율과 조회수가 급상승 중인 가장 핫한 직무들입니다.</p>
                                        </div>
                                    </div>
                                    {renderRecruitList(recruits)}
                                </div>
                            </TabsContent>
                        </div>
                    )}
                </Tabs>
            </div>
        </div>
    );
}
