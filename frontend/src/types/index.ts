export interface Recruit {
    id: number;
    title: string;
    company: string;
    startDate: string;
    deadline: string;
    tags: string[];
    content?: string;
}

export interface Portfolio {
    id: number;
    title: string;
    type: 'link' | 'file' | 'github' | 'notion';
    url?: string;
    fileName?: string;
    createdAt: string;
    content?: string;

    // Status
    processingStatus?: 'PENDING' | 'COMPLETED' | 'FAILED';

    // Flattened Project Data
    extractedSummary?: string;
    extracted_summary?: string;
    extractedJobTitle?: string;
    extracted_job_title?: string;
    projectName?: string;
    project_name?: string;
    period?: string;
    role?: string;
    description?: string;
    techStack?: string[];
    tech_stack?: string[];
    source_url?: string;
}

export interface CoverLetter {
    id: number;
    title: string;
    content: string;
    recruitId?: number;
    recruitTitle?: string;
    recruitCompany?: string;
    recruitDeadline?: string;
    updatedAt: string;
}

export interface User {
    id: number;
    email: string;
    name: string;
}
