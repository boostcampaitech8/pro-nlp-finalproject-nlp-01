"use client";

import React from "react";
import { Info } from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface InfoTooltipProps {
    message: string | React.ReactNode;
    className?: string;
    iconClassName?: string;
}

export function InfoTooltip({ message, className, iconClassName }: InfoTooltipProps) {
    return (
        <TooltipProvider delayDuration={300}>
            <Tooltip>
                <TooltipTrigger asChild>
                    <button
                        type="button"
                        className={cn("inline-flex items-center text-slate-400 hover:text-blue-500 transition-colors focus:outline-none", className)}
                    >
                        <Info className={cn("h-4 w-4", iconClassName)} />
                    </button>
                </TooltipTrigger>
                <TooltipContent
                    side="top"
                    className="max-w-[250px] bg-slate-900 text-white text-xs p-3 rounded-lg shadow-xl border-none"
                >
                    <p className="leading-relaxed">{message}</p>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}
