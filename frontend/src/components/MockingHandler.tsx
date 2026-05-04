"use client";

import { useEffect } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { isMockMode } from "@/lib/apiUtils";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/react";

export function MockingHandler({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const isMock = isMockMode();

    useEffect(() => {
        if (!isMock) return;

        // Handle SPA routing from 404.html redirect
        const p = searchParams.get('p');
        if (p) {
            // Remove the 'p' param and redirect to the actual path
            const newParams = new URLSearchParams(searchParams.toString());
            newParams.delete('p');
            const queryString = newParams.toString();
            const target = p + (queryString ? `?${queryString}` : '');
            router.replace(target);
        }
    }, [isMock, searchParams, router]);

    return (
        <>
            {children}
            {!isMock && (
                <>
                    <Analytics />
                    <SpeedInsights />
                </>
            )}
        </>
    );
}
