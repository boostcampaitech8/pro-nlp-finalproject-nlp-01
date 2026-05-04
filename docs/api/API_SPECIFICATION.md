# API 명세서 (API Specification)

이 문서는 AI 채용 플랫폼의 프론트엔드와 백엔드 간 협업을 위한 상세 API 규격을 정의합니다.

## 공통 가이드

### 기본 환경
- **Base URL**: `https://api.pro-nlp.com/api` (또는 `http://localhost:8080/api`)
- **Content-Type**: `application/json`
- **인증**: `Authorization: Bearer {token}` (JWT)

### 응답 상태 코드
- `200 OK`: 요청 성공 (동기 처리 완료)
- `201 Created`: 리소스 생성 성공
- `202 Accepted`: 비동기 요청 접수 (백그라운드 처리 시작)
- `401 Unauthorized`: 인증 실패
- `404 Not Found`: 리소스 없음

---

## 1. 인증 (Authentication)

### GET `/api/auth/kakao/callback`
카카오 로그인 및 토큰 발급.
- **Request**: `?code={kakao_auth_code}`
- **Response**: `{ "user": {...}, "token": "jwt..." }`

### GET `/api/auth/me`
내 정보 조회.

---

## 2. 채용 공고 (Recruitments)

### GET `/api/recruits`
공고 목록 조회 (필터링 지원).
- **Query**: `page`, `limit`, `category`, `keyword`, `sort`
- **Response**: `{ "items": [...], "meta": {...} }`

### GET `/api/recruits/{id}`
공고 상세 조회.

### GET `/api/recruits/recommend`
(AI) 사용자 맞춤 공고 추천. 사용자의 포트폴리오 분석 결과(`embeddings`)를 기반으로 추천.

---

## 3. 포트폴리오 (Portfolios)

### POST `/api/portfolios/analyze` (Preview)
(Sync) 입력된 소스(URL/File)를 **저장하지 않고** 즉시 텍스트를 추출하여 미리보기 제공.
- **Body**: `{ "source": "url...", "type": "github" }` or `FormData` (file)
- **Response**: `{ "content": "extracted text...", "success": true }`

### POST `/api/portfolios` (Create & Process)
(Async) 포트폴리오를 DB에 저장하고, **백그라운드 직무 분석 작업(Embedding)**을 트리거함.
- **Body**: `{ "title": "...", "source_url": "...", "type": "..." }`
- **Response (201)**:
```json
{
  "id": 1,
  "processing_status": "PENDING", 
  "project_name": "My Project"
}
```
*Note: 처리가 완료되면 `processing_status`가 `COMPLETED`로 변경됨 (Polling 필요).*

### POST `/api/portfolios/upload`, `/api/portfolios/notion`, `/api/portfolios/github`
편의성을 위한 소스별 생성 엔드포인트. (`/api/portfolios`와 동일한 로직 수행)

### GET `/api/portfolios`
내 포트폴리오 목록 조회.

### GET `/api/portfolios/{id}`
포트폴리오 상세 조회. (분석된 `description`, `tech_stack` 포함)

---

## 4. 자기소개서 (Cover Letters)

### POST `/api/cover-letters/generate`
(Sync/Blocking) AI를 사용하여 자기소개서 초안 생성. (시간이 다소 소요될 수 있음)
- **Body**:
```json
{
  "recruit_id": 1,
  "portfolioIds": [1, 2],
  "question": "지원동기",
  "tone": "professional"
}
```
- **Response**: `{ "id": 10, "content": "AI generated content...", "gap_analysis": {...} }`

### GET `/api/cover-letters`
자소서 목록 조회.

### GET `/api/cover-letters/{id}`
자소서 상세 조회.

### PATCH `/api/cover-letters/{id}`
자소서 내용 수정.


## 공통 가이드

### 기본 환경
- **Base URL**: `https://api.pro-nlp.com/api` (또는 로컬 환경: `http://localhost:8080/api`)
- **Content-Type**: `application/json`
- **인증 방식**: Bearer Token 인증 (로그인이 필요한 모든 API는 Header에 `Authorization: Bearer {token}` 포함 필수)

### 공통 에러 응답 구조
에러 발생 시 다음과 같은 일관된 응답 구조를 반환합니다.

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자에게 보여줄 에러 메시지",
    "details": "개발용 디버깅 정보 (선택 사항)"
  }
}
```

### 주요 상태 코드
- `200 OK`: 요청 성공
- `201 Created`: 생성 요청 성공 (POST)
- `400 Bad Request`: 필수 파라미터 누락 또는 유효하지 않은 데이터
- `401 Unauthorized`: 인증 토큰 누락 또는 만료
- `403 Forbidden`: 접근 권한 없음
- `404 Not Found`: 요청한 리소스를 찾을 수 없음
- `500 Internal Server Error`: 서버 내부 오류

---

## 1. 인증 (Authentication)

### GET `/api/auth/kakao/callback`
카카오 OAuth 인증 코드를 처리하여 로그인을 완료하고 토큰을 반환합니다.

**쿼리 파라미터:**
| 필드 | 타입 | 필수 여부 | 설명 |
| :--- | :--- | :--- | :--- |
| `code` | String | Y | 카카오에서 발급한 인가 코드 |

**응답 성공 (200 OK):**
```json
{
  "user": {
    "id": 1,
    "email": "user@kakao.com",
    "name": "카카오본인",
    "profileImage": "https://..."
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### GET `/api/auth/me`
현재 로그인된 사용자의 프로필 정보를 조회합니다.

**필수 헤더:** `Authorization: Bearer {token}`

**응답 성공 (200 OK):**
```json
{
  "id": 1,
  "email": "user@kakao.com",
  "name": "카카오본인",
  "profileImage": "https://..."
}
```

---

## 2. 채용 공고 (Recruitments)

### GET `/api/recruits`
채용 공고 목록을 조회합니다. 필터링 및 검색을 지원합니다.

**쿼리 파라미터:**
| 필드 | 타입 | 필수 여부 | 설명 |
| :--- | :--- | :--- | :--- |
| `page` | Integer | - | 페이지 번호 (기본: 1) |
| `limit` | Integer | - | 항목 수 (기본: 10) |
| `category` | String | - | 직무 필터 (`frontend`, `backend`, `ai`, `all`) |
| `keyword` | String | - | 검색어 (회사명, 공고명) |
| `sort` | String | - | 정렬 (`latest`, `popular`) |

**응답 성공 (200 OK):**
```json
{
  "items": [
    {
      "id": 1,
      "title": "프론트엔드 개발자",
      "company": "Google",
      "startDate": "2026-02-01",
      "deadline": "2026-03-01",
      "tags": ["React", "TypeScript"]
    }
  ],
  "meta": { "total": 128, "page": 1, "limit": 10, "totalPages": 13 }
}
```

### GET `/api/recruits/:id`
특정 공고의 상세 정보와 본문을 조회합니다.

### GET `/api/recruits/recommend`
사용자 커리어 데이터 기반 AI 맞춤 공고 목록을 조회합니다.

---

## 3. 포트폴리오 (Portfolios)

### POST `/api/portfolios/extract`
GitHub URL, 블로그 링크 또는 PDF 파일로부터 비정형 텍스트를 추출합니다.

**요청 본문:**
```json
{
  "source": "https://github.com/...",
  "type": "github"
}
```

### POST `/api/portfolios/analyze`
추출된 텍스트를 AI(LLM)가 분석하여 프로젝트 단위로 구조화합니다.

**응답 성공 (200 OK):** 구조화된 프로젝트 목록 반환

### GET `/api/portfolios`
저장된 포트폴리오 목록 조회

### PATCH `/api/portfolios/:id`
포트폴리오 정보 수정

### DELETE `/api/portfolios/:id`
포트폴리오 삭제

---

## 4. 자기소개서 (Cover Letters)

### POST `/api/cover-letters/generate`
AI를 통해 포트폴리오 기반의 자소서 초안을 생성합니다.

**요청 본문:**
```json
{
  "recruit_id": 1,
  "portfolioIds": [1, 2],
  "question": "지원동기",
  "tone": "professional"
}
```

### POST `/api/cover-letters/refine`
작성 중인 텍스트에 대해 AI가 문맥을 첨삭하고 대안 문장을 제안합니다.

**요청 본문:**
```json
{
  "currentText": "저는 리액트를 잘합니다...",
  "focus": "기술적 전문성 강조"
}
```

### GET `/api/cover-letters`
자소서 목록 조회

### GET `/api/cover-letters/:id`
자소서 상세 조회

### PATCH `/api/cover-letters/:id`
자소서 내용 수정 (수동 편집)

### DELETE `/api/cover-letters/:id`
자소서 삭제
