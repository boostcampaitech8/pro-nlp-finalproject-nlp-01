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
        model: str = "HCX-007",  # Changed to HCX-007 for Structured Outputs
        api_key_env: str = "NCP_CLOVASTUDIO_API_KEY",
    ) -> None:
        self.api_key = os.environ.get(api_key_env)
        env_url = os.environ.get("NCP_CLOVASTUDIO_BASE_URL")
        self.base_url = env_url if env_url else "https://clovastudio.stream.ntruss.com"
        self.model = model
        
        if not self.api_key:
            print(f"Warning: {api_key_env} is not set. NCP features will work.")
    
    async def _call_ncp(self, messages: List[dict], response_schema: dict = None, max_tokens: int = 3000) -> str:
        """Call NCP Chat Completions V3 with Structured Outputs support."""
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
            "maxCompletionTokens": max_tokens,  # Changed from maxTokens
            "temperature": 0.1,
            "topP": 0.8,
            "topK": 0,
            "thinking": {"effort": "none"}  # Required for Structured Outputs
        }
        
        # Add Structured Outputs if schema provided
        if response_schema:
            payload["responseFormat"] = {
                "type": "json",
                "schema": response_schema
            }
        
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            res_json = response.json()
            
            if res_json.get("status", {}).get("code") == "20000":
                return res_json.get("result", {}).get("message", {}).get("content", "")
            else:
                raise RuntimeError(f"NCP API Error: {res_json}")


    async def extract_user_data_and_queries(self, text: str) -> CombinedResult:
        """
        Extract structured user data and job queries from portfolio text using NCP Structured Outputs.
        """
        system_prompt = """
당신은 포트폴리오 분석 전문가입니다.
사용자의 포트폴리오 텍스트를 분석하여 다음을 추출하세요:

1. **사용자 정보**: 이름, 직무, 요약, 프로젝트, 기술 스택
2. **공고 검색 쿼리 3개** (A, B, C 타입):
   - A: 사용자의 핵심 기술과 경험을 기반으로 한 메인 포지션
   - B: 사용자의 부가 기술이나 관심 분야를 기반으로 한 서브 포지션
   - C: 사용자의 잠재력이나 성장 가능성을 고려한 도전적 포지션

**중요 규칙:**
- 모든 필드를 최대한 채우세요. 정보가 부족하면 문맥에서 추론하세요.
- 각 쿼리는 실제 채용 공고 검색에 사용될 수 있도록 구체적으로 작성하세요.
- evidence는 포트폴리오에서 해당 쿼리를 뒷받침하는 구체적인 근거를 제시하세요.

**description_for_embedding 작성 규칙:**
프로젝트의 description_for_embedding은 반드시 아래 템플릿을 따라 작성하세요:

[문제-해결 매핑]
1) 문제: (프로젝트에서 직면한 구체적인 문제나 과제)
   - 해결:
     - (문제를 해결하기 위해 수행한 구체적인 작업 1)
     - (문제를 해결하기 위해 수행한 구체적인 작업 2)
   - 결과: (해결 후 얻은 성과, 원문에 있을 때만)

2) 문제: (두 번째 문제, 있다면)
   - 해결:
     - (해결 작업)
   - 결과: (성과, 원문에 있을 때만)

[전체 성과]
- (프로젝트 전체의 정량적/정성적 성과, 원문에 있을 때만)
- 없으면: - 미기재

**템플릿 작성 주의사항:**
- 각 "문제"는 구체적이고 명확해야 합니다
- "해결" 항목은 기술적 구현 방법을 포함해야 합니다
- "결과"는 원문에 명시된 경우에만 작성하세요
- 정보가 부족하면 "미기재"로 표시하세요
"""

        user_prompt = f"""
[포트폴리오 텍스트]
{text}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Generate JSON Schema from Pydantic model
        schema = CombinedResult.model_json_schema()
        
        try:
            response_text = await self._call_ncp(messages, response_schema=schema)
            
            # With Structured Outputs, response is guaranteed valid JSON
            result = CombinedResult.model_validate_json(response_text)
            
            # Safety: Ensure only top 3 queries
            if len(result.job_queries.queries) > 3:
                result.job_queries.queries = result.job_queries.queries[:3]
                
            return result

        except Exception as e:
            logger.error(f"NCP LLM Generation Failed: {e}")
            raw_response = locals().get('response_text', 'No response')
            logger.error(f"Raw Response: {raw_response}")
            
            # Fallback if AI fails
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
