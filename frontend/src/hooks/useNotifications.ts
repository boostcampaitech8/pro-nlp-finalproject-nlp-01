"use client";

import { useEffect, useState, useCallback } from "react";
import { useToast } from "@/components/ui/toast-context";
import { useAuthStore } from "@/stores/useAuthStore";
import { getApiUrl, isMockMode } from "@/lib/apiUtils";

export interface Notification {
    id: number;
    title: string;
    message: string;
    is_read: boolean;
    link?: string;
    created_at: string;
}

// Options interface
interface UseNotificationsOptions {
    showToast?: boolean;
}

export function useNotifications(options: UseNotificationsOptions = { showToast: true }) {
    const { isAuthenticated, token } = useAuthStore();
    const { toast } = useToast();
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);

    const fetchNotifications = useCallback(async () => {
        if (!isAuthenticated) return;
        try {
            const url = getApiUrl("/api/notifications");
            // Add timestamp to query to force bypass browser cache
            const cacheBuster = `?t=${new Date().getTime()}`;
            const res = await fetch(url + cacheBuster, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Pragma': 'no-cache',
                    'Cache-Control': 'no-cache'
                },
                cache: 'no-store' // Next.js specific
            });
            if (res.ok) {
                const data = await res.json();
                setNotifications(data?.items || []);
                setUnreadCount(data?.unread_count || 0);
            }
        } catch (err) {
            console.error("Failed to fetch notifications", err);
        }
    }, [isAuthenticated, token]);

    const markAsRead = async (id: number) => {
        // Optimistic Update
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
        setUnreadCount(prev => Math.max(0, prev - 1));

        try {
            const res = await fetch(getApiUrl(`/api/notifications/${id}/read`), {
                method: "PATCH",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (!res.ok) {
                // Revert if failed (optional, but good practice)
                fetchNotifications();
            }
        } catch (err) {
            console.error("Failed to mark notification as read", err);
            fetchNotifications();
        }
    };

    const markAllAsRead = async () => {
        // Optimistic Update
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        setUnreadCount(0);

        try {
            const res = await fetch(getApiUrl(`/api/notifications/read-all`), {
                method: "PATCH",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (!res.ok) {
                fetchNotifications();
            }
        } catch (err) {
            console.error("Failed to mark all notifications as read", err);
            fetchNotifications();
        }
    };

    // Smart SSE State
    const [isPageVisible, setIsPageVisible] = useState(true);
    const [isUserIdle, setIsUserIdle] = useState(false);

    // 1. Visibility Detection
    useEffect(() => {
        const handleVisibilityChange = () => {
            const visible = !document.hidden;
            setIsPageVisible(visible);
            if (visible) {
                fetchNotifications();
            }
        };

        // Initialize state (deferred to avoid synchronous setState warning)
        // If state is already matching, we don't need to do anything.
        if (document.hidden) {
            // Use setTimeout to avoid "setState synchronously within effect" lint error
            const timer = setTimeout(() => setIsPageVisible(false), 0);
            return () => clearTimeout(timer);
        }

        document.addEventListener("visibilitychange", handleVisibilityChange);
        return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
    }, [fetchNotifications]);

    // 2. Idle Detection (5 minutes timeout)
    useEffect(() => {
        let timeoutId: NodeJS.Timeout;
        const IDLE_TIMEOUT = 5 * 60 * 1000; // 5 minutes

        const resetIdle = () => {
            if (isUserIdle) {
                setIsUserIdle(false); // Waking up
            }
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => setIsUserIdle(true), IDLE_TIMEOUT);
        };

        // Events to detect user activity
        const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];

        // Throttled handler could be better but native events are fine for resetting timer
        events.forEach(e => document.addEventListener(e, resetIdle, { passive: true }));

        resetIdle(); // Start timer

        return () => {
            events.forEach(e => document.removeEventListener(e, resetIdle));
            clearTimeout(timeoutId);
        };
    }, [isUserIdle]);

    // Determine if we should maintain the expensive SSE connection
    // Cloud Run scales to zero, so disconnecting when idle saves money.
    const isRealtimeActive = isPageVisible && !isUserIdle;

    // 3. SSE Manager
    useEffect(() => {
        if (!isAuthenticated) return;

        // If inactive, do not connect SSE to save resources/cost.
        // We relying on fetchNotifications() called by visibility/idle handlers when becoming active.
        // If inactive or in Mock mode, do not connect SSE.
        if (!isRealtimeActive || isMockMode()) {
            return;
        }

        // Initialize (Load latest data when becoming active)
        const init = async () => {
            await fetchNotifications();
        };
        init();

        // SSE Setup
        // Construction using getApiUrl to avoid path issues
        const ssePath = `/api/notifications/events?token=${token}`;
        const sseUrl = getApiUrl(ssePath);

        console.log("Connecting Notification SSE...");
        const eventSource = new EventSource(sseUrl);

        eventSource.onopen = () => {
            // console.log("SSE Connected");
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Show Toast only if enabled and there is content
                if (options.showToast !== false && (data.message || data.title)) {
                    toast(data.message || data.title, "success");
                }

                // 1. Refresh global notification list/count
                fetchNotifications();

                // 2. Broadcast Custom Event for specific UI updates
                if (data.type) {
                    const event = new CustomEvent('notification_event', {
                        detail: { type: data.type, data: data }
                    });
                    window.dispatchEvent(event);
                    console.log(`Global event dispatched: status_update_${data.type}`);
                }
            } catch (e) {
                console.error("SSE Parse Error", e);
            }
        };

        eventSource.onerror = (err) => {
            // Do not close connection on error, let EventSource retry automatically
            // unless we want to stop retrying on fatal auth errors?
            // For now, simple warning.
            console.warn("SSE Connection lost, retrying...", err);
        };

        return () => {
            console.log("Closing Notification SSE (Inactive or Unmount)");
            eventSource.close();
        };
    }, [isAuthenticated, token, fetchNotifications, toast, isRealtimeActive, options.showToast]);

    return { notifications, unreadCount, markAsRead, markAllAsRead, refresh: fetchNotifications };
}
