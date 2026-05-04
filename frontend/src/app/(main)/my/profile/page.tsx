"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/useAuthStore";
import { getApiUrl, fetchWithAuth } from "@/lib/apiUtils";
import { User } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Target, Sparkles, User as UserIcon, Github, Settings as NotionIcon, Unlink, CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";
import { integrationApi, UserIntegration } from "@/lib/integrationApi";
import { cn } from "@/lib/utils";

export default function ProfilePage() {
    const { isAuthenticated } = useAuthStore();
    const [profile, setProfile] = useState<User | null>(null);
    const [integrations, setIntegrations] = useState<UserIntegration[]>([]);
    const [loading, setLoading] = useState(true);
    const [isDisconnecting, setIsDisconnecting] = useState<number | null>(null);

    useEffect(() => {
        if (!isAuthenticated) return;

        const loadData = async () => {
            try {
                const [profRes, intRes] = await Promise.all([
                    fetchWithAuth(getApiUrl("/auth/me")),
                    integrationApi.fetchIntegrations()
                ]);

                if (profRes.ok) {
                    const profData = await profRes.json();
                    setProfile(profData);
                }
                setIntegrations(intRes);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [isAuthenticated]);

    const handleDisconnect = async (id: number) => {
        if (!confirm("정말 연동을 해제하시겠습니까? 관련 데이터 동기화가 중단됩니다.")) return;

        setIsDisconnecting(id);
        try {
            const success = await integrationApi.removeIntegration(id);
            if (success) {
                setIntegrations(prev => prev.filter(i => i.id !== id));
            }
        } catch (err) {
            console.error("Failed to disconnect", err);
        } finally {
            setIsDisconnecting(null);
        }
    };

    if (loading) return <div className="flex h-[calc(100vh-64px)] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;
    if (!profile) return <div className="text-center py-20 font-bold text-slate-500">로그인이 필요합니다.</div>;

    return (
        <div className="container max-w-screen-md mx-auto py-12 px-4 md:px-8 space-y-10 animate-in fade-in duration-700">
            {/* User Intro Section (Premium Header) */}
            <div className="relative overflow-hidden rounded-[3.5rem] bg-slate-900 p-12 md:p-16 text-center shadow-3xl">
                <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 bg-blue-600/20 rounded-full blur-[100px]" />
                <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-80 h-80 bg-indigo-600/20 rounded-full blur-[100px]" />

                <div className="relative space-y-8">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="inline-flex p-1.5 pr-6 rounded-full bg-white/5 backdrop-blur-2xl border border-white/10 items-center gap-4 text-white/70 text-sm font-semibold"
                    >
                        <div className="p-2.5 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/30">
                            <UserIcon className="h-4 w-4 text-white" />
                        </div>
                        {profile.email}
                    </motion.div>

                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-5xl md:text-6xl font-black text-white tracking-tighter"
                    >
                        {profile.name}<span className="text-blue-500">.</span>
                    </motion.h1>

                    {profile.desired_job_title ? (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                            className="flex justify-center"
                        >
                            <div className="px-8 py-3 rounded-2xl bg-white/10 backdrop-blur-md border border-white/5 text-blue-400 font-black text-base shadow-2xl flex items-center gap-3">
                                <Target className="h-5 w-5" />
                                {profile.desired_job_title}
                            </div>
                        </motion.div>
                    ) : (
                        <div className="flex justify-center">
                            <div className="px-8 py-3 rounded-2xl border border-white/5 bg-white/5 text-slate-500 font-bold text-sm tracking-wide">
                                분석가 가동 중...
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Profile Content Cards */}
            <div className="grid gap-8">
                {/* AI Career Summary */}
                <Card className="border-0 rounded-[3rem] shadow-2xl shadow-blue-500/5 overflow-hidden bg-white/70 backdrop-blur-xl border border-white/20">
                    <CardHeader className="bg-gradient-to-r from-blue-50/50 to-indigo-50/50 p-10 pb-6">
                        <CardTitle className="flex items-center gap-4 text-2xl font-black text-slate-900 tracking-tight">
                            <div className="p-3 bg-white rounded-2xl shadow-md border border-blue-100 text-blue-600">
                                <Sparkles className="h-6 w-6 fill-blue-50" />
                            </div>
                            나의 커리어 DNA
                        </CardTitle>
                        <CardDescription className="text-slate-500 text-base font-medium">AI가 분석한 당신만의 핵심 전문성과 가치입니다.</CardDescription>
                    </CardHeader>
                    <CardContent className="p-10 pt-6">
                        {profile.profile_summary ? (
                            <p className="text-xl text-slate-700 leading-[2.2] whitespace-pre-line font-semibold antialiased">
                                {profile.profile_summary}
                            </p>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-20 space-y-6">
                                <div className="w-20 h-20 bg-slate-50 rounded-[2rem] flex items-center justify-center animate-pulse border border-slate-100">
                                    <Sparkles className="h-10 w-10 text-slate-200" />
                                </div>
                                <div className="text-center space-y-2">
                                    <p className="text-slate-400 font-bold text-lg">
                                        포트폴리오를 등록하면 AI가 커리어를 분석해 드립니다.
                                    </p>
                                    <p className="text-slate-300 text-sm font-medium">당신의 강점과 성과를 한눈에 정리해 보세요.</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Integration Management */}
                <Card className="border-0 rounded-[3rem] shadow-2xl shadow-slate-200/5 overflow-hidden bg-white">
                    <CardHeader className="p-10 pb-4">
                        <CardTitle className="flex items-center gap-4 text-2xl font-black text-slate-900 tracking-tight">
                            <div className="p-3 bg-slate-50 rounded-2xl text-slate-900 border border-slate-100">
                                <NotionIcon className="h-6 w-6" />
                            </div>
                            디지털 리액션
                        </CardTitle>
                        <CardDescription className="text-slate-500 text-base font-medium">외부 커리어 플랫폼 연동 현황입니다.</CardDescription>
                    </CardHeader>
                    <CardContent className="p-10 space-y-4">
                        {[
                            { id: 'github', name: 'GitHub', icon: <Github className="h-5 w-5" />, color: 'bg-slate-900' },
                            { id: 'notion', name: 'Notion', icon: <NotionIcon className="h-5 w-5" />, color: 'bg-slate-100 text-slate-900' }
                        ].map(provider => {
                            const integration = integrations.find(i => i.provider === provider.id);
                            return (
                                <div key={provider.id} className="flex items-center justify-between p-5 rounded-3xl border border-slate-100 bg-slate-50/30 transition-all hover:bg-slate-50">
                                    <div className="flex items-center gap-4">
                                        <div className={cn("p-3 rounded-2xl flex items-center justify-center text-white shadow-sm", provider.color)}>
                                            {provider.icon}
                                        </div>
                                        <div>
                                            <div className="font-bold text-slate-800">{provider.name}</div>
                                            <div className="flex items-center gap-1.5 mt-0.5">
                                                {integration ? (
                                                    <span className="text-[10px] font-bold text-emerald-500 flex items-center gap-1">
                                                        <CheckCircle2 className="h-3 w-3" /> 연동됨
                                                    </span>
                                                ) : (
                                                    <span className="text-[10px] font-bold text-slate-300">연동되지 않음</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {integration ? (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleDisconnect(integration.id)}
                                            disabled={isDisconnecting === integration.id}
                                            className="text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl font-bold gap-2 h-9"
                                        >
                                            {isDisconnecting === integration.id ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <Unlink className="h-4 w-4" />
                                            )}
                                            연동 해제
                                        </Button>
                                    ) : (
                                        <Badge variant="outline" className="border-slate-100 bg-white text-slate-300 font-bold text-[10px] px-3 h-7">
                                            미연동
                                        </Badge>
                                    )}
                                </div>
                            );
                        })}
                    </CardContent>
                </Card>
            </div>

            <p className="text-center text-xs text-slate-400 leading-relaxed font-medium pb-10">
                이 정보는 등록하신 포트폴리오를 AI가 종합적으로 분석한 결과입니다.<br />
                포트폴리오가 추가되거나 변경되면 실시간으로 업데이트됩니다.
            </p>
        </div>
    );
}
