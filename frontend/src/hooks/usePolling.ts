import { useState, useEffect, useRef } from 'react';
import { getApiUrl, fetchWithAuth } from '@/lib/apiUtils';

export function usePolling<T>(
    endpoint: string,
    intervalMs: number = 3000,
    stopCondition?: (data: T) => boolean
) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<unknown>(null);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const stopConditionRef = useRef(stopCondition);

    // Keep stopConditionRef up to date without re-triggering the effect
    useEffect(() => {
        stopConditionRef.current = stopCondition;
    }, [stopCondition]);

    useEffect(() => {
        // Guard: If endpoint is empty, don't do anything
        if (!endpoint) {
            setLoading(false);
            return;
        }

        let isMounted = true;
        const fetchData = async () => {
            try {
                const res = await fetchWithAuth(getApiUrl(endpoint));
                if (!res.ok) throw new Error("Failed to fetch");
                const result = await res.json();
                if (isMounted) setData(result);
                return result;
            } catch (err) {
                if (isMounted) setError(err);
                return null;
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        const startPolling = async () => {
            const result = await fetchData();

            // Check initial result against stop condition
            if (result && stopConditionRef.current && stopConditionRef.current(result)) {
                return;
            }

            // Start periodic polling
            intervalRef.current = setInterval(async () => {
                const newData = await fetchData();
                if (newData && stopConditionRef.current && stopConditionRef.current(newData)) {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                }
            }, intervalMs);
        };

        startPolling();

        return () => {
            isMounted = false;
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [endpoint, intervalMs]); // stopCondition removed from dependencies

    return { data, loading, error };
}
