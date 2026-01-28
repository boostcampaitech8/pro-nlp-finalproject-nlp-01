import { getApiUrl, fetchWithAuth } from "./apiUtils";
import { Portfolio } from "../types";

export interface PortfolioApi {
    uploadFile: (file: File) => Promise<Portfolio>;
    importNotion: (url: string, title?: string) => Promise<Portfolio>;
    importGithub: (url: string, title?: string) => Promise<Portfolio>;
    fetchAll: () => Promise<{ items: Portfolio[] }>;
}

export const portfolioApi: PortfolioApi = {
    /**
     * Upload a file (PDF, TXT, MD) to create a portfolio.
     */
    uploadFile: async (file: File): Promise<Portfolio> => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("title", file.name); // Default title to filename

        const res = await fetchWithAuth(getApiUrl("/portfolios/upload"), {
            method: "POST",
            body: formData,
            // fetchWithAuth handles Authorization.
            // Content-Type for FormData is automatically set by browser with boundary.
            // Do NOT manually set Content-Type to multipart/form-data here.
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || "File upload failed");
        }

        return res.json();
    },

    /**
     * Import portfolio from a Notion URL.
     */
    importNotion: async (url: string, title: string = "Notion Page"): Promise<Portfolio> => {
        const formData = new FormData();
        formData.append("url", url);
        formData.append("title", title);

        // Alternatively, if backend accepts JSON for notion import (check backend):
        // Backend uses Form(...) for url and title. So FormData is correct.

        const res = await fetchWithAuth(getApiUrl("/portfolios/notion"), {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || "Notion import failed");
        }

        return res.json();
    },

    /**
     * Import portfolio from a GitHub URL (Repo or Profile).
     */
    importGithub: async (url: string, title: string = "GitHub Portfolio"): Promise<Portfolio> => {
        const formData = new FormData();
        formData.append("url", url);
        formData.append("title", title);

        const res = await fetchWithAuth(getApiUrl("/portfolios/github"), {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || "GitHub import failed");
        }

        return res.json();
    },

    /**
     * Fetch all portfolios.
     */
    fetchAll: async (): Promise<{ items: Portfolio[] }> => {
        const res = await fetchWithAuth(getApiUrl("/portfolios"));
        if (!res.ok) {
            throw new Error("Failed to fetch portfolios");
        }
        return res.json();
    }
};
