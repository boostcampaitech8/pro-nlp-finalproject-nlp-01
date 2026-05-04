"""
Pydantic schemas for Cover Letter Generation
Adapted from llm-pipeline/self_introduction/src/schemas.py
"""
from typing import List
from pydantic import BaseModel, Field

class GapAnalysisResult(BaseModel):
    """Gap analysis result schema"""
    
    overall_fit: str = Field(
        description="종합 적합도 평가 결과. 반드시 '상', '중', '하' 중 하나로 입력."
    )

    is_gap_found: bool = Field(
        description="True if essential skills are missing, False if well matched"
    )
    
    matching_points: List[str] = Field(
        default_factory=list,
        description="List of matching points between user experience and job requirements (in Korean)"
    )
    
    missing_elements: List[str] = Field(
        default_factory=list,
        description="List of missing skills/experiences in user profile compared to job requirements (in Korean)"
    )
    
    question_to_user: str = Field(
        default="",
        description="Question to ask the user to bridge the gap (Empty string if no gap, polite Korean)"
    )
    
    reasoning: str = Field(
        default="",
        description="Detailed reasoning for the analysis (in Korean)"
    )


class ResumeGenerationResult(BaseModel):
    """Cover Letter Generation Result Schema"""
    
    title: str = Field(
        description="Catchy subheading or headline for this section (e.g., '[데이터 기반의 의사결정으로 성과 창출]'). Should be concise and impactful."
    )
    
    content: str = Field(
        description="Generated cover letter content. valid natural language. No labels (Situation, Task, etc.). 600~800 characters."
    )

    key_points: List[str] = Field(
        default_factory=list,
        description="List of key competencies emphasized in the content (3-5 items)"
    )

    suggested_improvements: List[str] = Field(
        default_factory=list,
        description="Suggestions for improving the content or experiences (e.g., 'Add more quantitative metrics')"
    )

class EvidenceItem(BaseModel):
    """Evidence item for outline section"""
    project_name: str = Field(default="", description="Project or experience name")
    reason: str = Field(default="", description="Reason for using this project in this section")

class OutlineSection(BaseModel):
    """Section guide for outline"""
    section_title: str = Field(description="Title or theme of the paragraph")
    paragraph_goal: str = Field(description="Core goal of this paragraph")
    key_points: List[str] = Field(default_factory=list, description="Key bullet points to include (3-5 items)")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Projects/Experiences to use as evidence")

class ResumeOutlineResult(BaseModel):
    """Cover Letter Outline Result Schema"""
    
    one_liner: str = Field(description="A single sentence conclusion (Du-gwal-sik) summarizing the whole answer")
    key_messages: List[str] = Field(default_factory=list, description="3 key messages/keywords to emphasize")
    paragraph_plans: List[OutlineSection] = Field(description="Paragraph composition plans (2-3 sections)")
    questions_for_user: List[str] = Field(
        default_factory=list,
        description="Questions to ask the user to fill missing info (quantitative metrics, role details, etc.)"
    )

class HeadlineGenerationResult(BaseModel):
    """Headline generation result schema"""
    headline: str = Field(description="A single, compelling headline (15 characters or less, noun phrase)")
