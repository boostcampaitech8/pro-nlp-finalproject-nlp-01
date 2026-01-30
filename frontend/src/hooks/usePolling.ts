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

    useEffect(() => {
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

        // Initial fetch
        fetchData().then((result) => {
            if (result && stopCondition && stopCondition(result)) {
                // Already done, don't poll
                return;
            }
            // Start polling
            intervalRef.current = setInterval(async () => {
                const newData = await fetchData();
                if (newData && stopCondition && stopCondition(newData)) {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                }
            }, intervalMs);
        });

        return () => {
            isMounted = false;
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [endpoint, intervalMs, stopCondition]);

    return { data, loading, error };
}
