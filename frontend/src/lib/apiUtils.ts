import { useAuthStore } from "@/stores/useAuthStore";

export function isMockMode(): boolean {
    if (typeof window === 'undefined') return false;
    return window.location.hostname.includes('github.io') || 
           window.location.hostname.includes('localhost') ||
           process.env.NEXT_PUBLIC_MOCK === 'true';
}

function normalizeMockPath(path: string): string {
    const isGitHubPages = typeof window !== 'undefined' && window.location.hostname.includes('github.io');
    const basePath = isGitHubPages ? '/pro-nlp-finalproject-nlp-01' : '';
    
    let cleanPath = path;
    if (path.startsWith('http')) {
        try {
            cleanPath = new URL(path).pathname;
        } catch (e) {}
    }
    
    if (!cleanPath.startsWith('/')) cleanPath = '/' + cleanPath;
    if (basePath && cleanPath.startsWith(basePath)) {
        return cleanPath;
    }
    return `${basePath}${cleanPath}`;
}

export function getApiUrl(path: string): string {
    if (isMockMode()) {
        return normalizeMockPath(path);
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

if (typeof window !== 'undefined' && isMockMode()) {
    const originalFetch = window.fetch;
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : (input as URL).toString();
        if (url.includes('/mock-data/')) {
            return originalFetch(input, init);
        }
        return mockFetch(url, init);
    };

    // Global SSE Stub
    if (!window.EventSource || isMockMode()) {
        (window as any).EventSource = class {
            onopen: any = null;
            onmessage: any = null;
            onerror: any = null;
            constructor(url: string) {
                console.log("Mock EventSource initialized for:", url);
                setTimeout(() => { if (this.onopen) this.onopen(); }, 100);
            }
            close() { console.log("Mock EventSource closed"); }
        };
    }
}

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
    return fetch(url, options);
}

export async function getMockData(mockFile: string): Promise<any> {
    const isGitHubPages = typeof window !== 'undefined' && window.location.hostname.includes('github.io');
    const basePath = isGitHubPages ? '/pro-nlp-finalproject-nlp-01' : '';
    const res = await fetch(`${basePath}/mock-data/${mockFile}`);
    const rawData = await res.json();
    
    const normalize = (obj: any) => {
        if (!obj || typeof obj !== 'object') return obj;
        const arrayFields = ['tags', 'questions', 'tech_stack', 'strengths'];
        arrayFields.forEach(field => {
            if (typeof obj[field] === 'string') {
                try { obj[field] = JSON.parse(obj[field]); } catch (e) { obj[field] = []; }
            }
        });
        return obj;
    };
    
    return Array.isArray(rawData) ? rawData.map(normalize) : normalize(rawData);
}

async function mockFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const method = options.method?.toUpperCase() || 'GET';
    const isGitHubPages = typeof window !== 'undefined' && window.location.hostname.includes('github.io');
    const basePath = isGitHubPages ? '/pro-nlp-finalproject-nlp-01' : '';
    
    let path = url;
    if (url.startsWith('http')) {
        try {
            path = new URL(url).pathname;
        } catch (e) {}
    }
    const cleanPath = path.split('?')[0];

    const jsonRes = (data: any, status = 200) => new Response(JSON.stringify(data), {
        status,
        headers: { 'Content-Type': 'application/json' }
    });

    // 1. Intercept Auth & User
    if ((cleanPath.includes('/auth/login') || cleanPath.includes('/auth/test-login')) && method === 'POST') {
        try {
            const body = JSON.parse(options.body as string);
            const email = body.email || '';
            const role = body.role || '';
            let targetEmail = email;
            if (role && cleanPath.includes('test-login')) {
                targetEmail = `exhibit_${role}@pro-nlp.ai`;
            }

            if (targetEmail.includes('exhibit')) {
                const users = await getMockData('users.json');
                const user = users.find((u: { email: string }) => u.email === targetEmail);
                if (user) {
                    return jsonRes({
                        access_token: "mock-token-" + user.id,
                        token_type: "bearer",
                        user: user
                    });
                }
            }
        } catch (e) {}
        return jsonRes({ detail: "테스트 계정 정보를 확인해주세요." }, 401);
    }

    if (cleanPath.includes('/users/me') || cleanPath.includes('/auth/me')) {
        const token = useAuthStore.getState().token || '';
        const userId = token.replace('mock-token-', '');
        const users = await getMockData('users.json');
        const me = users.find((u: { id: string }) => String(u.id) === userId) || users[0];
        return jsonRes(me);
    }

    // 2. Intercept Writes & AI
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
        if (cleanPath.includes('/portfolios/upload') || cleanPath.includes('/portfolios/analyze')) {
            return jsonRes({ success: true, portfolio_id: 6, status: 'completed' });
        }
        if (cleanPath.includes('/integrations/github/auth-url') || cleanPath.includes('/integrations/notion/auth-url')) {
            return jsonRes({ url: "#" });
        }
        if (cleanPath.includes('/cover-letters/generate')) {
            const body = JSON.parse(options.body as string);
            return jsonRes({ 
                id: body.cover_letter_id || 18, 
                processing_status: 'PENDING',
                message: "AI 생성이 시작되었습니다." 
            });
        }
        if (cleanPath.includes('/headline')) {
            return jsonRes({ title: "[혁신과 도전] 끊임없는 배움으로 성장하는 개발자" });
        }
        if (cleanPath.includes('/confirm')) {
            return jsonRes({ processing_status: 'COMPLETED', status: 'COMPLETED' });
        }
        // General success
        return jsonRes({ success: true, message: "Mocking 환경에서 처리되었습니다." });
    }

    // 3. Handle Read operations (GET)
    try {
        let mockFile = '';
        if (cleanPath.includes('/recruits')) mockFile = 'recruitments.json';
        else if (cleanPath.includes('/portfolios')) mockFile = 'portfolios.json';
        else if (cleanPath.includes('/cover-letters')) mockFile = 'cover_letters.json';
        else if (cleanPath.includes('/cover-letter-items')) mockFile = 'cover_letter_items.json';
        else if (cleanPath.includes('/notifications')) mockFile = 'notifications.json';
        else if (cleanPath.includes('/integrations')) mockFile = 'user_integrations.json';

        if (mockFile) {
            const data = await getMockData(mockFile);

            // Handle Versions specially
            if (cleanPath.includes('/versions')) {
                return jsonRes([
                    { id: 101, title: "최초 작성본", created_at: "2026-05-01T10:00:00Z", items_snapshot: [] },
                    { id: 102, title: "AI 초안 생성본", created_at: "2026-05-02T14:30:00Z", items_snapshot: [] }
                ]);
            }

            // Detail mapping
            const idMatch = cleanPath.match(/\/(\d+)$/);
            if (idMatch && !cleanPath.includes('/notifications')) {
                const id = idMatch[1];
                const item = data.find((i: { id: string }) => String(i.id) === id);
                if (item) {
                    // For cover letters, join with items
                    if (cleanPath.includes('/cover-letters')) {
                        item.processing_status = item.processing_status || 'COMPLETED';
                        
                        // Load and attach items
                        try {
                            const allItems = await getMockData('cover_letter_items.json');
                            item.items = allItems
                                .filter((it: any) => String(it.cover_letter_id) === String(id))
                                .map((it: any) => ({
                                    ...it,
                                    id: parseInt(it.id),
                                    key_points: typeof it.key_points === 'string' ? JSON.parse(it.key_points) : it.key_points,
                                    suggested_improvements: typeof it.suggested_improvements === 'string' ? JSON.parse(it.suggested_improvements) : it.suggested_improvements
                                }));
                        } catch (e) {
                            console.error("Failed to load mock items for cover letter", e);
                            item.items = [];
                        }
                    }
                    return jsonRes(item);
                }
                return jsonRes({ detail: "Not Found" }, 404);
            }

            // List mapping
            if (cleanPath.includes('/recruits')) {
                // If recommend, shuffle or filter slightly
                const list = cleanPath.includes('recommend') ? data.slice(5, 15) : data.slice(0, 10);
                return jsonRes({
                    items: list,
                    meta: { total: data.length, page: 1, limit: 10, totalPages: 1 }
                });
            }

            if (cleanPath.includes('/notifications')) {
                const unread = data.filter((n: any) => String(n.is_read) === 'false').length;
                return jsonRes({ items: data, unread_count: unread });
            }

            if (cleanPath.includes('/portfolios') || cleanPath.includes('/cover-letters')) {
                return jsonRes({ items: data });
            }

            return jsonRes(data);
        }
    } catch (e) {
        console.error("Mock fetch error:", e);
    }

    return jsonRes({ detail: "Mock data not found" }, 404);
}
