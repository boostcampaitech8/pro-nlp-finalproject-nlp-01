from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, JSON, Float, Table, Enum as SqEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from common.database import Base
import enum

class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # User Profile Fields (extracted from portfolios)
    profile_summary = Column(Text, nullable=True)  # Overall summary across all projects
    desired_job_title = Column(String, nullable=True)  # Desired job position

    portfolios = relationship("Portfolio", back_populates="owner")
    cover_letters = relationship("CoverLetter", back_populates="owner")
    integrations = relationship("UserIntegration", back_populates="user", cascade="all, delete-orphan")

class Recruitment(Base):
    __tablename__ = "recruitments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    company = Column(String, nullable=False, index=True)
    link = Column(String, nullable=True, unique=True, index=True)
    start_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    location = Column(String, nullable=True)
    experience = Column(String, nullable=True)
    education = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    category = Column(String, nullable=True) # Merged job_sector into category
    key_responsibilities = Column(Text, nullable=True)
    required_qualifications = Column(Text, nullable=True)
    preferred_qualifications = Column(Text, nullable=True)
    company_description = Column(Text, nullable=True)  # 기업 인재상/핵심 가치
    embedding = Column(Vector(1024), nullable=True)  # Unified 1:1 embedding storage
    tags = Column(JSON, nullable=True) # Direct JSON storage for tech stack tags
    view_count = Column(Integer, default=0) # View count for popularity sorting
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cover_letters = relationship("CoverLetter", back_populates="recruitment")
    recommendations = relationship("Recommendation", back_populates="recruitment", cascade="all, delete-orphan")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # github, link, file, notion
    source_url = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Processing Status
    processing_status = Column(SqEnum(ProcessingStatus), default=ProcessingStatus.PENDING)
    
    # Project Details (Flattened)
    project_name = Column(String, nullable=False)  # Now required since title is removed
    period = Column(String, nullable=True)
    role = Column(String, nullable=True)
    description = Column(Text, nullable=True) # Refined Description for Embedding
    tech_stack = Column(JSON, nullable=True) # List of strings
    strengths = Column(JSON, nullable=True) # List of StrengthItem dicts

    owner = relationship("User", back_populates="portfolios")
    job_queries = relationship("PortfolioJobQuery", back_populates="portfolio", cascade="all, delete-orphan")
    chunks = relationship("PortfolioChunk", back_populates="portfolio", cascade="all, delete-orphan")

class PortfolioChunk(Base):
    __tablename__ = "portfolio_chunks"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    chunk_content = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    portfolio = relationship("Portfolio", back_populates="chunks")

class PortfolioJobQuery(Base):
    __tablename__ = "portfolio_job_queries"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    type = Column(String, nullable=True) # A, B, C
    query_text = Column(String, nullable=True)
    embedding = Column(Vector(1024), nullable=True) # Pre-calculated embedding
    evidence = Column(JSON, nullable=True) # List of strings

    portfolio = relationship("Portfolio", back_populates="job_queries")

class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    recruitment_id = Column(Integer, ForeignKey("recruitments.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="cover_letters")
    recruitment = relationship("Recruitment", back_populates="cover_letters")
    items = relationship("CoverLetterItem", back_populates="cover_letter", cascade="all, delete-orphan")
    
    # Analysis Results
    processing_status = Column(SqEnum(ProcessingStatus), default=ProcessingStatus.PENDING)
    gap_analysis = Column(JSON, nullable=True)
    job_analysis = Column(JSON, nullable=True)

class CoverLetterItem(Base):
    __tablename__ = "cover_letter_items"
    
    id = Column(Integer, primary_key=True, index=True)
    cover_letter_id = Column(Integer, ForeignKey("cover_letters.id"), nullable=False)
    
    question = Column(Text, nullable=False)
    content = Column(Text, nullable=True)
    category = Column(String, nullable=True) # motivation, growth, capability, etc.
    hint = Column(Text, nullable=True)  # 작성 힌트/가이드
    max_length = Column(Integer, nullable=True, default=1000)  # 글자 수 제한
    
    # AI Analysis
    key_points = Column(JSON, nullable=True) # List of strings
    suggested_improvements = Column(JSON, nullable=True) # List of strings
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    cover_letter = relationship("CoverLetter", back_populates="items")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recruitment_id = Column(Integer, ForeignKey("recruitments.id"), nullable=False)
    rank_order = Column(Integer, nullable=False)
    reason = Column(JSON, nullable=True) # List of strings
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User") # Optional: add back_populates if needed
    recruitment = relationship("Recruitment", back_populates="recommendations")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    link = Column(String, nullable=True) # Deep link to Portfolio/CoverLetter
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)  # 'github', 'notion'
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    provider_user_id = Column(String, nullable=True) # ID from the provider
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="integrations")
