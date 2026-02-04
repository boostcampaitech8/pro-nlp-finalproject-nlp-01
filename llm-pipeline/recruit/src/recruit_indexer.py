import os
import shutil
from typing import List, Dict, Optional
from pathlib import Path

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

try:
    from kiwipiepy import Kiwi
    KIWI_AVAILABLE = True
except ImportError:
    KIWI_AVAILABLE = False
    print("Warning: kiwipiepy is not installed. Falling back to simple split.")

# Configuration constants
# Adjust these paths as needed, assuming we run from project root or relative to this file
CURRENT_DIR = Path(__file__).resolve().parent
RECRUIT_ROOT = CURRENT_DIR.parent
PERSIST_DIR = RECRUIT_ROOT / "data" / "chroma_db_new"
EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"

class RecruitIndexer:
    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or str(PERSIST_DIR)
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.kiwi = None
        if KIWI_AVAILABLE:
            try:
                self.kiwi = Kiwi()
            except Exception as e:
                print(f"Kiwi initialization failed: {e}")
        
    def preprocess_recruitment(self, data: Dict) -> Document:
        """
        Preprocesses raw recruitment JSON into a LangChain Document.
        
        Policy:
        1. Embedding Content: Concatenate 'key_responsibilities', 'required_qualifications', 
           'preferred_qualifications'.
        2. Metadata: Store ALL fields from the input JSON.
        3. Unique ID: Use 'link' field.
        """
        # 1. Construct Embedding Content
        # We handle missing fields gracefully by defaulting to empty strings
        content_parts = [
            f"주요 업무: {data.get('key_responsibilities', '')}",
            f"자격 요건: {data.get('required_qualifications', '')}",
            f"우대 사항: {data.get('preferred_qualifications', '')}"
        ]
        page_content = " ".join(content_parts)
        
        # 2. Metadata (All fields)
        # ChromaDB requires metadata values to be str, int, float, or bool.
        # We must convert lists to strings.
        metadata = {}
        for key, value in data.items():
            if isinstance(value, list):
                metadata[key] = ", ".join([str(v) for v in value])
            else:
                metadata[key] = value
        
        # 3. Create Document
        # Ideally we pass 'id' to the vectorstore add_documents method, 
        # but storing it in metadata/object is also good practice.
        return Document(page_content=page_content, metadata=metadata)

    def _kiwi_tokenize(self, text: str) -> List[str]:
        """
        Kiwi 형태소 분석기를 사용하여 명사(NNG, NNP, SL)만 추출합니다.
        BM25 검색의 정확도를 높이기 위해 사용됩니다.
        """
        if not self.kiwi:
            return text.split() # Fallback

        tokens = []
        try:
            # tokenize returns list of Token(form, tag, start, len)
            matches = self.kiwi.tokenize(text, normalize_coda=True)
            for token in matches:
                # NNG: 일반 명사, NNP: 고유 명사, SL: 외국어(기술명 등)
                if token.tag in ['NNG', 'NNP', 'SL']:
                    tokens.append(token.form)
        except Exception:
             return text.split()
        
        return tokens if tokens else text.split() # Return split if no nouns found (e.g. only particles)

    def create_vectorstore(self, data_list: List[Dict], collection_name: str = "recruit_collection"):
        """
        Creates or updates a Chroma vectorstore from a list of recruitment dictionaries.
        """
        documents = []
        ids = []
        
        for item in data_list:
            doc = self.preprocess_recruitment(item)
            
            # Generate Unique ID: company + title
            company = item.get('company', 'UnknownCompany')
            title = item.get('title', 'UnknownTitle')
            base_id = f"{company}_{title}"
            
            # Ensure ID is unique
            unique_id = base_id
            counter = 1
            while unique_id in ids:
                counter += 1
                unique_id = f"{base_id}_{counter}"
            
            # 검색 시 바로 꺼내 쓸 수 있도록 메타데이터에도 ID 저장
            doc.metadata['unique_id'] = unique_id
            
            documents.append(doc)
            ids.append(unique_id)
            
        # Ensure persist directory exists
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Initialize Chroma
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=self.persist_dir
        )
        
        # Add documents with custom IDs
        vectorstore.add_documents(documents=documents, ids=ids)
        
        return vectorstore

    def search_recruitments(self, query: str, k: int = 5, collection_name: str = "recruit_collection"):
        """
        Simple search wrapper for verification.
        """
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=self.persist_dir
        )
        
        return vectorstore.similarity_search(query, k=k)

    def search_recruitments_with_scores(self, query: str, k: int = 5, collection_name: str = "recruit_collection"):
        """
        Search with similarity scores (lower distance is better for Chroma/L2).
        Returns List[Tuple[Document, float]]
        """
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=self.persist_dir
        )
        
        return vectorstore.similarity_search_with_score(query, k=k)

    def get_all_documents(self, collection_name: str = "recruit_collection"):
        """
        Retrieves all documents stored in the vectorstore.
        Returns a dictionary containing 'ids', 'metadatas', and 'documents' (page_content).
        """
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=self.persist_dir
        )
        return vectorstore.get()

    def search_bm25(self, query: str, k: int = 10, collection_name: str = "recruit_collection"):
        """
        Pure BM25 search with Kiwi tokenization.
        """
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=self.persist_dir
        )
        
        all_data = vectorstore.get()
        documents = []
        if all_data['documents']:
            for content, metadata in zip(all_data['documents'], all_data['metadatas']):
                documents.append(Document(page_content=content, metadata=metadata))
        
        if not documents:
            return []

        bm25_retriever = BM25Retriever.from_documents(
            documents,
            preprocess_func=self._kiwi_tokenize
        )
        bm25_retriever.k = k
        return bm25_retriever.invoke(query)

    def search_hybrid(self, query: str, keyword_query: Optional[str] = None, k: int = 5, collection_name: str = "recruit_collection") -> List[tuple[Document, float]]:
        """
        Hybrid Search: Combines Vector search (Chroma) and Keyword search (BM25).
        Returns a list of (Document, score) tuples.
        Score is the Vector Distance (L2) - Lower is better.
        """
        import numpy as np

        # 1. Prepare Vector Store
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=self.persist_dir
        )
        
        # 2. Vector Search (Get scores)
        # Chroma L2: Lower is better
        vector_results = vectorstore.similarity_search_with_score(query, k=k)
        
        # 3. BM25 Search
        # Need all docs for BM25
        # We also need embeddings to calculate scores for BM25-only results
        all_data = vectorstore.get(include=['metadatas', 'documents', 'embeddings'])
        
        documents_map = {} # ID -> Document
        embeddings_map = {} # ID -> Embedding
        bm25_docs_pool = []

        if all_data['documents']:
            for i, (content, metadata) in enumerate(zip(all_data['documents'], all_data['metadatas'])):
                doc = Document(page_content=content, metadata=metadata)
                uid = metadata.get('unique_id')
                if uid:
                    documents_map[uid] = doc
                    if all_data.get('embeddings') is not None:
                        embeddings_map[uid] = all_data['embeddings'][i]
                bm25_docs_pool.append(doc)
        
        if not bm25_docs_pool:
            return vector_results # Fallback
            
        bm25_retriever = BM25Retriever.from_documents(
            bm25_docs_pool,
            preprocess_func=self._kiwi_tokenize
        )
        bm25_retriever.k = k
        
        bm25_results = bm25_retriever.invoke(keyword_query if keyword_query else query)
        
        # 4. Integrate Results
        combined_results = {} # uid -> {'doc': doc, 'score': score}
        
        # Add Vector Results (Already has scores)
        for doc, score in vector_results:
            uid = doc.metadata.get('unique_id')
            if uid:
                combined_results[uid] = {'doc': doc, 'score': score}
        
        # Add BM25 Results (Calculate Score if missing)
        # To calculate score, we need query embedding
        query_embedding = self.embedding_model.embed_query(query)
        
        for doc in bm25_results:
            uid = doc.metadata.get('unique_id')
            if not uid: 
                continue
                
            if uid in combined_results:
                # Already exists from vector search (usually implies good score), take the better (lower) score?
                # Actually vector search score is accurate L2.
                # Just keep existing.
                continue
            else:
                # Found by BM25 but not top vector results. Calculate vector score manually.
                if uid in embeddings_map:
                    doc_vec = embeddings_map[uid]
                    # Calculate Euclidean Distance (L2)
                    dist = np.linalg.norm(np.array(query_embedding) - np.array(doc_vec))
                    combined_results[uid] = {'doc': doc, 'score': float(dist)}
                else:
                    # No embedding found (should not happen if synced), assign a default bad score
                    combined_results[uid] = {'doc': doc, 'score': 999.0}
        
        # Convert to list and sort by score (ASC)
        final_list = []
        for uid, data in combined_results.items():
            final_list.append((data['doc'], data['score']))
            
        final_list.sort(key=lambda x: x[1])
        
        return final_list[:k*2] # Return slighly more candidates for downstream filtering

if __name__ == "__main__":
    print("RecruitIndexer module loaded.")
