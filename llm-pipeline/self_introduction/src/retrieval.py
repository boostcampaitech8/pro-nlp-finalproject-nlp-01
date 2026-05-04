"""
Hybrid 검색 모듈 (BM25 + Vector)
- BM25: 키워드 기반 정확 매칭
- Vector: 의미적 유사성 검색
- 가중치 조합으로 최종 순위 결정
"""
from typing import List
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from langchain_chroma import Chroma

from config.settings import SEARCH_TOP_K, BM25_WEIGHT, VECTOR_WEIGHT


class HybridRetriever:
    """
    Hybrid Retriever: BM25 + Vector Search 결합
    """
    
    def __init__(
        self,
        vectorstore: Chroma,
        documents: List[Document],
        bm25_weight: float = BM25_WEIGHT,
        vector_weight: float = VECTOR_WEIGHT,
        top_k: int = SEARCH_TOP_K
    ):
        self.vectorstore = vectorstore
        self.documents = documents
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.top_k = top_k
        
        # BM25 인덱스 생성
        self.tokenized_docs = [self._tokenize(doc.page_content) for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized_docs)
    
    def _tokenize(self, text: str) -> List[str]:
        """간단한 토큰화 (공백 기반)"""
        # 한국어는 공백 + 조사 분리가 필요하지만, 단순화를 위해 공백 기반 사용
        return text.lower().split()
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """점수 정규화 (0~1)"""
        if not scores:
            return scores
        min_score = min(scores)
        max_score = max(scores)
        if max_score == min_score:
            return [1.0] * len(scores)
        return [(s - min_score) / (max_score - min_score) for s in scores]
    
    def search(self, query: str) -> List[Document]:
        """
        Hybrid 검색 수행
        Returns: 상위 k개 문서 (full_context 포함)
        """
        # 1. BM25 검색
        tokenized_query = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        normalized_bm25 = self._normalize_scores(list(bm25_scores))
        
        # 2. Vector 검색
        vector_results = self.vectorstore.similarity_search_with_score(
            query, 
            k=len(self.documents)  # 전체 문서에 대해 점수 계산
        )
        
        # Vector 점수를 문서 인덱스에 매핑
        vector_score_map = {}
        for doc, score in vector_results:
            # ChromaDB는 거리를 반환하므로 유사도로 변환 (1 - distance)
            # 또는 점수가 이미 유사도일 수 있음
            for i, orig_doc in enumerate(self.documents):
                if orig_doc.page_content == doc.page_content:
                    vector_score_map[i] = 1 - score if score <= 1 else 1 / (1 + score)
                    break
        
        # 3. 점수 결합
        combined_scores = []
        for i in range(len(self.documents)):
            bm25_score = normalized_bm25[i] if i < len(normalized_bm25) else 0
            vector_score = vector_score_map.get(i, 0)
            
            combined = (
                self.bm25_weight * bm25_score + 
                self.vector_weight * vector_score
            )
            combined_scores.append((i, combined))
        
        # 4. 상위 k개 선택
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        top_indices = [idx for idx, _ in combined_scores[:self.top_k]]
        
        # 5. full_context를 포함한 문서 반환
        results = []
        for idx in top_indices:
            doc = self.documents[idx]
            # 메타데이터에서 full_context 가져와서 새 Document 생성
            full_context = doc.metadata.get("full_context", doc.page_content)
            result_doc = Document(
                page_content=full_context,  # LLM에게는 전체 문맥 전달
                metadata=doc.metadata
            )
            results.append(result_doc)
        
        return results


class ChromaRetriever:
    """
    ChromaRetriever: ChromaDB에서 직접 검색 수행
    (BM25 없이 벡터 검색만 수행하거나, 로드된 문서와 조합 가능)
    """
    
    def __init__(
        self,
        vectorstore: Chroma,
        top_k: int = SEARCH_TOP_K
    ):
        self.vectorstore = vectorstore
        self.top_k = top_k
        
    def search(self, query: str) -> List[Document]:
        """
        벡터 검색 수행
        Returns: 상위 k개 문서 (full_context 포함)
        """
        # 1. Vector 검색
        results = self.vectorstore.similarity_search(query, k=self.top_k)
        
        # 2. full_context를 본문으로 사용하도록 변환
        processed_results = []
        for doc in results:
            full_context = doc.metadata.get("full_context", doc.page_content)
            result_doc = Document(
                page_content=full_context,
                metadata=doc.metadata
            )
            processed_results.append(result_doc)
            
        return processed_results


def create_hybrid_retriever(
    vectorstore: Chroma,
    documents: List[Document]
) -> HybridRetriever:
    """Hybrid Retriever 생성 헬퍼 함수"""
    return HybridRetriever(vectorstore, documents)


if __name__ == "__main__":
    from rich import print as rprint
    from src.embeddings import load_user_vectorstore
    from src.data_loader import get_all_user_documents
    
    rprint("[bold yellow]Testing Hybrid Retriever...[/bold yellow]")
    
    # User1 데이터로 테스트
    user_docs = get_all_user_documents("user1")
    vectorstore = load_user_vectorstore("user1")
    
    retriever = HybridRetriever(vectorstore, user_docs)
    
    # 검색 테스트
    query = "대용량 트래픽 처리 경험"
    results = retriever.search(query)
    
    rprint(f"\n[bold green]Query: {query}[/bold green]")
    rprint(f"[bold blue]Results ({len(results)}):[/bold blue]")
    
    for i, doc in enumerate(results):
        rprint(f"\n--- Result {i+1} ---")
        rprint(f"Project: {doc.metadata.get('project_name', 'N/A')}")
        rprint(f"Content preview: {doc.page_content[:200]}...")
