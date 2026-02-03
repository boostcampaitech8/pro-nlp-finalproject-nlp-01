from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from typing import List, Optional
from datetime import date, datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    pass

class UserIntegration(BaseModel):
    id: int
    provider: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class User(UserBase):
    id: int
    created_at: datetime
    profile_summary: Optional[str] = None
    desired_job_title: Optional[str] = None
    integrations: List[UserIntegration] = []
    model_config = ConfigDict(from_attributes=True)

# Recruitment Schemas
class RecruitmentBase(BaseModel):
    title: str
    company: str
    link: Optional[str] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    location: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None
    category: Optional[str] = None
    key_responsibilities: Optional[str] = None
    required_qualifications: Optional[str] = None
    preferred_qualifications: Optional[str] = None
    company_description: Optional[str] = None  # 기업 인재상/핵심 가치
    reason: Optional[str] = None
    view_count: Optional[int] = 0
    tags: List[str] = []

    @field_validator('tags', mode='before')
    @classmethod
    def set_tags_default(cls, v):
        return v or []

class RecruitmentCreate(RecruitmentBase):
    pass

class Recruitment(RecruitmentBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RecruitmentListResponse(BaseModel):
    items: List[Recruitment]
    meta: dict
    model_config = ConfigDict(from_attributes=True)

# Portfolio Strength Schema
class PortfolioStrength(BaseModel):
    tag: str
    claim: str
    evidence: List[str] = []
    level: str # low, medium, high

# Portfolio Schemas
class PortfolioBase(BaseModel):
    type: str
    source_url: Optional[str] = None
    project_name: Optional[str] = None
    period: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    strengths: Optional[List[PortfolioStrength]] = None

class PortfolioCreate(PortfolioBase):
    user_id: int

class PortfolioJobQueryCreate(BaseModel):
    type: str
    query_text: str
    evidence: Optional[List[str]] = []

class PortfolioJobQuery(PortfolioJobQueryCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class PortfolioSummary(PortfolioBase):
    id: int
    user_id: int
    created_at: datetime
    
    processing_status: Optional[str] = None
    
    # Flattened Project Details
    project_name: str  # Now required
    period: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    strengths: Optional[List[PortfolioStrength]] = None
    
    model_config = ConfigDict(from_attributes=True)

# Legacy alias for backward compatibility or simple usage
class Portfolio(PortfolioSummary):
    pass

class PortfolioDetail(PortfolioSummary):
    # Relationship
    job_queries: List[PortfolioJobQuery] = []

class PortfolioListResponse(BaseModel):
    items: List[PortfolioSummary]
    model_config = ConfigDict(from_attributes=True)

class PortfolioCreateRequest(PortfolioBase):
    job_queries: Optional[List[PortfolioJobQueryCreate]] = []
    
    @field_validator('source_url')
    @classmethod
    def validate_source_url(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.strip()) == 0:
            raise ValueError("Source URL cannot be empty")
        if v and len(v) > 2048:
            raise ValueError("Source URL is too long (max 2048 characters)")
        return v.strip() if v else v
    
    @field_validator('project_name')
    @classmethod
    def validate_project_name(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.strip()) == 0:
            raise ValueError("Project name cannot be empty")
        if v and len(v) > 200:
            raise ValueError("Project name is too long (max 200 characters)")
        return v.strip() if v else v
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v:
            allowed_types = ['github', 'notion', 'blog', 'file']
            if v not in allowed_types:
                raise ValueError(f"Type must be one of: {', '.join(allowed_types)}")
        return v

class PortfolioUpdateRequest(BaseModel):
    type: Optional[str] = None
    source_url: Optional[str] = None
    content: Optional[str] = None
    project_name: Optional[str] = None
    period: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    strengths: Optional[List[dict]] = None

# Cover Letter Schemas
class CoverLetterBase(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    recruitment_id: Optional[int] = None
    processing_status: Optional[str] = "PENDING"

class CoverLetterItemBase(BaseModel):
    question: str
    content: Optional[str] = None
    category: Optional[str] = None
    # hint removed
    max_length: Optional[int] = 1000  # 글자 수 제한
    key_points: Optional[List[str]] = None
    suggested_improvements: Optional[List[str]] = None

class CoverLetterItemCreate(CoverLetterItemBase):
    pass

class CoverLetterItem(CoverLetterItemBase):
    id: int
    cover_letter_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class CoverLetterItemDetail(CoverLetterItem):
    """Refined item with analysis"""
    pass

class CoverLetterCreate(CoverLetterBase):
    user_id: int
    questions: Optional[List[CoverLetterItemCreate]] = []

class CoverLetterSummary(CoverLetterBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Legacy alias for backward compatibility
class CoverLetter(CoverLetterSummary):
    pass

class CoverLetterVersion(BaseModel):
    id: int
    cover_letter_id: int
    title: Optional[str] = None
    items_snapshot: List[dict] # Snapshot of questions and contents
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CoverLetterDetail(CoverLetterSummary):
    gap_analysis: Optional[dict] = None
    job_analysis: Optional[dict] = None
    items: List[CoverLetterItem] = []

class CoverLetterListResponse(BaseModel):
    items: List[CoverLetterSummary]
    model_config = ConfigDict(from_attributes=True)

class CoverLetterCreateRequest(CoverLetterBase):
    questions: Optional[List[CoverLetterItemCreate]] = []

class CoverLetterUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    questions: Optional[List[CoverLetterItemCreate]] = None

# AI Related Schemas
class PortfolioAnalyzeRequest(BaseModel):
    source: str
    type: str  # github, link, file, notion

class CoverLetterGenerateRequest(BaseModel):
    recruit_id: int
    cover_letter_id: Optional[int] = None
    portfolio_ids: List[int] = []
    questions: List[str]
    tone: str = "professional"
    mode: str = "full" # 'full' or 'outline'
    subheading: bool = False
    temperature: float = 0.0

class RecruitmentDetail(Recruitment):
    # If we need recommendations or letters in detail view
    pass

# Recommendation Schemas
class RecommendationBase(BaseModel):
    recruitment_id: int
    rank_order: int
    reason: Optional[List[str]] = []

class Recommendation(RecommendationBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RecommendationListResponse(BaseModel):
    items: List[Recommendation]
    model_config = ConfigDict(from_attributes=True)

# Notification Schemas
class NotificationBase(BaseModel):
    title: str
    message: str
    is_read: bool = False
    link: Optional[str] = None

class Notification(NotificationBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NotificationListResponse(BaseModel):
    items: List[Notification]
    unread_count: int
    model_config = ConfigDict(from_attributes=True)
