"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Sparkles, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export type ProcessingStatus = 'PENDING' | 'PROCESSING' | 'REVIEW_REQUIRED' | 'COMPLETED' | 'FAILED';

interface StatusBadgeProps {
    status: ProcessingStatus | string; // Accept string for flexibility with API responses
    className?: string;
    showIcon?: boolean;
    variant?: 'default' | 'card-tag';
}

export function StatusBadge({ status, className, showIcon = true, variant = 'default' }: StatusBadgeProps) {
    const normalizedStatus = (status || 'PENDING').toUpperCase();

    const isCardTag = variant === 'card-tag';

    // Base styles for the tag variant (Modern Badge Style)
    // Positioned inside the card at top-right for a cleaner look
    const cardTagStyles = isCardTag ? "absolute top-5 right-5 z-10 px-3 py-1 shadow-md rounded-lg whitespace-nowrap border border-slate-100 ring-1 ring-slate-200/50 backdrop-blur-md transition-all duration-300" : "";

    const defaultStyles = !isCardTag ? "bg-white/80 backdrop-blur-xs border-slate-200/60 shadow-xs" : "";

    if (normalizedStatus === 'PENDING' || normalizedStatus === 'PROCESSING') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-amber-500 border-amber-400 text-white text-[10px] gap-1.5 font-bold animate-pulse py-1",
                    isCardTag ? cardTagStyles : "bg-amber-50/80 border-amber-200/60 text-amber-700 shadow-sm shadow-amber-100/50",
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
                    isCardTag ? cardTagStyles : "bg-orange-500 border-orange-500 text-white shadow-lg shadow-orange-200/50",
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
                    isCardTag ? cardTagStyles : "bg-emerald-500 border-emerald-500 text-white shadow-xl shadow-emerald-200/50",
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
                    isCardTag ? cardTagStyles : "bg-rose-500 border-rose-500 text-white shadow-lg shadow-rose-200/50",
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
        <Badge variant="outline" className={cn("text-[10px] font-bold py-1", isCardTag ? cardTagStyles : defaultStyles, className)}>
            {status}
        </Badge>
    );
}
