from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, JSON, Table, Enum as SqEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.database import Base
import enum

class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # User Profile Fields (extracted from portfolios)
    profile_summary = Column(Text, nullable=True)  # Overall summary across all projects
    desired_job_title = Column(String, nullable=True)  # Desired job position

    portfolios = relationship("Portfolio", back_populates="owner")
    cover_letters = relationship("CoverLetter", back_populates="owner")

class Recruitment(Base):
    __tablename__ = "recruitments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    link = Column(String, nullable=True)
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
    tags = Column(JSON, nullable=True)  # List of strings
    embedding = Column(Vector(1024), nullable=True)  # Unified 1:1 embedding storage
    view_count = Column(Integer, default=0) # View count for popularity sorting
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cover_letters = relationship("CoverLetter", back_populates="recruitment")
    recommendations = relationship("Recommendation", back_populates="recruitment", cascade="all, delete-orphan")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # github, link, file, notion
    source_url = Column(String, nullable=True)
    content = Column(Text, nullable=True) # Raw extracted text
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
    embedding = Column(Vector(1024), nullable=True)  # Native vector storage (List of floats)

    owner = relationship("User", back_populates="portfolios")
    job_queries = relationship("PortfolioJobQuery", back_populates="portfolio", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="portfolio", cascade="all, delete-orphan")

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

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    recruitment_id = Column(Integer, ForeignKey("recruitments.id"), nullable=False)
    rank_order = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    portfolio = relationship("Portfolio", back_populates="recommendations")
    recruitment = relationship("Recruitment", back_populates="recommendations")
