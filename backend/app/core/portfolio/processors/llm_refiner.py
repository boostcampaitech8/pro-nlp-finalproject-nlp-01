from __future__ import annotations

import os
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, model_validator, field_validator
import logging

logger = logging.getLogger(__name__)




# ---------- refined schemas ---------- #
class Profile(BaseModel):
    user_id: Optional[str] = Field(None, description="원문에 있으면 추출, 없으면 null")
    name: Optional[str] = Field(None, description="원문에 있으면 추출, 없으면 null")
    job_title: Optional[str] = Field(None, description="원문에 있으면 추출, 없으면 null")
    summary: Optional[str] = Field(None, description="원문에 있으면 추출, 없으면 null")


class Project(BaseModel):
    project_name: str = Field(..., description="프로젝트 이름")
    period: Optional[str] = Field(None, description="프로젝트 기간")
    role: Optional[str] = Field(None, description="역할(짧게)")
    tech_stack: List[str] = Field(default_factory=list, description="원문에 등장한 기술명만")
    description_for_embedding: Optional[str] = Field(
        None, description="아래 섹션 템플릿을 따르는 멀티라인 문자열"
    )

    @model_validator(mode='before')
    @classmethod
    def check_aliases(cls, data: dict) -> dict:
        if isinstance(data, dict):
            # Handle 'title' -> 'project_name'
            if 'project_name' not in data:
                if 'title' in data:
                     data['project_name'] = data['title']
                else:
                     # Fallback if neither exists
                     data['project_name'] = "미기재 프로젝트"
        return data

    @field_validator('description_for_embedding', mode='before')
    @classmethod
    def validate_description(cls, v):
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        return v


class UserData(BaseModel):
    profile: Profile = Field(default_factory=Profile)
    projects: List[Project] = Field(
        default_factory=list, description="텍스트에서 추출된 모든 프로젝트 리스트"
    )
    skills: List[str] = Field(
        default_factory=list, description="원문 근거 있는 핵심 역량 키워드만"
    )


class QueryItem(BaseModel):
    type: Literal["A", "B", "C"] = Field(..., description="쿼리 유형")
    query: str = Field(..., description="기업 공고 검색용 자연어 쿼리 1문장")
    evidence: List[str] = Field(default_factory=list, description="근거 구절 1~3개")


class JobQueryResult(BaseModel):
    queries: List[QueryItem] = Field(default_factory=list)


class CombinedResult(BaseModel):
    user_data: UserData
    job_queries: JobQueryResult


class LLMRefiner:
    """
    - refine_text(): (선택) 텍스트 정제(지금은 pass-through로 둬도 됨)
    - extract_user_data_and_queries(): 포트폴리오 텍스트를 스키마로 구조화 + 공고 검색 쿼리 생성
    """

    def __init__(
        self,
        model: str = "HCX-005",
        api_key_env: str = "NCP_CLOVASTUDIO_API_KEY",
    ) -> None:
        self.api_key = os.environ.get(api_key_env)
        env_url = os.environ.get("NCP_CLOVASTUDIO_BASE_URL")
        self.base_url = env_url if env_url else "https://clovastudio.stream.ntruss.com"
        self.model = model
        
        if not self.api_key:
            print(f"Warning: {api_key_env} is not set. NCP features will work.")
    
    async def _call_ncp(self, messages: List[dict], max_tokens: int = 3000) -> str:
        """Call NCP Chat Completions V3 asynchronously."""
        if not self.api_key:
            raise RuntimeError("NCP API Key is missing.")

        url = f"{self.base_url}/v3/chat-completions/{self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "messages": messages,
            "maxTokens": max_tokens,
            "temperature": 0.5,
            "topP": 0.8,
            "topK": 0
        }
        
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            res_json = resp.json()
            
            if res_json.get("status", {}).get("code") == "20000":
                return res_json.get("result", {}).get("message", {}).get("content", "")
            else:
                raise RuntimeError(f"NCP API Error: {res_json}")

    async def extract_user_data_and_queries(self, text: str) -> Optional[CombinedResult]:
        if not self.api_key:
            raise RuntimeError("NCP API helper not initialized (missing API Key).")

        system_prompt = f"""
너는 한국어 포트폴리오 텍스트를 (1) user1_data JSON으로 구조화하고,
동시에 (2) 기업 공고 검색 쿼리(A/B/C) 3개를 생성하는 도구야.

========================
(1) user1_data 생성 규칙
========================
- 텍스트에 등장하는 모든 프로젝트를 각각 구조화하여 projects 배열에 담아라.
- 텍스트에 근거한 내용만 작성(추측/과장/확장 금지)
- 원문에 없는 profile 값(user_id/name/job_title/summary)은 null
- period/role/description_for_embedding이 없으면 null
- role은 1문장으로 짧게 (괄호로 길게 나열 금지)
- tech_stack은 원문에 등장한 기술명만 배열로
- skills는 원문 근거 있는 핵심 역량 키워드 0~8개(없으면 빈 배열)

description_for_embedding 형식(반드시 그대로):
- 멀티라인 문자열이며 아래 헤더를 그대로 사용해라.
- '문제 상황'과 '해결 과정'이 연결되도록 작성해라(각 해결 과정에 어떤 문제를 해결하는지 포함).

[문제-해결 매핑]
1) 문제: ...
   - 해결:
     - ...
     - ...
   - 결과: ... (원문에 있을 때만)

2) 문제: ...
   - 해결:
     - ...
   - 결과: ... (원문에 있을 때만)

[전체 성과]
- ... (원문에 있을 때만)
- 없으면: - 미기재

추가 규칙:
- 원문에 없는 도메인/기술/수치(TPS, %, ms, PSNR 등) 생성 금지

========================
(2) 공고 검색 쿼리 생성 규칙
========================
- 아래에서 만든 user_data.projects[0] 내용을 근거로 쿼리를 만들어라.
- 추측/과장 금지: user_data에 없는 기술/도메인/수치 절대 생성하지 마.
- 쿼리 3개를 정확히 생성(A,B,C).
- 각 query는 한 문장, 80~140자 내.
- evidence에는 user_data(특히 projects[0])에서 근거가 된 구절을 1~3개 짧게 그대로 넣어.

쿼리 유형:
A: 기술 스택 + 핵심 역량
- 예시 스타일: "Python, FastAPI, Redis, Kafka 기반의 대용량 트래픽 처리 및 비동기 시스템 아키텍처 설계 경험"
B: 문제 해결 중심(어떤 문제를 어떻게 해결)
- 예시 스타일: "10,000 TPS 이상의 고부하 상황에서 대기열 시스템 구현 및 응답 지연 문제를 해결한 백엔드 개발자"
C: 프로젝트 요약(목적/기능 + 기여)
- 예시 스타일: "이커머스 선착순 시스템 및 결제 모듈 리팩토링 경험, 유량 제어 및 DB 부하 최적화 역량"

- A, B, C 쿼리는 서로 표현과 관점이 겹치지 않도록 작성하라.
  (A는 기술 중심, B는 문제 중심, C는 프로젝트 맥락 중심)

========================
출력 형식
========================
반드시 아래 JSON 예시와 정확히 동일한 구조(키 이름, 데이터 타입)로 출력하라:
{{
  "user_data": {{
    "profile": {{ "user_id": null, "name": "홍길동", "job_title": "백엔드 개발자", "summary": "..." }},
    "projects": [
      {{
        "project_name": "프로젝트 A",
        "period": "2023.01 - 2023.06",
        "role": "백엔드 개발 및 인프라 구축",
        "tech_stack": ["Python", "Django", "AWS"],
        "description_for_embedding": "..."
      }}
    ],
    "skills": ["Python", "AWS", "Docker"]
  }},
  "job_queries": {{
    "queries": [
      {{
        "type": "A",
        "query": "Python, Django, AWS 기반의 대규모 트래픽 처리 백엔드 개발자",
        "evidence": ["Python 및 AWS 사용 경험", "대규모 트래픽 처리 프로젝트"]
      }},
      {{
        "type": "B",
        "query": "...",
        "evidence": ["..."]
      }},
      {{
        "type": "C",
        "query": "...",
        "evidence": ["..."]
      }}
    ]
  }}
}}

[TEXT]
{text}
"""
        # NCP handles large context well, but let's be safe.
        # messages construction
        messages = [
            {"role": "system", "content": "너는 JSON 생성기야. 반드시 유효한 JSON만 출력해."},
            {"role": "user", "content": system_prompt}
        ]

        try:
            response_text = await self._call_ncp(messages)
            
            # Clean up cleanup
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            
            # Validation
            result = CombinedResult.model_validate_json(cleaned_text)
            
            # Safety: Ensure only top 3 queries
            if len(result.job_queries.queries) > 3:
                result.job_queries.queries = result.job_queries.queries[:3]
                
            return result

        except Exception as e:
            logger.error(f"NCP LLM Generation Failed: {e}")
            raw_response = locals().get('response_text', 'No response')
            logger.error(f"Raw Response: {raw_response}")
            
            # Fallback if AI fails: Return minimal structure instead of crashing
            return CombinedResult(
                user_data=UserData(
                    profile=Profile(summary="AI 분석에 실패했습니다. (원문 참조)"),
                    projects=[
                        Project(
                            project_name="추출 실패", 
                            description_for_embedding=f"AI 응답 오류: {str(e)}\n\n(URL: {self.base_url}/v3/chat-completions/{self.model})\n\n원문 내용:\n{text[:500]}..."
                        )
                    ]
                ),
                job_queries=JobQueryResult(queries=[])
            )
