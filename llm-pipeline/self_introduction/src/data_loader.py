"""
데이터 로딩 및 전처리 모듈
- JSON 파일에서 데이터 로딩
- 텍스트 청킹 (메타데이터 전략 적용)
- LangChain Document 객체 생성
"""
import json
from pathlib import Path
from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def load_json(file_path: Path) -> Dict[str, Any]:
    """JSON 파일 로드"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_company_data() -> Dict[str, Any]:
    """기업 데이터 로드"""
    return load_json(DATA_DIR / "company_data.json")


def load_user_data(user_id: str) -> Dict[str, Any]:
    """사용자 데이터 로드 (user1 또는 user2)"""
    file_name = f"{user_id}_data.json"
    return load_json(DATA_DIR / file_name)


def create_user_documents(user_data: Dict[str, Any]) -> List[Document]:
    """
    사용자 데이터를 Document 객체 리스트로 변환
    - 메타데이터 전략: chunk에는 검색용 텍스트, metadata에는 전체 문맥 저장
    """
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "]
    )
    
    profile = user_data.get("profile", {})
    user_name = profile.get("name", "Unknown")
    user_id = profile.get("user_id", "Unknown")
    
    for project in user_data.get("projects", []):
        project_name = project.get("project_name", "")
        full_description = project.get("description_for_embedding", "")
        tech_stack = project.get("tech_stack", [])
        role = project.get("role", "")
        period = project.get("period", "")
        
        # 청크 분할
        chunks = text_splitter.split_text(full_description)
        
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,  # 검색용 (짧은 글)
                metadata={
                    "source": "user_portfolio",
                    "user_id": user_id,
                    "user_name": user_name,
                    "project_name": project_name,
                    "tech_stack": ", ".join(tech_stack),
                    "role": role,
                    "period": period,
                    "chunk_index": i,
                    "full_context": full_description  # LLM 전달용 (긴 글)
                }
            )
            documents.append(doc)
    
    return documents


def create_company_documents(company_data: Dict[str, Any]) -> List[Document]:
    """
    기업 데이터를 Document 객체 리스트로 변환
    """
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "]
    )
    
    company_info = company_data.get("company_info", {})
    company_name = company_info.get("company_name", "")
    
    job_position = company_data.get("job_position", {})
    job_requirements = company_data.get("job_requirements", {})
    
    full_text = company_data.get("raw_text_for_embedding", "")
    
    # 청크 분할
    chunks = text_splitter.split_text(full_text)
    
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "source": "company_job_posting",
                "company_name": company_name,
                "job_title": job_position.get("title", ""),
                "tech_stack_required": ", ".join(job_position.get("tech_stack_required", [])),
                "tech_stack_preferred": ", ".join(job_position.get("tech_stack_preferred", [])),
                "experience_level": job_position.get("experience_level", ""),
                "chunk_index": i,
                "full_context": full_text
            }
        )
        documents.append(doc)
    
    return documents


def get_all_user_documents(user_id: str) -> List[Document]:
    """특정 사용자의 모든 문서 가져오기"""
    user_data = load_user_data(user_id)
    return create_user_documents(user_data)


def get_company_documents() -> List[Document]:
    """기업 문서 가져오기"""
    company_data = load_company_data()
    return create_company_documents(company_data)


if __name__ == "__main__":
    # 테스트
    from rich import print as rprint
    
    rprint("[bold green]User1 Documents:[/bold green]")
    user1_docs = get_all_user_documents("user1")
    for doc in user1_docs[:2]:
        rprint(f"Content: {doc.page_content[:100]}...")
        rprint(f"Metadata: {doc.metadata}")
        rprint("---")
    
    rprint(f"\n[bold blue]Total User1 Documents: {len(user1_docs)}[/bold blue]")
