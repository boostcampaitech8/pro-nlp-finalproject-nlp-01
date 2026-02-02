"""
환경 변수 및 설정 관리 모듈
- HyperCLOVA OpenAI 호환 API 사용
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

# API 키 (CLOVA Studio)
CLOVA_API_KEY = os.getenv("CLOVA_API_KEY")

# CLOVA Studio OpenAI 호환 API 설정
CLOVA_BASE_URL = "https://clovastudio.stream.ntruss.com/v1/openai"

# 데이터 경로
DATA_DIR = PROJECT_ROOT / "data"
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"

# ChromaDB 설정
CHROMA_PERSIST_DIR = str(EMBEDDINGS_DIR / "chroma_db")

# 임베딩 설정 (CLOVA bge-m3)
EMBEDDING_MODEL = "bge-m3"

# LLM 설정 (HyperCLOVA X)
LLM_MODEL = "HCX-007"
LLM_TEMPERATURE = 0.5   # 사실 기반 생성 (할루시네이션 원천 차단을 위해 0.0 설정)
LLM_TOP_P = 0.8        # 안정적 어휘 (API 기본값과 동일하나, 명시적 고정)
LLM_REPETITION_PENALTY = 1.2  # 문장 반복 방지 (기본값 1.1보다 높게 설정하여 반복 억제 강화)
LLM_MAX_TOKENS = 32768  # 긴 자소서 생성을 위해 최대치 설정

# 검색 설정
SEARCH_TOP_K = 5
BM25_WEIGHT = 0.3
VECTOR_WEIGHT = 0.7

# 청킹 설정
CHUNK_SIZE = 800
CHUNK_OVERLAP = 160

# Thinking 설정 (HCX-007 이상)
# Level: low, medium, high 중 선택 (API 지원 시)
LLM_USE_THINKING = True
LLM_THINKING_LEVEL = "high"  # budget_tokens 등 구체적 값은 나중에 매핑
