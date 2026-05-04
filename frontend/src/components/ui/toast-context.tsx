"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
    id: string;
    message: string;
    type: ToastType;
}

interface ToastContextType {
    toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error("useToast must be used within a ToastProvider");
    }
    return context;
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const toast = useCallback((message: string, type: ToastType = "info") => {
        const id = Math.random().toString(36).substr(2, 9);
        setToasts((prev) => [...prev, { id, message, type }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 3000);
    }, []);

    const removeToast = (id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    return (
        <ToastContext.Provider value={{ toast }}>
            {children}
            <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
                <AnimatePresence>
                    {toasts.map((t) => (
                        <motion.div
                            key={t.id}
                            initial={{ opacity: 0, y: 20, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, x: 20, transition: { duration: 0.2 } }}
                            className={cn(
                                "pointer-events-auto flex items-center gap-3 px-5 py-4 rounded-2xl shadow-2xl border min-w-[320px] max-w-md",
                                t.type === "success" && "bg-emerald-50 border-emerald-100 text-emerald-900",
                                t.type === "error" && "bg-red-50 border-red-100 text-red-900",
                                t.type === "info" && "bg-blue-50 border-blue-100 text-blue-900",
                                t.type === "warning" && "bg-amber-50 border-amber-100 text-amber-900"
                            )}
                        >
                            {t.type === "success" && <CheckCircle className="h-5 w-5 text-emerald-500" />}
                            {t.type === "error" && <AlertCircle className="h-5 w-5 text-red-500" />}
                            {t.type === "info" && <Info className="h-5 w-5 text-blue-500" />}
                            {t.type === "warning" && <AlertCircle className="h-5 w-5 text-amber-500" />}

                            <span className="flex-1 text-sm font-bold leading-tight antialiased">
                                {t.message}
                            </span>

                            <button
                                onClick={() => removeToast(t.id)}
                                className="p-1 hover:bg-black/5 rounded-full transition-colors"
                            >
                                <X className="h-4 w-4 opacity-50" />
                            </button>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
        </ToastContext.Provider>
    );
};
