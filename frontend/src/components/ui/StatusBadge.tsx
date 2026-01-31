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
    const cardTagStyles = isCardTag ? "absolute -top-1.5 -right-3 rotate-6 z-10 px-4 py-1.5 shadow-xl scale-110 rounded-lg whitespace-nowrap" : "";

    if (normalizedStatus === 'PENDING' || normalizedStatus === 'PROCESSING') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-yellow-50 border-yellow-200 text-yellow-700 text-[10px] gap-1.5 font-black animate-pulse py-0.5 transition-all duration-300",
                    cardTagStyles,
                    className
                )}
            >
                {showIcon && <Loader2 className="h-3 w-3 animate-spin" />}
                {normalizedStatus === 'PENDING' ? 'PENDING...' : 'ANALYZING...'}
            </Badge>
        );
    }

    if (normalizedStatus === 'REVIEW_REQUIRED') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-amber-500 border-amber-600 text-white text-[10px] gap-1.5 font-black py-0.5 shadow-sm shadow-amber-200 animate-bounce",
                    cardTagStyles,
                    className
                )}
            >
                {showIcon && <Sparkles className="h-3 w-3 fill-white" />}
                검토 필요
            </Badge>
        );
    }

    if (normalizedStatus === 'COMPLETED') {
        return (
            <Badge
                variant="outline"
                className={cn(
                    "bg-emerald-500 border-emerald-600 text-white text-[10px] gap-1.5 font-black py-0.5 shadow-lg shadow-emerald-200",
                    cardTagStyles,
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
                    "bg-red-500 border-red-600 text-white text-[10px] gap-1.5 font-black py-0.5",
                    cardTagStyles,
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
        <Badge variant="outline" className={cn("text-[10px] font-bold py-0.5", cardTagStyles, className)}>
            {status}
        </Badge>
    );
}
