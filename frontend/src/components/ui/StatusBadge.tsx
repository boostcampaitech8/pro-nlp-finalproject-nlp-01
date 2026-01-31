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

    // Base styles for the tag variant (tilted, floating)
    // Positioned at top-right, tilted opposite way (reversed angle), and increased shadow/offset
    const cardTagStyles = isCardTag ? "absolute -top-1 -right-2 rotate-6 z-10 px-4 py-1.5 shadow-2xl scale-110 rounded-lg whitespace-nowrap border-white/20 backdrop-blur-sm" : "";

    // Default variant can also look premium with a subtle glow
    const defaultStyles = !isCardTag ? "bg-white/80 backdrop-blur-xs border-slate-200/60 shadow-xs" : "";

    if (normalizedStatus === 'PENDING' || normalizedStatus === 'PROCESSING') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-amber-50/80 border-amber-200/60 text-amber-700 text-[10px] gap-1.5 font-bold animate-pulse py-1 transition-all duration-300 shadow-sm shadow-amber-100/50",
                    isCardTag ? cardTagStyles : defaultStyles,
                    className
                )}
            >
                {showIcon && <Loader2 className="h-3 w-3 animate-spin text-amber-500" />}
                {normalizedStatus === 'PENDING' ? 'PENDING...' : 'ANALYZING...'}
            </Badge>
        );
    }

    if (normalizedStatus === 'REVIEW_REQUIRED') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-orange-500 border-orange-400 text-white text-[10px] gap-1.5 font-bold py-1 shadow-lg shadow-orange-200/50 ring-2 ring-white/20",
                    isCardTag ? cardTagStyles : cn(defaultStyles, "bg-orange-500 border-orange-500 text-white"),
                    className
                )}
            >
                {showIcon && <Sparkles className="h-3 w-3 fill-white text-white animate-pulse" />}
                검토 필요
            </Badge>
        );
    }

    if (normalizedStatus === 'COMPLETED') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-emerald-500 border-emerald-400 text-white text-[10px] gap-1.5 font-bold py-1 shadow-xl shadow-emerald-200/50 ring-2 ring-white/20",
                    isCardTag ? cardTagStyles : cn(defaultStyles, "bg-emerald-500 border-emerald-500 text-white"),
                    className
                )}
            >
                {showIcon && <CheckCircle2 className="h-3 w-3" />}
                최종 확정
            </Badge>
        );
    }

    if (normalizedStatus === 'FAILED') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-rose-500 border-rose-400 text-white text-[10px] gap-1.5 font-bold py-1 shadow-lg shadow-rose-200/50",
                    isCardTag ? cardTagStyles : cn(defaultStyles, "bg-rose-500 border-rose-500 text-white"),
                    className
                )}
            >
                {showIcon && <AlertCircle className="h-3 w-3" />}
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
