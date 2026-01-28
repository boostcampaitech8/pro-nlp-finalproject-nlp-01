import os
import requests
from typing import List, Optional

class NaverClovaEmbeddings:
    """
    Custom LangChain Embeddings implementation for Naver Clova Studio Embedding v2.
    """
    def __init__(self, api_key: str, base_url: str = None):
        from langchain_core.embeddings import Embeddings
        # We don't strictly need to inherit if we implement the protocol
        self.api_key = api_key
        # Default to Clova Studio standard endpoint if not provided
        self.base_url = base_url or "https://clovastudio.stream.ntruss.com"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {"text": text}
        endpoint = f"{self.base_url.rstrip('/')}/v1/api-tools/embedding/v2"
        
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        
        res_json = response.json()
        if res_json.get("status", {}).get("code") == "20000":
             return res_json["result"]["embedding"]
        else:
             raise ValueError(f"Naver Clova API Error: {res_json}")

class SupabaseVectorStore:
    """
    Manages embedding storage in Supabase using PGVector.
    Uses Naver HyperCLOVA X (Clova Studio) for embeddings.
    """

    def __init__(self, table_name: str = "portfolio_embeddings"):
        raw_url = os.getenv("DATABASE_URL")
        if not raw_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Handle legacy 'postgres://' prefix
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql://", 1)
            
        # Standardize for PGVector async usage
        if "postgresql+asyncpg://" not in raw_url:
            self.connection_string = raw_url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            self.connection_string = raw_url
        
        self.table_name = table_name
        self._embedding_model = None
        self._vector_store = None
        
        # NCP Clova Studio Credentials
        self.ncp_api_key = os.getenv("NCP_CLOVASTUDIO_API_KEY")
        self.ncp_base_url = os.getenv("NCP_CLOVASTUDIO_BASE_URL")
        
        if not self.ncp_api_key:
             print("Warning: NCP_CLOVASTUDIO_API_KEY not set. Embedding will fail.")

    @property
    def embedding_model(self):
        if not self._embedding_model:
            # API-based embedding: Zero local memory/CPU overhead
            self._embedding_model = NaverClovaEmbeddings(
                api_key=self.ncp_api_key,
                base_url=self.ncp_base_url
            )
        return self._embedding_model

    @property
    def vector_store(self):
        if not self._vector_store:
            from langchain_postgres import PGVector
            self._vector_store = PGVector(
                embeddings=self.embedding_model,
                collection_name=self.table_name,
                connection=self.connection_string,
                use_jsonb=True,
            )
        return self._vector_store

    async def add_documents(self, documents):
        """
        Adds documents to the Supabase vector store.
        """
        from langchain_core.documents import Document
        # documents is List[Document]
        await self.vector_store.aadd_documents(documents)

    async def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Performs similarity search.
        """
        return await self.vector_store.asimilarity_search(query, k=k)
