from __future__ import annotations

import os
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
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
        model: str = "HCX-DASH-002",
        api_key_env: str = "NCP_CLOVASTUDIO_API_KEY",
    ) -> None:
        self.api_key = os.environ.get(api_key_env)
        self.base_url = os.environ.get("NCP_CLOVASTUDIO_BASE_URL", "https://clovastudio.stream.ntruss.com")
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
너는 한국어 포트폴리오 텍스트를 분석하여 구조화된 JSON 데이터를 생성하는 전문가야.
반드시 아래 JSON 스키마(CombinedResult)에 맞춰서 정확한 JSON 문자열만 응답해. 마크다운 코드 블록(```json)이나 사족을 붙이지 마.

[스키마 설명]
1. user_data (사용자 정보)
  - profile: user_id, name, job_title, summary (원문에 없으면 null)
  - projects: 프로젝트 리스트 (아래 상세 규칙 참고)
  - skills: 핵심 역량 키워드 리스트
2. job_queries (공고 검색 쿼리)
  - queries: 3개의 검색 쿼리 객체 (A, B, C 유형)
    - type: "A" | "B" | "C"
    - query: 검색 쿼리 문장 (80~140자)
    - evidence: 근거 구절 리스트

[Project 구조 생성 규칙]
- description_for_embedding 필드는 반드시 멀티라인 문자열로, 아래 형식을 지켜야 함:
  [문제-해결 매핑]
  1) 문제: ...
     - 해결: ...
     - 결과: ...
  [전체 성과]
  - ...

[Query 생성 규칙]
- A유형: 기술 스택 + 핵심 역량
- B유형: 문제 해결 중심
- C유형: 프로젝트 요약 (목적 + 기여)

[입력 텍스트]
{text}

[출력 예시]
{{
  "user_data": {{
    "profile": {{ "name": "...", ... }},
    "projects": [ ... ],
    "skills": [ ... ]
  }},
  "job_queries": {{
    "queries": [
       {{ "type": "A", "query": "...", "evidence": ["..."] }},
       ...
    ]
  }}
}}
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
                            description_for_embedding=f"AI 응답 오류: {str(e)}\n\n원문 내용:\n{text[:500]}..."
                        )
                    ]
                ),
                job_queries=JobQueryResult(queries=[])
            )
