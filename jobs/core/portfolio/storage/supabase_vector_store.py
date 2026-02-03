import os
import uuid
import json
import requests
from sqlalchemy import create_engine, text
from typing import List, Dict
from langchain_core.documents import Document
from common.config import settings

class ManualRAG:
    def __init__(self, collection_name="portfolio_embeddings"):
        url = settings.DATABASE_URL
        # Ensure we use synchronous driver for this part
        if "postgresql+asyncpg://" in url:
            url = url.replace("postgresql+asyncpg://", "postgresql://")
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
            
        from sqlalchemy.pool import NullPool
        self.engine = create_engine(url, poolclass=NullPool)
        self.collection_name = collection_name
        self.api_key = settings.NCP_CLOVASTUDIO_API_KEY

    def get_embedding(self, text_content):
        base_url = settings.NCP_CLOVASTUDIO_BASE_URL.strip()
        # Ensure it doesn't end with slash
        if base_url.endswith("/"):
            base_url = base_url[:-1]
            
        url = f"{base_url}/v1/api-tools/embedding/v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            # "X-NCP-CLOVASTUDIO-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        res = requests.post(
            url,
            headers=headers,
            json={"text": text_content}
        )
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Log the detailed response for debugging
            raise Exception(f"Embedding API Failed: {e}, Response: {res.text}")

        return res.json()["result"]["embedding"]

    def add_document(self, content, metadata):
        embedding = self.get_embedding(content)
        with self.engine.connect() as conn:
            conn = conn.execution_options(compiled_cache=None)
            with conn.begin():
                # Get collection ID
                res = conn.execute(text("SELECT uuid FROM langchain_pg_collection WHERE name = :name"), {"name": self.collection_name})
                row = res.fetchone()
                if row:
                    cid = row[0]
                else:
                    cid = str(uuid.uuid4())
                    conn.execute(text("INSERT INTO langchain_pg_collection (uuid, name) VALUES (:uuid, :name)"), {"uuid": cid, "name": self.collection_name})
                
                # Insert embedding
                conn.execute(
                    text("INSERT INTO langchain_pg_embedding (id, collection_id, embedding, document, cmetadata) VALUES (:id, :cid, :emb, :doc, :meta)"),
                    {"id": str(uuid.uuid4()), "cid": cid, "emb": embedding, "doc": content, "meta": json.dumps(metadata)}
                )

    def similarity_search(self, query, k=4):
        query_emb = self.get_embedding(query)
        with self.engine.connect() as conn:
            conn = conn.execution_options(compiled_cache=None)
            # orden by cosine distance (<=>)
            res = conn.execute(
                text("""
                    SELECT document, e.cmetadata 
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                    WHERE c.name = :name
                    ORDER BY embedding <=> :emb
                    LIMIT :k
                """),
                {"name": self.collection_name, "emb": str(query_emb), "k": k}
            )
            return [{"content": row[0], "metadata": row[1]} for row in res]

# Integration for backend
class SupabaseVectorStore:
    def __init__(self, table_name="portfolio_embeddings"):
        self.rag = ManualRAG(collection_name=table_name)
    
    async def add_documents(self, documents):
        import asyncio
        loop = asyncio.get_event_loop()
        for doc in documents:
            await loop.run_in_executor(None, self.rag.add_document, doc.page_content, doc.metadata)
            
    async def similarity_search(self, query, k=4):
        import asyncio
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, self.rag.similarity_search, query, k)
        return [Document(page_content=r["content"], metadata=r["metadata"]) for r in results]

    async def get_embedding(self, text: str) -> List[float]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.rag.get_embedding, text)
