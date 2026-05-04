import { useAuthStore } from "@/stores/useAuthStore";

export function isMockMode(): boolean {
    if (typeof window === 'undefined') return false;
    // Enable mock mode if hostname contains github.io or if explicitly set in env
    return window.location.hostname.includes('github.io') || process.env.NEXT_PUBLIC_MOCK === 'true';
}

export function getApiUrl(path: string): string {
    if (isMockMode()) {
        // In mock mode, we point to the public/mock-data directory
        // We'll handle the actual fetching in fetchWithAuth
        return path;
    }

    let baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
    if (baseUrl && !baseUrl.startsWith('http')) {
        baseUrl = `https://${baseUrl}`;
    }
    const prefix = process.env.NEXT_PUBLIC_API_URL_PREFIX || '/api';

    const cleanPath = path.startsWith('http')
        ? path
        : path.startsWith('/') ? path : `/${path}`;

    if (cleanPath.startsWith(prefix)) {
        return `${baseUrl}${cleanPath}`;
    }

    return `${baseUrl}${prefix}${cleanPath}`;
}

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
    if (isMockMode()) {
        return mockFetch(url, options);
    }

    const token = useAuthStore.getState().token;
    const headers: HeadersInit = {
        ...options.headers,
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    };

    if (options.method && !["GET", "HEAD"].includes(options.method.toUpperCase())) {
        const isFormData = options.body instanceof FormData;
        if (!isFormData && !(headers as Record<string, string>)["Content-Type"]) {
            (headers as Record<string, string>)["Content-Type"] = "application/json";
        }
    }

    const res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
        useAuthStore.getState().logout();
        if (typeof window !== 'undefined') {
            window.location.href = '/login';
        }
    }

    return res;
}

async function mockFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const method = options.method?.toUpperCase() || 'GET';
    const path = url.split('?')[0];

    // 1. Intercept Auth and Create/Update/Delete operations
    const isAuth = path.includes('/auth/register') || path.includes('/auth/login') || path.includes('/auth/kakao');
    const isWrite = ["POST", "PUT", "PATCH", "DELETE"].includes(method);

    if (isAuth || isWrite) {
        return new Response(JSON.stringify({ detail: "현재 Mocking 에서 지원하지않는 기능입니다." }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' }
        });
    }

    // 2. Handle Read operations (GET)
    try {
        let mockFile = '';
        if (path.includes('/recruits')) {
            mockFile = 'recruitments.json';
        } else if (path.includes('/portfolios')) {
            mockFile = 'portfolios.json';
        } else if (path.includes('/cover-letters')) {
            mockFile = 'cover_letters.json';
        } else if (path.includes('/notifications')) {
            mockFile = 'notifications.json';
        } else if (path.includes('/users/me')) {
            // Return one of the allowed users as "me" for demo purposes
            // We'll pick ID 6 (김OO)
            const usersRes = await fetch('/mock-data/users.json');
            const users = await usersRes.json();
            const me = users.find((u: any) => u.id === '6' || u.name === '김OO');
            return new Response(JSON.stringify(me), { status: 200, headers: { 'Content-Type': 'application/json' } });
        }

        if (mockFile) {
            const res = await fetch(`/mock-data/${mockFile}`);
            const data = await res.json();

            // Handle list vs detail
            const idMatch = path.match(/\/(\d+)$/);
            if (idMatch) {
                const id = idMatch[1];
                const item = data.find((i: any) => i.id === id);
                if (item) {
                    return new Response(JSON.stringify(item), { status: 200, headers: { 'Content-Type': 'application/json' } });
                }
                return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
            }

            // Handle filtering/pagination (simple mock)
            let filteredData = data;
            if (path.includes('/recruits')) {
                // Return in the expected RecruitListResponse format
                return new Response(JSON.stringify({
                    items: filteredData.slice(0, 10),
                    meta: { total: filteredData.length, page: 1, limit: 10, totalPages: 1 }
                }), { status: 200, headers: { 'Content-Type': 'application/json' } });
            }

            return new Response(JSON.stringify(filteredData), { status: 200, headers: { 'Content-Type': 'application/json' } });
        }
    } catch (e) {
        console.error("Mock fetch error:", e);
    }

    return new Response(JSON.stringify({ detail: "Mock data not found" }), { status: 404 });
}
