import { getApiUrl, fetchWithAuth, isMockMode, getMockData } from "./apiUtils";

export interface IntegrationRepo {
    name: string;
    url: string;
    private: boolean;
    description: string | null;
}

export interface NotionPage {
    id: string;
    title: string;
    url: string;
}

export interface UserIntegration {
    id: number;
    provider: string;
    created_at: string;
}

export const integrationApi = {
    fetchIntegrations: async (): Promise<UserIntegration[]> => {
        if (isMockMode()) {
            return await getMockData('user_integrations.json');
        }
        const res = await fetchWithAuth(getApiUrl("/integrations"));
        if (!res.ok) return [];
        return res.json();
    },

    getGithubAuthUrl: async (): Promise<string> => {
        if (isMockMode()) return "#";
        const res = await fetchWithAuth(getApiUrl("/integrations/github/auth-url"));
        if (!res.ok) throw new Error("Failed to get GitHub auth URL");
        const data = await res.json();
        return data.url;
    },

    fetchGithubRepos: async (): Promise<IntegrationRepo[]> => {
        if (isMockMode()) return [
            { name: "mock-repo-1", url: "#", private: false, description: "Sample GitHub Repository" },
            { name: "mock-repo-2", url: "#", private: true, description: "Private Mock Project" }
        ];
        const res = await fetchWithAuth(getApiUrl("/integrations/github/repos"));
        if (!res.ok) throw new Error("Failed to fetch Github repos");
        return res.json();
    },

    getNotionAuthUrl: async (): Promise<string> => {
        if (isMockMode()) return "#";
        const res = await fetchWithAuth(getApiUrl("/integrations/notion/auth-url"));
        if (!res.ok) throw new Error("Failed to get Notion auth URL");
        const data = await res.json();
        return data.url;
    },

    fetchNotionPages: async (): Promise<NotionPage[]> => {
        if (isMockMode()) return [
            { id: "p1", title: "My Portfolio Page", url: "#" },
            { id: "p2", title: "Project Case Studies", url: "#" }
        ];
        const res = await fetchWithAuth(getApiUrl("/integrations/notion/pages"));
        if (!res.ok) throw new Error("Failed to fetch Notion pages");
        return res.json();
    },

    removeIntegration: async (id: number): Promise<boolean> => {
        if (isMockMode()) return true;
        const res = await fetchWithAuth(getApiUrl(`/integrations/${id}`), {
            method: "DELETE"
        });
        return res.ok;
    }
};
