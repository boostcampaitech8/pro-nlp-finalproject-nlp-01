"""
벡터 스토어 관리 모듈
- CLOVA Studio OpenAI 호환 임베딩 (bge-m3)
- ChromaDB 컬렉션 생성 및 관리
- 문서 임베딩 및 영속 저장
"""
from typing import List, Optional
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from openai import OpenAI

from config.settings import (
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    EMBEDDINGS_DIR,
    CLOVA_API_KEY,
    CLOVA_BASE_URL
)
from src.data_loader import get_all_user_documents, get_company_documents


class CLOVAEmbeddings(Embeddings):
    """CLOVA Studio 임베딩 클래스 (OpenAI 호환 API)"""
    
    def __init__(self, model: str = "bge-m3"):
        self.model = model
        self.client = OpenAI(
            api_key=CLOVA_API_KEY,
            base_url=CLOVA_BASE_URL
        )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서 리스트 임베딩"""
        embeddings = []
        for text in texts:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"  # CLOVA 필수 파라미터
            )
            embeddings.append(response.data[0].embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """쿼리 텍스트 임베딩"""
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float"  # CLOVA 필수 파라미터
        )
        return response.data[0].embedding


def get_embeddings() -> CLOVAEmbeddings:
    """CLOVA Studio 임베딩 모델 초기화"""
    return CLOVAEmbeddings(model=EMBEDDING_MODEL)


def get_or_create_vectorstore(
    collection_name: str,
    documents: Optional[List[Document]] = None
) -> Chroma:
    """
    벡터스토어 가져오기 또는 생성
    - 이미 존재하면 로드
    - 없으면 documents로 새로 생성
    """
    persist_directory = str(Path(CHROMA_PERSIST_DIR) / collection_name)
    embeddings = get_embeddings()
    
    # 디렉토리가 존재하고 데이터가 있으면 로드
    if Path(persist_directory).exists() and any(Path(persist_directory).iterdir()):
        return Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_directory
        )
    
    # 새로 생성
    if documents is None:
        raise ValueError(f"Collection {collection_name} does not exist and no documents provided")
    
    # 디렉토리 생성
    Path(persist_directory).mkdir(parents=True, exist_ok=True)
    
    return Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory
    )


def create_user_vectorstore(user_id: str) -> Chroma:
    """특정 사용자의 벡터스토어 생성"""
    documents = get_all_user_documents(user_id)
    collection_name = f"user_{user_id}"
    return get_or_create_vectorstore(collection_name, documents)


def create_company_vectorstore() -> Chroma:
    """기업 벡터스토어 생성"""
    documents = get_company_documents()
    return get_or_create_vectorstore("company", documents)


def load_user_vectorstore(user_id: str) -> Chroma:
    """사용자 벡터스토어 로드"""
    collection_name = f"user_{user_id}"
    persist_directory = str(Path(CHROMA_PERSIST_DIR) / collection_name)
    
    if not Path(persist_directory).exists():
        # 없으면 새로 생성
        return create_user_vectorstore(user_id)
    
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=persist_directory
    )


def load_company_vectorstore() -> Chroma:
    """기업 벡터스토어 로드"""
    persist_directory = str(Path(CHROMA_PERSIST_DIR) / "company")
    
    if not Path(persist_directory).exists():
        return create_company_vectorstore()
    
    return Chroma(
        collection_name="company",
        embedding_function=get_embeddings(),
        persist_directory=persist_directory
    )


def create_all_vectorstores():
    """모든 벡터스토어 생성 (초기화용)"""
    from rich import print as rprint
    from config.settings import DATA_DIR
    
    rprint("[bold yellow]Creating vectorstores...[/bold yellow]")
    
    # data 폴더에서 사용자 목록 동적 감지
    user_files = list(Path(DATA_DIR).glob("*_data.json"))
    user_ids = [f.stem.replace("_data", "") for f in user_files if f.stem != "company_data"]
    
    if not user_ids:
        rprint("[yellow]⚠️ 사용자 데이터 파일이 없습니다.[/yellow]")
    
    # 사용자 벡터스토어 생성
    for user_id in user_ids:
        rprint(f"  Creating {user_id} vectorstore...")
        create_user_vectorstore(user_id)
        rprint(f"  [green]✓ {user_id} vectorstore created[/green]")
    
    # 기업 벡터스토어 생성
    rprint("  Creating company vectorstore...")
    create_company_vectorstore()
    rprint("  [green]✓ company vectorstore created[/green]")
    
    rprint("[bold green]All vectorstores created successfully![/bold green]")


if __name__ == "__main__":
    create_all_vectorstores()
