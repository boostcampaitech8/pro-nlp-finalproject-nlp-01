# AI Resume Consultant (AI 자소서 컨설턴트)

RAG & LangChain 기반 AI 자소서 컨설턴트 시스템

## 기능

- 사용자 경험과 기업 채용 요건 매칭
- Gap 분석 (부족한 역량 식별)
- 맞춤형 자소서 생성 (문항별)
- PydanticOutputParser로 구조화된 결과 출력

## 설치

```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows)
.\.venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 환경 설정

`.env` 파일을 생성하고 Google AI Studio API 키를 설정하세요:

```
GOOGLE_API_KEY=your_api_key_here
```

## 사용법

### 기본 사용법

```bash
# 최초 실행 (벡터스토어 초기화 필수)
python main.py --user user1 --init

# 이후 실행 (초기화 불필요)
python main.py --user user1
python main.py --user user2

# 실수로 venv portfolio 폴더꺼 사용했음
llm-pipeline/portfolios/venv/Scripts/python llm-pipeline/self_introduction/generate_from_chroma.py --user_id unknown_user

llm-pipeline/portfolios/venv/Scripts/python llm-pipeline/self_introduction/generate_from_chroma.py --user_id unknown_user --save

```


### 특정 문항만 생성

```bash
# 1번 문항 (지원동기) 생성
python main.py --user user1 --question 1

# 2번 문항 (강점/성과) 생성
python main.py --user user1 --question 2

# 3번 문항 (문제해결 경험) 생성
python main.py --user user1 --question 3
```

### 결과 파일 저장

```bash
# 생성된 자소서를 파일로 저장
python main.py --user user1 --save
```

## CLI 옵션

| 옵션 | 설명 |
|------|------|
| `--user` | 분석할 사용자 선택 (`user1` 또는 `user2`) |
| `--question` | 특정 문항만 생성 (`1`, `2`, `3`) |
| `--init` | 벡터스토어 초기화 (최초 1회 필수) |
| `--save` | 결과를 파일로 저장 (`output/` 폴더) |

## 자소서 문항

1. **지원동기 및 입사 후 포부** (1000자 이내)
2. **본인의 강점과 이를 활용하여 성과를 낸 경험** (1000자 이내)
3. **기술적으로 어려운 문제를 해결한 경험** (1000자 이내)

## 기술 스택

- **LLM**: Google Gemini (gemini-3-flash-preview)
- **Embeddings**: HuggingFace (jhgan/ko-sroberta-multitask)
- **Vector Store**: ChromaDB
- **검색**: BM25 + Vector Hybrid Search
- **출력 구조화**: PydanticOutputParser
- **UI**: Rich (터미널 스타일링)

## 프로젝트 구조

```
ai_resume_consultant/
├── config/
│   └── settings.py          # 환경 변수 및 설정
├── data/
│   ├── company_data.json    # 기업 채용 데이터
│   ├── user1_data.json      # 사용자1 데이터 (적합 케이스)
│   └── user2_data.json      # 사용자2 데이터 (Gap 케이스)
├── src/
│   ├── data_loader.py       # 데이터 로딩 및 전처리
│   ├── embeddings.py        # 벡터 스토어 관리
│   ├── retrieval.py         # Hybrid 검색
│   ├── schemas.py           # Pydantic 스키마
│   ├── prompt_templates.py  # 프롬프트 템플릿
│   └── gap_analysis.py      # Gap 분석 및 자소서 생성
├── main.py                  # CLI 진입점
└── requirements.txt         # 의존성
```
