import logging
from typing import List, Dict, Optional
from datetime import date
from langchain_core.documents import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from common.models import Recruitment
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
        Processing is done individually per item to ensure robustness.
        """
        import datetime
        added_count = 0
        
        for item in data_list:
            try:
                # 1. SQL DB Insertion/Update
                # Check if exists by link (primary unique constraint)
                link = item.get('link')
                db_recruit = None
                if link:
                    stmt = select(Recruitment).where(Recruitment.link == link)
                    result = await db.execute(stmt)
                    db_recruit = result.scalar_one_or_none()
                
                # Format dates
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

                # Fix: Check and swap if start_date > deadline
                if start_date_obj and deadline_date and start_date_obj > deadline_date:
                    logger.warning(f"Swapping start_date ({start_date_obj}) and deadline ({deadline_date}) for {link or 'item'}")
                    start_date_obj, deadline_date = deadline_date, start_date_obj

                if not db_recruit:
                    db_recruit = Recruitment(
                        title=item.get('title'),
                        company=item.get('company'),
                        link=link,
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
                        tags=item.get('tags', []),
                        questions=item.get('questions')
                    )
                    db.add(db_recruit)
                else:
                    # Update existing record
                    db_recruit.title = item.get('title', db_recruit.title)
                    db_recruit.company = item.get('company', db_recruit.company)
                    db_recruit.deadline = deadline_date or db_recruit.deadline
                    db_recruit.tags = item.get('tags', db_recruit.tags)
                    db_recruit.questions = item.get('questions', db_recruit.questions)
                
                await db.flush() 
                
                # 2. Generate Embedding for 1:1 Storage (Only if missing)
                if db_recruit.embedding is None:
                    try:
                        doc = self.preprocess_recruitment(item)
                        embedding = await self.vector_store.get_embedding(doc.page_content)
                        db_recruit.embedding = embedding
                        logger.info(f"Generated embedding for recruitment {db_recruit.id}")
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for recruitment {db_recruit.id}: {e}")
                
                # Commit each item individually
                await db.commit()
                added_count += 1
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to process recruitment item {item.get('link') or item.get('title')}: {e}")
                continue
                
        return added_count

    async def search_by_vector(self, db: AsyncSession, embedding: List[float], k: int = 5):
        """
        Search for relevant recruitments using a pre-calculated embedding vector.
        Returns a list of Documents with 'distance' in metadata.
        """
        from sqlalchemy import text
        import json
        
        # SQL for cosine similarity search
        stmt = text("""
            SELECT id, title, company, category, location, start_date, deadline, 
                   key_responsibilities, required_qualifications, preferred_qualifications,
                   embedding <=> :emb as distance
            FROM recruitments
            WHERE embedding IS NOT NULL
              AND (deadline IS NULL OR deadline >= CURRENT_DATE)
              AND created_at >= (CURRENT_DATE - INTERVAL '1 month')
            ORDER BY distance
            LIMIT :k
        """)
        
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
                "distance": float(row.distance)
            }
            doc = Document(
                page_content=f"{row.key_responsibilities}\n{row.required_qualifications}", 
                metadata=metadata
            )
            matches.append(doc)
        return matches

    def _kiwi_tokenize(self, text: str) -> List[str]:
        """
        Extract nouns using Kiwi for better BM25 matching.
        """
        try:
            from kiwipiepy import Kiwi
            if not hasattr(self, '_kiwi'):
                self._kiwi = Kiwi()
            
            result = self._kiwi.tokenize(text)
            return [t.form for t in result if t.tag in ['NNG', 'NNP', 'SL']]
        except Exception as e:
            logger.warning(f"Kiwi tokenization failed, falling back to split: {e}")
            return text.split()

    async def search_hybrid(self, db: AsyncSession, query: str, k: int = 5):
        """
        Hybrid Search: Combines Vector search and Keyword search (BM25).
        Fuses results using Reciprocal Rank Fusion (RRF).
        """
        from sqlalchemy import select
        from langchain_community.retrievers import BM25Retriever
        import numpy as np

        # 1. Vector Search
        query_emb = await self.vector_store.get_embedding(query)
        # Get more candidates for fusion
        vector_results = await self.search_by_vector(db, query_emb, k=k*3)
        
        # 2. BM25 Search
        # Fetch active recruitments (not expired, within 1 month)
        stmt = (
            select(Recruitment)
            .where(
                Recruitment.embedding.isnot(None),
                sa.or_(Recruitment.deadline.is_(None), Recruitment.deadline >= sa.func.current_date()),
                Recruitment.created_at >= (sa.func.current_date() - sa.text("INTERVAL '1 month'"))
            )
        )
        res = await db.execute(stmt)
        all_recruits = res.scalars().all()
        
        if not all_recruits:
            return vector_results[:k]
            
        corpus_docs = []
        for r in all_recruits:
            content = f"{r.title} {r.key_responsibilities} {r.required_qualifications} {r.preferred_qualifications}"
            metadata = {
                "id": r.id,
                "title": r.title,
                "company": r.company
            }
            corpus_docs.append(Document(page_content=content, metadata=metadata))
            
        bm25_retriever = BM25Retriever.from_documents(
            corpus_docs, 
            preprocess_func=self._kiwi_tokenize
        )
        bm25_retriever.k = k * 3
        bm25_results = bm25_retriever.invoke(query)
        
        # 3. Reciprocal Rank Fusion (RRF)
        # score = sum(1 / (rank + 60))
        fused_scores = {} # id -> score
        doc_map = {} # id -> Document
        
        for rank, doc in enumerate(vector_results):
            rid = doc.metadata['id']
            fused_scores[rid] = fused_scores.get(rid, 0) + 1.0 / (rank + 60)
            doc_map[rid] = doc
            
        for rank, doc in enumerate(bm25_results):
            rid = doc.metadata['id']
            fused_scores[rid] = fused_scores.get(rid, 0) + 1.0 / (rank + 60)
            # If not in doc_map, we need to fetch full metadata or use it as is
            # For simplicity, if it's in vector results we have full info.
            # If not, let's fetch it from the database or use the corpus version.
            if rid not in doc_map:
                # Find the original record
                orig = next((r for r in all_recruits if r.id == rid), None)
                if orig:
                    metadata = {
                        "id": orig.id,
                        "title": orig.title,
                        "company": orig.company,
                        "category": orig.category,
                        "location": orig.location,
                        "start_date": orig.start_date.isoformat() if orig.start_date else None,
                        "deadline": orig.deadline.isoformat() if orig.deadline else None,
                        "key_responsibilities": orig.key_responsibilities,
                        "required_qualifications": orig.required_qualifications,
                        "unique_id": f"{orig.company}_{orig.title}",
                        "distance": 1.0 # default distance for BM25-only
                    }
                    doc_map[rid] = Document(page_content=orig.key_responsibilities or "", metadata=metadata)

        # Sort by fused score
        final_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)[:k]
        
        return [doc_map[rid] for rid in final_ids]

    async def search(self, db: AsyncSession, query: str, k: int = 5):
        """
        Default search now uses Hybrid Search for better accuracy.
        """
        return await self.search_hybrid(db, query, k)
