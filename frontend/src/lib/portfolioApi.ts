import { getApiUrl, fetchWithAuth, isMockMode, getMockData } from "./apiUtils";
import { Portfolio } from "../types";

export interface AnalysisResult {
    portfolio_id?: number;
    status?: string;
    success: boolean;
    error?: string;
}

export interface PortfolioApi {
    uploadFile: (file: File) => Promise<Portfolio>;
    importNotion: (url: string, title?: string) => Promise<Portfolio>;
    importGithub: (url: string, title?: string) => Promise<Portfolio>;
    importBlog: (url: string, title?: string) => Promise<Portfolio>;
    analyzePortfolio: (source: string, type: string) => Promise<AnalysisResult>;
    analyzePortfolioFile: (file: File) => Promise<AnalysisResult>;
    getPortfolio: (id: number) => Promise<Portfolio>;
    discoverBlogPosts: (url: string) => Promise<{ title: string; url: string }[]>;
    createPortfolio: (data: Partial<Portfolio>) => Promise<Portfolio>;
    fetchAll: () => Promise<{ items: Portfolio[] }>;
    deletePortfolio: (id: number) => Promise<boolean>;
}

export const portfolioApi: PortfolioApi = {
    /**
     * Upload a file (PDF, TXT, MD) to create a portfolio.
     */
    uploadFile: async (file: File): Promise<Portfolio> => {
        if (isMockMode()) {
            const data = await getMockData('portfolios.json');
            return data[0];
        }
        const formData = new FormData();

        const res = await fetchWithAuth(getApiUrl("/portfolios/upload"), {
            method: "POST",
            body: formData,
            // fetchWithAuth handles Authorization.
            // Content-Type for FormData is automatically set by browser with boundary.
            // Do NOT manually set Content-Type to multipart/form-data here.
        });

        if (!res.ok) {
            const errorData = (await res.json().catch(() => ({}))) as { detail?: string };
            throw new Error(errorData.detail || "File upload failed");
        }

        return res.json() as Promise<Portfolio>;
    },

    /**
     * Import portfolio from a Notion URL.
     */
    importNotion: async (url: string, projectName: string = "Notion Page"): Promise<Portfolio> => {
        const res = await fetchWithAuth(getApiUrl("/portfolios/notion"), {
            method: "POST",
            body: JSON.stringify({
                project_name: projectName,
                source_url: url,
                type: "notion"
            }),
        });

        if (!res.ok) {
            const errorData = (await res.json().catch(() => ({}))) as { detail?: string };
            throw new Error(errorData.detail || "Notion import failed");
        }

        return res.json() as Promise<Portfolio>;
    },

    /**
     * Import portfolio from a GitHub URL (Repo or Profile).
     */
    importGithub: async (url: string, projectName: string = "GitHub Portfolio"): Promise<Portfolio> => {
        const res = await fetchWithAuth(getApiUrl("/portfolios/github"), {
            method: "POST",
            body: JSON.stringify({
                project_name: projectName,
                source_url: url,
                type: "github"
            }),
        });

        if (!res.ok) {
            const errorData = (await res.json().catch(() => ({}))) as { detail?: string };
            throw new Error(errorData.detail || "GitHub import failed");
        }

        return res.json() as Promise<Portfolio>;
    },

    /**
     * Import portfolio from a Blog URL (Velog, Tistory).
     */
    importBlog: async (url: string, projectName: string = "Blog Portfolio"): Promise<Portfolio> => {
        const res = await fetchWithAuth(getApiUrl("/portfolios/blog"), {
            method: "POST",
            body: JSON.stringify({
                project_name: projectName,
                source_url: url,
                type: "blog"
            }),
        });

        if (!res.ok) {
            const errorData = (await res.json().catch(() => ({}))) as { detail?: string };
            throw new Error(errorData.detail || "Blog import failed");
        }

        return res.json() as Promise<Portfolio>;
    },

    /**
     * Analyze a portfolio source (preview only).
     */
    analyzePortfolio: async (source: string, type: string): Promise<AnalysisResult> => {
        if (isMockMode()) return { success: true, status: 'completed', portfolio_id: 35 };
        const res = await fetchWithAuth(getApiUrl("/portfolios/analyze"), {
            method: "POST",
            body: JSON.stringify({ source, type }),
        });

        if (!res.ok) {
            const errorData = (await res.json().catch(() => ({}))) as { detail?: string };
            throw new Error(errorData.detail || "Analysis failed");
        }

        return res.json() as Promise<AnalysisResult>;
    },

    analyzePortfolioFile: async (file: File): Promise<AnalysisResult> => {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetchWithAuth(getApiUrl("/portfolios/analyze/file"), {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const errorData = (await res.json().catch(() => ({}))) as { detail?: string };
            throw new Error(errorData.detail || "File analysis failed");
        }

        return res.json() as Promise<AnalysisResult>;
    },

    getPortfolio: async (id: number): Promise<Portfolio> => {
        if (isMockMode()) {
            const data = await getMockData('portfolios.json');
            const item = data.find((p: any) => String(p.id) === String(id));
            if (!item) throw new Error("포트폴리오를 찾을 수 없습니다.");
            return item;
        }
        const res = await fetchWithAuth(getApiUrl(`/portfolios/${id}`));
        if (!res.ok) {
            throw new Error("Failed to fetch portfolio detail");
        }
        return res.json() as Promise<Portfolio>;
    },

    discoverBlogPosts: async (url: string): Promise<{ title: string; url: string }[]> => {
        const res = await fetchWithAuth(getApiUrl(`/portfolios/blog/discover?url=${encodeURIComponent(url)}`));
        if (!res.ok) {
            throw new Error("Failed to discover blog posts");
        }
        return res.json() as Promise<{ title: string; url: string }[]>;
    },

    /**
     * Delete a portfolio.
     */
    deletePortfolio: async (id: number): Promise<boolean> => {
        if (isMockMode()) return true;
        const res = await fetchWithAuth(getApiUrl(`/portfolios/${id}`), {
            method: "DELETE"
        });
        return res.ok;
    },

    /**
     * Create a portfolio from processed data.
     */
    createPortfolio: async (data: Partial<Portfolio>): Promise<Portfolio> => {
        const res = await fetchWithAuth(getApiUrl("/portfolios"), {
            method: "POST",
            body: JSON.stringify(data),
        });

        if (!res.ok) {
            const errorData = (await res.json().catch(() => ({}))) as { detail?: string };
            throw new Error(errorData.detail || "Creation failed");
        }

        return res.json() as Promise<Portfolio>;
    },

    /**
     * Fetch all portfolios.
     */
    fetchAll: async (): Promise<{ items: Portfolio[] }> => {
        if (isMockMode()) {
            const data = await getMockData('portfolios.json');
            return { items: data };
        }
        const res = await fetchWithAuth(getApiUrl("/portfolios"));
        if (!res.ok) {
            throw new Error("Failed to fetch portfolios");
        }
        return res.json() as Promise<{ items: Portfolio[] }>;
    }
};
