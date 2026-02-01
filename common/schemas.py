from pydantic import BaseModel, EmailStr, ConfigDict, Field
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
    tags: Optional[List[str]] = None
    reason: Optional[str] = None
    view_count: Optional[int] = 0

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

# Portfolio Schemas
class PortfolioBase(BaseModel):
    type: str
    source_url: Optional[str] = None
    content: Optional[str] = None
    project_name: Optional[str] = None
    period: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None

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

class PortfolioUpdateRequest(BaseModel):
    type: Optional[str] = None
    source_url: Optional[str] = None
    content: Optional[str] = None
    project_name: Optional[str] = None
    period: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None

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
    key_points: Optional[List[str]] = None
    suggested_improvements: Optional[List[str]] = None

class CoverLetterItemCreate(CoverLetterItemBase):
    pass

class CoverLetterItem(CoverLetterItemBase):
    id: int
    cover_letter_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class CoverLetterCreate(CoverLetterBase):
    user_id: int

class CoverLetterSummary(CoverLetterBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Legacy alias for backward compatibility
class CoverLetter(CoverLetterSummary):
    pass

class CoverLetterDetail(CoverLetterSummary):
    gap_analysis: Optional[dict] = None
    job_analysis: Optional[dict] = None
    items: List[CoverLetterItem] = []

class CoverLetterListResponse(BaseModel):
    items: List[CoverLetterSummary]
    model_config = ConfigDict(from_attributes=True)

class CoverLetterCreateRequest(CoverLetterBase):
    pass

class CoverLetterUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

# AI Related Schemas
class PortfolioAnalyzeRequest(BaseModel):
    source: str
    type: str  # github, link, file, notion

class CoverLetterGenerateRequest(BaseModel):
    recruit_id: int
    portfolio_ids: List[int] = []
    questions: List[str]
    tone: str = "professional"
    mode: str = "full" # 'full' or 'outline'

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
