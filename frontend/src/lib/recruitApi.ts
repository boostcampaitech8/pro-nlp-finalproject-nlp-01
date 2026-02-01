import { getApiUrl, fetchWithAuth } from "./apiUtils";
import { Recruit } from "../types";

export interface RecruitListResponse {
    items: Recruit[];
    meta: {
        total: number;
        page: number;
        limit: number;
        totalPages: number;
    };
}

export interface RecruitApi {
    fetchRecruits: (params: URLSearchParams, activeTab: string) => Promise<RecruitListResponse>;
    getRecruit: (id: string | number) => Promise<Recruit & { content?: string }>;
}

export const recruitApi: RecruitApi = {
    fetchRecruits: async (params: URLSearchParams, activeTab: string): Promise<RecruitListResponse> => {
        const endpoint = activeTab === 'recommend' ? '/recruits/recommend' : '/recruits';
        const url = getApiUrl(`${endpoint}?${params.toString()}`);

        const res = await fetchWithAuth(url);
        if (!res.ok) {
            const error = await res.json().catch(() => ({}));
            throw new Error(error.detail || "채용 공고 목록을 불러오는데 실패했습니다.");
        }
        return res.json() as Promise<RecruitListResponse>;
    },

    getRecruit: async (id: string | number): Promise<Recruit & { content?: string }> => {
        const res = await fetchWithAuth(getApiUrl(`/recruits/${id}`));
        if (!res.ok) {
            const error = await res.json().catch(() => ({}));
            throw new Error(error.detail || "채용 공고 상세 정보를 불러오는데 실패했습니다.");
        }
        return res.json();
    }
};
