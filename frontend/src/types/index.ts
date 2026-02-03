export interface Recruit {
    id: number;
    title: string;
    company: string;
    start_date?: string;
    deadline?: string;
    tags?: string[];
    content?: string;
    reason?: string | string[];

    // Detailed Fields (Snake Case Unified)
    link?: string;
    experience?: string;
    education?: string;
    employment_type?: string;
    salary?: string;
    category?: string;
    location?: string;
    key_responsibilities?: string;
    required_qualifications?: string;
    preferred_qualifications?: string;
    view_count?: number;
}

export interface PortfolioJobQuery {
    type: 'A' | 'B' | 'C';
    query_text: string;
    evidence: string[];
}

export interface PortfolioStrength {
    tag: string;
    claim: string;
    evidence: string[];
    level: 'low' | 'medium' | 'high';
}

export interface Portfolio {
    id: number;
    project_name: string;
    type: 'link' | 'file' | 'github' | 'notion' | 'blog';
    source_url?: string;
    content?: string;
    created_at: string;

    // Status (Snake Case Unified)
    processing_status?: 'PENDING' | 'PROCESSING' | 'REVIEW_REQUIRED' | 'COMPLETED' | 'FAILED';

    // Flattened Project Data
    period?: string;
    role?: string;
    description?: string;
    tech_stack?: string[];
    strengths?: PortfolioStrength[];
    job_queries?: PortfolioJobQuery[];
}

export interface CoverLetterItem {
    id: number;
    question: string;
    content: string;
    category?: string;
    hint?: string;
    max_length?: number;
    key_points?: string[];
    suggested_improvements?: string[];
}

export interface GapAnalysisResult {
    matching_points: string[];
    missing_elements: string[];
    overall_fit: string;
}

export interface CoverLetter {
    id: number;
    title: string;
    content?: string;
    recruit_id?: number;
    recruit_title?: string;
    recruit_company?: string;
    recruit_deadline?: string;
    created_at: string;
    updated_at?: string;

    // AI Analysis (Snake Case Unified)
    processing_status?: 'PENDING' | 'PROCESSING' | 'REVIEW_REQUIRED' | 'COMPLETED' | 'FAILED';
    gap_analysis?: GapAnalysisResult;
    items?: CoverLetterItem[];
}

export interface CoverLetterVersion {
    id: number;
    cover_letter_id: number;
    title?: string;
    items_snapshot: {
        question: string;
        content: string;
        order_index?: number;
    }[];
    created_at: string;
}

export interface User {
    id: number;
    email: string;
    name: string;
    profile_summary?: string;
    desired_job_title?: string;
}

export interface NotificationEventDetail {
    type: string;
    data: {
        target_id?: number;
        title?: string;
        message?: string;
        link?: string;
        [key: string]: unknown;
    };
}
