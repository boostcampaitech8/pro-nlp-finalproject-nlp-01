import json
import logging
from typing import List
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from common import models
from jobs.core.cover_letter.config import SEARCH_TOP_K

logger = logging.getLogger(__name__)

class PGHybridRetriever:
    """
    Hybrid Retriever combining BM25 (Keyword) and Vector Search (Semantic)
    using stored embeddings in PostgreSQL.
    """
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.documents = [] # (id, text, embedding, metadata)
        self.bm25 = None
        
    async def load_documents(self):
        """Load user's portfolios and recruitment data for context"""
        # Fetch Portfolios
        stmt = select(models.Portfolio).where(models.Portfolio.user_id == self.user_id)
        result = await self.db.execute(stmt)
        portfolios = result.scalars().all()
        
        for p in portfolios:
            # Combine relevant text fields
            content = f"{p.project_name}\n{p.description or ''}\n{p.role or ''}\n{p.content or ''}"
            
            # Using stored embedding if available, otherwise skip vector part for this doc
            embedding = p.embedding
            if isinstance(embedding, str):
                try:
                    embedding = json.loads(embedding)
                except:
                    embedding = None
            
            self.documents.append({
                "id": p.id,
                "text": content,
                "embedding": embedding,
                "metadata": {
                    "source": "portfolio",
                    "project_name": p.project_name,
                    "role": p.role,
                    "stack": p.tech_stack
                }
            })
            
        # Initialize BM25
        if self.documents:
            tokenized_corpus = [doc["text"].lower().split() for doc in self.documents]
            self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, query_embedding: List[float] = None, top_k: int = SEARCH_TOP_K) -> List[Document]:
        if not self.documents:
            return []

        # 1. BM25 Scores
        tokenized_query = query.lower().split()
        if self.bm25:
            bm25_scores = self.bm25.get_scores(tokenized_query)
        else:
            bm25_scores = [0.0] * len(self.documents)
        
        # Normalize BM25 (Min-Max)
        if len(bm25_scores) > 0:
            min_s, max_s = min(bm25_scores), max(bm25_scores)
            if max_s > min_s:
                bm25_scores = [(s - min_s) / (max_s - min_s) for s in bm25_scores]
            else:
                bm25_scores = [1.0] * len(bm25_scores) # All same

        # 2. Vector Scores (Cosine Similarity)
        vector_scores = [0.0] * len(self.documents)
        if query_embedding is not None:
            q_vec = np.array(query_embedding)
            norm_q = np.linalg.norm(q_vec)
            
            for i, doc in enumerate(self.documents):
                if doc["embedding"] is not None:
                    d_vec = np.array(doc["embedding"])
                    norm_d = np.linalg.norm(d_vec)
                    if norm_q > 0 and norm_d > 0:
                        cos_sim = np.dot(q_vec, d_vec) / (norm_q * norm_d)
                        vector_scores[i] = (cos_sim + 1) / 2 # Normalize -1~1 to 0~1
        
        # 3. Hybrid Combination
        # Weight: BM25 0.3, Vector 0.7 (Adjustable)
        final_scores = []
        for i in range(len(self.documents)):
            score = 0.3 * bm25_scores[i] + 0.7 * vector_scores[i]
            final_scores.append((score, self.documents[i]))
            
        final_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Convert to LangChain Documents
        results = []
        for score, doc_data in final_scores[:top_k]:
            results.append(Document(
                page_content=doc_data["text"],
                metadata=doc_data["metadata"]
            ))
            
        return results
