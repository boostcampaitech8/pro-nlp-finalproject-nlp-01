import type { Metadata } from "next";
import { Noto_Sans_KR as FontSans } from "next/font/google";
import { cn } from "@/lib/utils";
import "./globals.css";
import { MSWComponent } from "@/components/MSWComponent";
import { ToastProvider } from "@/components/ui/toast-context";
import { ThemeProvider } from "@/components/theme-provider";
import { MockingHandler } from "@/components/MockingHandler";
import { Suspense } from "react";

const fontSans = FontSans({
    subsets: ["latin"],
    weight: ["300", "400", "500", "700", "900"],
    variable: "--font-sans",
});

export const metadata: Metadata = {
    title: "모두취업",
    description: "AI-powered job application manager",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="ko" suppressHydrationWarning>
            <body className={cn(
                "min-h-screen bg-background font-sans antialiased flex flex-col",
                fontSans.variable
            )}>
                <MSWComponent>
                    <ThemeProvider
                        attribute="class"
                        defaultTheme="system"
                        enableSystem
                        disableTransitionOnChange
                    >
                        <ToastProvider>
                            <Suspense fallback={null}>
                                <MockingHandler>
                                    {children}
                                </MockingHandler>
                            </Suspense>
                        </ToastProvider>
                    </ThemeProvider>
                </MSWComponent>
            </body>
        </html>
    );
}
