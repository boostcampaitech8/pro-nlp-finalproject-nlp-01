# Recruitment Information Pipeline & RAG System

이 디렉터리는 채용 공고 데이터를 자동으로 수집, 가공하고 이를 기반으로 사용자 포트폴리오에 최적화된 공고를 추천하는 RAG(Retrieval-Augmented Generation) 시스템의 파이프라인을 포함하고 있습니다.

## 📂 디렉터리 구조

```text
recruit/
├── data/               # 수집 및 가공된 데이터, Vector DB 저장소
│   ├── recruit_data/   # 크롤링 결과(CSV) 및 LLM 추출 결과(JSON)
│   └── chroma_db/      # Chroma Vector DB 데이터베이스 파일
├── notebooks/          # 초기 로직 연구용 Jupyter Notebook
├── src/                # 메인 실행 소스 코드
└── requirements.txt    # 실행 환경 구성을 위한 패키지 목록
```

## 📄 주요 파일 설명

### 1. 데이터 수집 및 가공 (`src/`)

- **`recruitment_info_gathering.py`**: 
  - `inthiswork.com` 사이트에서 공고를 크롤링합니다.
  - 텍스트가 부족한 이미지 공고의 경우 `surya-ocr`로 텍스트를 추출합니다.
  - Google Gemini API를 사용하여 비정형 텍스트를 구조화된 JSON 데이터로 변환합니다.

- **`recruit_indexer.py`**: 
  - 가공된 채용 공고 데이터를 Vector DB(Chroma)에 인덱싱하는 핵심 로직을 포함합니다.
  - `jhgan/ko-sroberta-multitask` 모델을 사용하여 한국어 임베딩을 수행합니다.

- **`run_recruit_indexer.py`**: 
  - `final_recruitment_all_items.json` 파일을 로드하여 실제로 Vector DB를 생성/업데이트하는 실행 스크립트입니다.

### 2. 검색 및 추천 로직 (`src/`)

- **`query_creator.py`**:
  - 사용자 데이터를 분석하여 검색에 최적화된 3가지 유형의 쿼리(기술 스택, 문제 해결, 프로젝트 성과 중심)를 생성합니다.
  - 검색된 후보 공고들을 LLM(Gemini)이 다시 한 번 비교 분석하여 최종 TOP 3를 추천하고 사유를 작성하는 Re-ranking 기능을 수행합니다.

- **`example_search.py`**:
  - 전체 파이프라인의 통합 실행 예시입니다. 사용자 포트폴리오 입력부터 쿼리 생성, 검색, 필터링, 최종 추천까지의 흐름을 보여줍니다.

### 3. 유틸리티 및 테스트 (`src/`)

- **`inspect_db.py`**: 현재 Vector DB에 저장된 공고의 개수와 상세 메타데이터를 확인하는 디버깅용 도구입니다.
- **`test_recruit_indexer.py`**: 단일 문서 임베딩 및 검색 기능이 정상 동작하는지 확인하는 단위 테스트 스크립트입니다.

## 🚀 실행 방법

1. **환경 구축**:
   ```bash
   pip install -r requirements.txt
   ```

2. **데이터 수집 (선택 사항)**:
   ```bash
   python src/recruitment_info_gathering.py
   ```

3. **인덱싱 (Vector DB 생성)**:
   ```bash
   python src/run_recruit_indexer.py
   ```

4. **검색 및 추천 테스트**:
   ```bash
   python src/example_search.py
   ```

## 🛠 기술 스택
- **Language**: Python
- **LLM API**: Google Gemini (Direct SDK)
- **Vector DB**: ChromaDB
- **Framework**: LangChain (Core, HuggingFace, Chroma)
- **OCR**: Surya-OCR
- **Embedding**: ko-sroberta-multitask
