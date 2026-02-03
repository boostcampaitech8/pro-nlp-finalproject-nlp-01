from __future__ import annotations

import os
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, model_validator, field_validator
import logging
from common.config import settings

logger = logging.getLogger(__name__)




# ---------- refined schemas ---------- #
class Profile(BaseModel):
    user_id: Optional[str] = Field(None, description="원문에 있으면 추출, 없으면 null")
    name: Optional[str] = Field(None, description="원문에 있으면 추출, 없으면 null")
    job_title: Optional[str] = Field(None, description="원문에 있으면 추출, 없으면 null")
    summary: Optional[str] = Field(None, description="원문에 있으면 추출, 없으면 null")


class QueryItem(BaseModel):
    type: Literal["A", "B", "C"] = Field(..., description="쿼리 유형")
    query: str = Field(..., description="기업 공고 검색용 자연어 쿼리 1문장")
    evidence: List[str] = Field(default_factory=list, description="근거 구절 1~3개")


class StrengthItem(BaseModel):
    tag: Literal[
        "문제 해결",
        "주인의식",
        "책임감",
        "도전",
        "새로운 기술 적용",
        "새로운 방법으로 문제 해결",
        "실험/검증",
        "설계/구조화",
        "품질 개선",
        "성능 최적화",
        "협업",
        "커뮤니케이션",
        "프로젝트 리딩",
        "데이터/지표 기반 개선",
    ] = Field(..., description="강점(역량) 태그 (목록 중 선택)")

    claim: str = Field(..., description="이 프로젝트에서 드러난 강점을 한 문장으로 요약")

    evidence: List[str] = Field(
        default_factory=list,
        description="원문 근거 구절 1~3개(짧게 그대로). evidence 없으면 해당 강점은 만들지 말 것.",
    )

    level: Literal["low", "medium", "high"] = Field(
        ..., description="원문 근거 기반 강도 (근거가 약하면 low)"
    )


class Project(BaseModel):
    project_name: str = Field(..., description="프로젝트 이름")
    period: Optional[str] = Field(None, description="프로젝트 기간")
    role: Optional[str] = Field(None, description="역할(짧게)")
    tech_stack: List[str] = Field(default_factory=list, description="원문에 등장한 기술명만")
    description_for_embedding: Optional[str] = Field(
        None, description="아래 섹션 템플릿을 따르는 멀티라인 문자열"
    )
    strengths: List[StrengthItem] = Field(
        default_factory=list,
        description="이 프로젝트에서 드러난 강점(역량) 3~7개 (근거 포함). 근거 없으면 빈 배열 가능.",
    )
    job_queries: List[QueryItem] = Field(
        ..., 
        description="이 프로젝트에 특화된 A/B/C 타입 채용 공고 검색 쿼리 3개 (필수)"
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
        default_factory=list, description="텍스트에서 추출된 모든 프로젝트 리스트 (각 프로젝트는 자체 job_queries 포함)"
    )
    skills: List[str] = Field(
        default_factory=list, description="원문 근거 있는 핵심 역량 키워드만"
    )


class CombinedResult(BaseModel):
    user_data: UserData


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
        self.api_key = settings.NCP_CLOVASTUDIO_API_KEY
        base_url = settings.NCP_CLOVASTUDIO_BASE_URL.strip()
        if not base_url or not base_url.startswith(('http://', 'https://')):
            if base_url and "." in base_url:
                base_url = f"https://{base_url}"
            else:
                base_url = "https://clovastudio.stream.ntruss.com"
        self.base_url = base_url
        self.model = model
        logger.info(f"LLMRefiner initialized with base_url: {self.base_url} and model: {self.model}")
        
        if not self.api_key:
            logger.warning(f"Warning: {api_key_env} is not set. NCP features will work.")
    
    async def _call_ncp(self, messages: List[dict], response_schema: dict = None, max_tokens: int = 4096) -> str:
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
        import asyncio
        import random

        max_retries = 3
        base_delay = 2.0 # seconds
        
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    
                    # Handle Rate Limit (429) or Server Errors (5xx)
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            logger.warning(f"NCP API returned {response.status_code}. Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            response.raise_for_status() # Final attempt failed
                    
                    response.raise_for_status()
                    res_json = response.json()
                    
                    if res_json.get("status", {}).get("code") == "20000":
                        return res_json.get("result", {}).get("message", {}).get("content", "")
                    else:
                        status_code = res_json.get("status", {}).get("code")
                        # Some business logic errors might also be retriable
                        if status_code == "42901" and attempt < max_retries:
                             delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                             logger.warning(f"NCP API business error {status_code}. Retrying in {delay:.2f}s...")
                             await asyncio.sleep(delay)
                             continue
                        
                        raise RuntimeError(f"NCP API Error: {res_json}")
            
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"NCP connection error: {e}. Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    raise


    async def extract_user_data_and_queries(self, text: str) -> CombinedResult:
        """
        Extract structured user data and job queries from portfolio text using NCP Structured Outputs.
        """
        system_prompt = """
당신은 포트폴리오 분석 전문가입니다.
사용자의 포트폴리오 텍스트를 분석하여 다음을 추출하세요:

2. **각 프로젝트마다**:
   - **strengths(강점/역량) 3~7개**: tag/claim/evidence/level 포함
   - **채용 공고 검색 쿼리 3개** (A, B, C 타입):

**중요 규칙:**
- 모든 필드를 최대한 채우세요. 정보가 부족하면 문맥에서 추론하세요.
- 텍스트에 근거한 내용만 작성(추측/과장/확장 금지).
- 정보가 부족하면 null 또는 빈 배열로 둔다. 임의로 채우지 않는다.
- strengths / job_queries의 evidence에는 원문에서 근거가 된 구절을 1~3개 "짧게 그대로" 넣어라.
- evidence가 없는 strengths는 생성하지 않는다.
- **각 프로젝트는 반드시 자체 job_queries 필드를 가져야 합니다** (A, B, C 타입 3개)
- 각 쿼리는 **해당 프로젝트의 기술 스택과 역할에 특화**되어야 합니다
- evidence는 **해당 프로젝트**에서 쿼리를 뒷받침하는 구체적인 근거를 제시하세요

**strengths 작성 가이드:**
- strengths.tag는 아래 목록 중 원문 근거가 있는 것만 선택:
  문제 해결 / 주인의식 / 책임감 / 도전 / 새로운 기술 적용 / 새로운 방법으로 문제 해결 /
  실험/검증 / 설계/구조화 / 품질 개선 / 성능 최적화 / 협업 / 커뮤니케이션 /
  프로젝트 리딩 / 데이터/지표 기반 개선
- claim: "이 프로젝트에서 내가 어떻게 그 역량을 보여줬는지"를 1문장으로 작성.
- level 판단:
  high: 문제-해결 흐름이 구체적이고 핵심 기여가 드러남
  medium: 행동/방법은 있으나 결과/영향이 약함
  low: 사용/참여 언급 수준(그래도 evidence는 반드시 있어야 함)

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

**job_queries 생성 예시:**
프로젝트: "E-commerce 백엔드 API 개발" (Python, Django, Redis 사용)
- A: "Python, Django, Redis 기반의 대규모 트래픽 처리 백엔드 개발자"
- B: "E-commerce 플랫폼 결제 시스템 및 재고 관리 API 개발 경험자"
- C: "MSA 아키텍처 전환 및 캐싱 전략 설계 경험이 있는 시니어 백엔드 개발자"
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
            
            # Safety: Ensure each project has at most 3 queries
            for project in result.user_data.projects:
                if len(project.job_queries) > 3:
                    project.job_queries = project.job_queries[:3]
                
                # safety for strengths
                if len(project.strengths) > 8:
                    project.strengths = project.strengths[:8]
                
                # remove strengths without evidence
                project.strengths = [
                    s for s in project.strengths if s.evidence and s.claim and s.tag
                ]
                
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
                            description_for_embedding=f"AI 응답 오류: {str(e)}\n\n(URL: {self.base_url}/v3/chat-completions/{self.model})\n\n원문 내용:\n{text[:500]}...",
                            job_queries=[]
                        )
                    ]
                )
            )

    async def refine_single_project(self, text: str, project_name_hint: str = None) -> Project:
        """
        Refine a single project's data. This is more efficient than full extraction 
        because we know there is only ONE project.
        """
        system_prompt = f"""
당신은 IT 전문 포트폴리오 분석가입니다.
제공된 텍스트(README 및 소스 코드 조각)를 분석하여 **단 하나의 프로젝트**에 대한 상세 정보를 추출하세요.

**분석 대상:** {project_name_hint or "주어진 프로젝트"}

**추출 항목:**
1. **project_name**: 가장 적합한 프로젝트 이름
2. **period**: 진행 기간 (없으면 null)
3. **role**: 주요 역할 및 담당 업무
4. **tech_stack**: 사용된 핵심 기술 스택 리스트
5. **description_for_embedding**: 아래 템플릿을 따라 작성
6. **strengths**: 이 프로젝트에서 드러난 강점(역량) 3~7개 (tag/claim/evidence/level)
7. **job_queries**: 이 프로젝트 경험을 바탕으로 지원 가능한 채용 공고 검색용 쿼리 3개 (A, B, C 타입)
   - A: 해당 프로젝트의 핵심 기술과 경험을 기반으로 한 메인 포지션
   - B: 해당 프로젝트의 부가 기술이나 도메인을 기반으로 한 서브 포지션
   - C: 해당 프로젝트 경험을 바탕으로 한 도전적 포지션

**description_for_embedding 작성 규칙 (필수):**
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
- "해결" 항목은 기술적 구현 방법을 포함해야 합니다 (소스 코드 조각이 있다면 특정 라이브러리, 알고리즘 등 상세히 반영)
- "결과"는 원문에 명시된 경우에만 작성하세요
- 정보가 부족하면 "미기재"로 표시하세요

**strengths 작성 규칙:**
- strengths.tag: [문제 해결, 주인의식, 책임감, 도전, 새로운 기술 적용, 새로운 방법으로 문제 해결, 실험/검증, 설계/구조화, 품질 개선, 성능 최적화, 협업, 커뮤니케이션, 프로젝트 리딩, 데이터/지표 기반 개선] 중 선택
- claim: 1문장 요약
- evidence: 원문 근거 구절 1~3개 (짧게 그대로)
- level: low, medium, high
"""
        user_prompt = f"[프로젝트 데이터]\n{text}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # We reuse Project's schema for Structured Output
        schema = Project.model_json_schema()
        
        try:
            response_text = await self._call_ncp(messages, response_schema=schema)
            project = Project.model_validate_json(response_text)
            
            if len(project.job_queries) > 3:
                project.job_queries = project.job_queries[:3]
                
            return project
        except Exception as e:
            logger.error(f"Single Project Refinement Failed: {e}")
            return Project(
                project_name=project_name_hint or "분석 실패 프로젝트",
                description_for_embedding=f"분석 오류: {str(e)}\n\n원문 일부:\n{text[:200]}...",
                job_queries=[]
            )

    async def update_global_user_profile(self, current_summary: str, current_job_title: str, new_project_info: str) -> dict:
        """
        Incrementally update the user's global profile summary and job title based on new project experience.
        """
        system_prompt = """
당신은 커리어 컨설턴트입니다.
사용자의 '기존 프로필 요약'과 '새로운 프로젝트 경험'을 받아서, 이를 통합하여 **더욱 전문적이고 포괄적인 새로운 프로필 요약**을 작성하세요.

**작성 규칙:**
1. **상호 보완적 통합**: 기존 내용에 새로운 경험을 자연스럽게 녹여내세요. 단순히 덧붙이지 말고 문단을 재구성하세요.
2. **직무명(Job Title) 업데이트**: 새로운 경험이 기존 직무보다 상위 레벨이거나 다른 분야라면, 가장 적합한 직무명을 제안하세요. (예: 백엔드 개발자 -> 풀스택 개발자, 주니어 -> 시니어 등)
3. **핵심 역량 강조**: 사용자의 기술 스택과 성과를 바탕으로 강점을 부각하세요.
4. **분량**: 3~5문장 내외로 간결하고 임팩트 있게 작성하세요.
5. **어조**: 신뢰감 있고 전문적인 어조("~함", "~임" 또는 "~합니다" 체)를 사용하세요.

**출력 형식 (JSON):**
{
    "summary": "새롭게 작성된 프로필 요약",
    "job_title": "업데이트된 희망 직무명"
}
"""
        user_prompt = f"""
[기존 프로필]
직무: {current_job_title or '미설정'}
요약: {current_summary or '없음'}

[새로 추가된 프로젝트 경험]
{new_project_info}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Simple schema for this call
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "job_title": {"type": "string"}
            },
            "required": ["summary", "job_title"]
        }

        try:
            response_text = await self._call_ncp(messages, response_schema=schema)
            import json
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Failed to update global profile: {e}")
            # Fallback: Just append raw info or keep existing
            return {
                "summary": (current_summary + "\n\n[New] " + new_project_info[:100] + "...") if current_summary else new_project_info[:200],
                "job_title": current_job_title
            }
