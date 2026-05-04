"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Sparkles, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export type ProcessingStatus = 'PENDING' | 'PROCESSING' | 'REVIEW_REQUIRED' | 'COMPLETED' | 'FAILED';

interface StatusBadgeProps {
    status: ProcessingStatus | string; // Accept string for flexibility with API responses
    className?: string;
    showIcon?: boolean;
    variant?: 'default' | 'card-tag' | 'detail' | 'ribbon';
}

export function StatusBadge({ status, className, showIcon = true, variant = 'default' }: StatusBadgeProps) {
    const normalizedStatus = (status || 'PENDING').toUpperCase();

    const isCardTag = variant === 'card-tag';
    const isDetail = variant === 'detail';

    // Base styles for the tag variant (Modern Badge Style)
    // Shared visuals for both card-tag and detail variants
    const modernBadgeVisuals = "px-3 py-1 shadow-md rounded-lg whitespace-nowrap border border-slate-100 ring-1 ring-slate-200/50 backdrop-blur-md transition-all duration-300";

    // Positioning specific to card-tag
    const absolutePositioning = "absolute top-4 right-4 z-10";

    // Ribbon style for diagonal display
    const ribbonVisuals = "absolute top-2 -right-3 rotate-[20deg] shadow-sm z-20 px-3 py-0.5 text-[9px] font-black tracking-wider uppercase border-none rounded-sm transform hover:scale-105 hover:rotate-12 transition-all duration-300";

    const cardTagStyles = isCardTag
        ? `${absolutePositioning} ${modernBadgeVisuals}`
        : (isDetail ? modernBadgeVisuals : (variant === 'ribbon' ? ribbonVisuals : ""));

    const defaultStyles = (!isCardTag && !isDetail && variant !== 'ribbon') ? "bg-white/80 backdrop-blur-xs border-slate-200/60 shadow-xs" : "";

    if (normalizedStatus === 'PENDING') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-slate-100 border-slate-200 text-slate-500 text-[10px] gap-1.5 font-bold py-1",
                    isCardTag ? cardTagStyles : (variant === 'ribbon' ? ribbonVisuals + " bg-slate-500 text-white shadow-slate-500/20" : "bg-slate-50/80 border-slate-200/60 text-slate-500 shadow-sm shadow-slate-100/50"),
                    className
                )}
            >
                {showIcon && <Loader2 className="h-3 w-3" />}
                분석 대기
            </Badge>
        );
    }

    if (normalizedStatus === 'PROCESSING') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-amber-500 border-amber-400 text-white text-[10px] gap-1.5 font-bold animate-pulse py-1",
                    isCardTag ? cardTagStyles : (variant === 'ribbon' ? ribbonVisuals + " bg-amber-500 text-white shadow-amber-500/20" : "bg-amber-50/80 border-amber-200/60 text-amber-700 shadow-sm shadow-amber-100/50"),
                    className
                )}
            >
                {showIcon && <Loader2 className="h-3 w-3 animate-spin" />}
                분석 중...
            </Badge>
        );
    }

    if (normalizedStatus === 'REVIEW_REQUIRED') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-gradient-to-r from-orange-500 to-amber-500 border-orange-400 text-white text-[10px] gap-1.5 font-bold py-1",
                    isCardTag ? cardTagStyles : (variant === 'ribbon' ? ribbonVisuals + " bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-orange-500/20" : "bg-orange-500 border-orange-500 text-white shadow-lg shadow-orange-200/50"),
                    className
                )}
            >
                {showIcon && <Sparkles className="h-3.5 w-3.5 fill-white text-white" />}
                검토 필요
            </Badge>
        );
    }

    if (normalizedStatus === 'COMPLETED') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-gradient-to-r from-blue-600 to-indigo-600 border-blue-400 text-white text-[10px] gap-1.5 font-bold py-1",
                    isCardTag ? cardTagStyles : (variant === 'ribbon' ? ribbonVisuals + " bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-blue-500/20" : "bg-blue-600 border-blue-500 text-white shadow-xl shadow-blue-200/50"),
                    className
                )}
            >
                {showIcon && <CheckCircle2 className="h-3.5 w-3.5" />}
                최종 확정
            </Badge>
        );
    }

    if (normalizedStatus === 'FAILED') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-rose-500 border-rose-400 text-white text-[10px] gap-1.5 font-bold py-1",
                    isCardTag ? cardTagStyles : (variant === 'ribbon' ? ribbonVisuals + " bg-rose-500 text-white shadow-rose-500/20" : "bg-rose-500 border-rose-500 text-white shadow-lg shadow-rose-200/50"),
                    className
                )}
            >
                {showIcon && <AlertCircle className="h-3.5 w-3.5" />}
                분석 실패
            </Badge>
        );
    }

    // Default Fallback
    return (
        <Badge variant="outline" className={cn("text-[10px] font-bold py-1", isCardTag ? cardTagStyles : (variant === 'ribbon' ? ribbonVisuals + " bg-slate-500 text-white" : defaultStyles), className)}>
            {status}
        </Badge>
    );
}
