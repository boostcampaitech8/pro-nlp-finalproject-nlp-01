import logging
from typing import List, Dict, Optional
from datetime import date
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from common.models import Recruitment, Tag
from jobs.core.portfolio.storage.supabase_vector_store import SupabaseVectorStore

logger = logging.getLogger(__name__)


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("\x00", "")

class RecruitIndexer:
    """
    Handles indexing of recruitment data into the Supabase Vector Store.
    Adapted from llm-pipeline/recruit/src/recruit_indexer.py
    """
    def __init__(self, collection_name: str = "recruitment_embeddings"):
        self.vector_store = SupabaseVectorStore(table_name=collection_name)

    def preprocess_recruitment(self, data: Dict) -> Document:
        """
        Preprocesses raw recruitment JSON into a LangChain Document.
        
        Policy:
        1. Embedding Content: Concatenate 'key_responsibilities', 'required_qualifications', 
           'preferred_qualifications'.
        2. Metadata: Store ALL fields from the input JSON.
        3. Unique ID: Use 'company' + 'title'.
        """
        content_parts = [
            f"회사: {data.get('company', '')}",
            f"제목: {data.get('title', '')}",
            f"카테고리: {data.get('category', '')}",
            f"경험 수준: {data.get('experience', '')}",
            f"학력: {data.get('education', '')}",
            f"고용 형태: {data.get('employment_type', '')}",
            f"급여: {data.get('salary', '')}",
            f"주요 업무: {data.get('key_responsibilities', '')}",
            f"자격 요건: {data.get('required_qualifications', '')}",
            f"우대 사항: {data.get('preferred_qualifications', '')}",
        ]
        content_parts = [sanitize_text(p) for p in content_parts]
        page_content = " ".join([p for p in content_parts if p.split(": ")[1]])
        
        # 2. Metadata (All fields)
        # ChromaDB/Supabase requires metadata values to be str, int, float, or bool.
        metadata = {}
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, list):
                metadata[key] = ", ".join([str(v) for v in value])
            elif isinstance(value, (str, int, float, bool)):
                metadata[key] = value
            else:
                metadata[key] = str(value)
        
        # Add a source for generic tracking
        metadata["source"] = "crawler"
        
        return Document(page_content=page_content, metadata=metadata)

    async def add_recruitments(self, db: AsyncSession, data_list: List[Dict]):
        """
        Processes and adds multiple recruitment items to BOTH SQL DB and vector store.
        """
        import datetime
        
        for item in data_list:
            # 1. SQL DB Insertion/Update
            # Check if exists by title and company
            stmt = select(Recruitment).where(
                Recruitment.title == item.get('title'),
                Recruitment.company == item.get('company')
            )
            result = await db.execute(stmt)
            db_recruit = result.scalar_one_or_none()
            
            # Format deadline and start_date
            deadline_val = item.get('deadline')
            deadline_date = None
            if deadline_val and isinstance(deadline_val, str):
                 try: deadline_date = datetime.date.fromisoformat(deadline_val)
                 except: pass
            
            start_date_val = item.get('start_date')
            start_date_obj = None
            if start_date_val and isinstance(start_date_val, str):
                 try: start_date_obj = datetime.date.fromisoformat(start_date_val)
                 except: pass

            if not db_recruit:
                db_recruit = Recruitment(
                    title=item.get('title'),
                    company=item.get('company'),
                    link=item.get('link'),
                    start_date=start_date_obj,
                    deadline=deadline_date,
                    location=item.get('location'),
                    experience=item.get('experience'),
                    education=item.get('education'),
                    employment_type=item.get('employment_type'),
                    salary=item.get('salary'),
                    category=item.get('category'),
                    key_responsibilities=sanitize_text(item.get('key_responsibilities')),
                    required_qualifications=sanitize_text(item.get('required_qualifications')),
                    preferred_qualifications=sanitize_text(item.get('preferred_qualifications')),
                    tags=item.get('tags', []) # Directly use JSON list
                )
                db.add(db_recruit)
            else:
                # Update existing
                db_recruit.link = item.get('link', db_recruit.link)
                db_recruit.deadline = deadline_date or db_recruit.deadline
                db_recruit.tags = item.get('tags', db_recruit.tags)
            
            await db.flush() # Get the ID for metadata
            
            # 2. Generate Embedding for 1:1 Storage (Only if new or missing embedding)
            if not db_recruit.embedding:
                try:
                    doc = self.preprocess_recruitment(item)
                    embedding = await self.vector_store.get_embedding(doc.page_content)
                    db_recruit.embedding = embedding
                    logger.info(f"Generated embedding for recruitment {db_recruit.id}")
                except Exception as e:
                    logger.error(f"Failed to generate embedding for recruitment {db_recruit.id}: {e}")
            else:
                logger.info(f"Skipping embedding generation for existing recruitment {db_recruit.id}")
            
        await db.commit()
        return len(data_list)

    async def search_by_vector(self, db: AsyncSession, embedding: List[float], k: int = 5):
        """
        Search for relevant recruitments using a pre-calculated embedding vector.
        """
        from sqlalchemy import text
        
        # SQL for cosine similarity search
        stmt = text("""
            SELECT id, title, company, category, location, start_date, deadline, 
                   key_responsibilities, required_qualifications, preferred_qualifications,
                   embedding <=> :emb as distance
            FROM recruitments
            WHERE embedding IS NOT NULL
            ORDER BY distance
            LIMIT :k
        """)
        
        # pgvector expects string representation of vector like '[0.1, 0.2, ...]'
        import json
        # Ensure it's a list first (handle numpy arrays)
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        embedding_str = json.dumps(embedding)
        
        result = await db.execute(stmt, {"emb": embedding_str, "k": k})
        rows = result.all()
        
        matches = []
        for row in rows:
            metadata = {
                "id": row.id,
                "title": row.title,
                "company": row.company,
                "category": row.category,
                "location": row.location,
                "start_date": row.start_date.isoformat() if row.start_date else None,
                "deadline": row.deadline.isoformat() if row.deadline else None,
                "key_responsibilities": row.key_responsibilities,
                "required_qualifications": row.required_qualifications,
                "preferred_qualifications": row.preferred_qualifications,
                "unique_id": f"{row.company}_{row.title}",
                "distance": row.distance
            }
            doc = Document(
                page_content=f"{row.key_responsibilities}\n{row.required_qualifications}", 
                metadata=metadata
            )
            matches.append(doc)
        return matches

    async def search(self, db: AsyncSession, query: str, k: int = 5):
        """
        Search for relevant recruitments by generating embedding for query text first.
        """
        query_emb = await self.vector_store.get_embedding(query)
        return await self.search_by_vector(db, query_emb, k)
