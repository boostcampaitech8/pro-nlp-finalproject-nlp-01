# 포트폴리오 처리 파이프라인 (실험용)

이 모듈은 다양한 소스(파일, GitHub, Notion)에서 사용자 포트폴리오를 처리하고, LLM을 사용하여 내용을 정제한 후, Chroma DB에 벡터 임베딩으로 저장하는 실험적인 파이프라인을 구현합니다.

## 주요 기능

-   **다중 소스 추출**:
    -   **파일**: PDF (`pdfplumber`), 텍스트(.txt, .md) 파일 추출 지원.
    -   **GitHub**: GitHub 리포지토리 URL (단일 프로젝트) 또는 사용자 ID (퍼블릭 리포당 개별 프로젝트) 추출 지원.
    -   **Notion**: (추후 구현 예정) 워크스페이스 내 페이지/데이터베이스 크롤링 지원.
-   **LLM 정제 및 구조화**: Google Gemini (`gemini-2.5-flash`)를 사용해 모든 프로젝트를 개별적으로 구조화하고 자소서 검색용 쿼리 생성.
-   **RAG 최적화 저장**: `self_introduction` 모듈의 사양(300자 청킹)에 맞춰 ChromaDB에 저장하며, 검색 정확도를 위해 각 조각(Chunk)을 생성.

## 설정 (Setup)

1.  **환경 변수**:
    `llm-pipeline/portfolios/` 폴더 내에 `.env` 파일을 생성합니다.
    ```ini
    GOOGLE_API_KEY=your_google_api_key
    GITHUB_TOKEN=your_optional_github_token
    ```

2.  **설치**:
    ```bash
    # 의존성 패키지 설치
    llm-pipeline/portfolios/venv/Scripts/pip install -r llm-pipeline/portfolios/requirements.txt
    ```

## 사용법 (Usage)

각 소스 타입에 맞는 스크립트를 실행합니다. 데이터는 자동으로 `self_introduction/embeddings/chroma_db` 경로에 저장됩니다.

### 1. 로컬 파일 처리 (PDF 등)
```bash
# data 폴더에 파일을 넣고 실행
llm-pipeline/portfolios/venv/Scripts/python llm-pipeline/portfolios/process_file.py --path "llm-pipeline/portfolios/data/portfolio.pdf"
```

### 2. GitHub 소스 처리
```bash
# 특정 리포지토리 URL (단일 프로젝트 추출)
llm-pipeline/portfolios/venv/Scripts/python llm-pipeline/portfolios/process_github.py --url https://github.com/owner/repo

# 사용자 ID (모든 퍼블릭 리포를 개별 프로젝트로 추출)
llm-pipeline/portfolios/venv/Scripts/python llm-pipeline/portfolios/process_github.py --url <github_id>
```

### 3. 저장된 데이터 확인 (JSON 내보내기)
저장된 임베딩 벡터의 내용을 가독성 좋은 JSON으로 확인하고 싶을 때 사용합니다.
```bash
llm-pipeline/portfolios/venv/Scripts/python llm-pipeline/portfolios/export_embeddings.py
```
*   결과는 각 컬렉션 폴더 및 `all_portfolios_export.json` 파일로 생성됩니다.
*   데이터는 프로젝트별로 묶이고 `chunk_index` 순서대로 정렬되어 출력됩니다.

## 참고 사항

-   **추출 전략**: GitHub 사용자 ID 처리 시, 각 리포지토리당 1개의 프로젝트 데이터가 생성되도록 설계되어 있습니다.
-   **청킹(Chunking)**: 긴 프로젝트 설명은 약 300자 단위로 쪼개져 저장됩니다. 각 조각의 메타데이터에는 `full_context` 필드가 포함되어 있어, 자소서 생성 시 LLM이 전체 내용을 참조할 수 있습니다.
-   **Notion**: 현재 워크스페이스 전체 검색 로직이 초안 수준으로 포함되어 있으나, 권한 설정 및 데이터 정제 품질 고도화를 위해 추후 정식 업데이트 예정입니다.

## 디렉토리 구조

```
llm-pipeline/portfolios/
├── src/
│   ├── extractors/       # 소스별 추출기
│   ├── processors/       # LLM 정제 (Gemini)
│   └── storage/          # ChromaDB 연동 및 청킹 로직
├── data/                 # 테스트용 데이터 (추출 전용)
├── export_embeddings.py  # 확인용 JSON 내보내기 툴
├── process_file.py       # 파일 처리 엔트리
├── process_github.py     # GitHub 처리 엔트리
├── process_notion.py     # Notion 처리 엔트리 (WIP)
├── requirements.txt      # 의존성 목록
└── README.md             # 본 파일
```
