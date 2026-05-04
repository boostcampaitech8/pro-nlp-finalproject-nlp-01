from __future__ import annotations

import os
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, model_validator, field_validator
import logging
import asyncio

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

    # 프로젝트별 강점(역량)
    strengths: List[StrengthItem] = Field(
        default_factory=list,
        description="이 프로젝트에서 드러난 강점(역량) 3~7개 (근거 포함). 근거 없으면 빈 배열 가능.",
    )

    # 프로젝트별 공고 검색 쿼리 (A/B/C 3개 목표)
    job_queries: List[QueryItem] = Field(
        default_factory=list,
        description="이 프로젝트에 특화된 A/B/C 타입 채용 공고 검색 쿼리 3개 (권장: 정확히 3개)",
    )

    @model_validator(mode="before")
    @classmethod
    def check_aliases(cls, data: dict) -> dict:
        if isinstance(data, dict):
            # Handle 'title' -> 'project_name'
            if "project_name" not in data:
                if "title" in data:
                    data["project_name"] = data["title"]
                else:
                    data["project_name"] = "미기재 프로젝트"
        return data

    @field_validator("description_for_embedding", mode="before")
    @classmethod
    def validate_description(cls, v):
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        return v


class UserData(BaseModel):
    profile: Profile = Field(default_factory=Profile)
    projects: List[Project] = Field(
        default_factory=list,
        description="텍스트에서 추출된 모든 프로젝트 리스트 (각 프로젝트는 strengths/job_queries 포함)",
    )
    skills: List[str] = Field(default_factory=list, description="원문 근거 있는 핵심 역량 키워드만")


class CombinedResult(BaseModel):
    user_data: UserData


class LLMRefiner:
    """
    - refine_text(): (선택) 텍스트 정제(지금은 pass-through로 둬도 됨)
    - extract_user_data_and_queries(): 포트폴리오 텍스트를 스키마로 구조화 + 공고 검색 쿼리 생성 + 강점(역량) 추출
    """

    def __init__(
        self,
        model: str = "HCX-007",  # Changed to HCX-007 for Structured Outputs
        api_key_env: str = "NCP_CLOVASTUDIO_API_KEY",
    ) -> None:
        self.api_key = os.environ.get(api_key_env)
        base_url = (os.environ.get("NCP_CLOVASTUDIO_BASE_URL") or "").strip()
        if not base_url or not base_url.startswith(("http://", "https://")):
            if base_url and "." in base_url:
                base_url = f"https://{base_url}"
            else:
                base_url = "https://clovastudio.stream.ntruss.com"
        self.base_url = base_url
        self.model = model
        logger.info(
            f"LLMRefiner initialized with base_url: {self.base_url} and model: {self.model}"
        )

        if not self.api_key:
            print(f"Warning: {api_key_env} is not set. NCP features will work.")

    def refine_text(self, raw_text: str) -> str:
        """
        기존 파이프라인 호환용. 지금은 원문 그대로 반환.
        (나중에 요약/정리 등을 하고 싶으면 여기 구현)
        """
        return raw_text

    async def _call_ncp(
        self,
        messages: List[dict],
        response_schema: dict = None,
        max_tokens: int = 4096,
    ) -> str:
        """Call NCP Chat Completions V3 with Structured Outputs support and retries."""
        if not self.api_key:
            raise RuntimeError("NCP API Key is missing.")

        url = f"{self.base_url}/v3/chat-completions/{self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "messages": messages,
            "maxCompletionTokens": max_tokens,
            "temperature": 0.1,
            "topP": 0.8,
            "topK": 0,
            "thinking": {"effort": "none"},
        }

        # Add Structured Outputs if schema provided
        if response_schema:
            payload["responseFormat"] = {"type": "json", "schema": response_schema}

        import httpx

        max_retries = 5
        base_delay = 2.0

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 429:
                        wait_time = base_delay * (2**attempt)
                        logger.warning(
                            f"NCP Rate Limit (429) exceeded. Retrying in {wait_time}s... "
                            f"(Attempt {attempt+1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    res_json = response.json()

                    if res_json.get("status", {}).get("code") == "20000":
                        return (
                            res_json.get("result", {})
                            .get("message", {})
                            .get("content", "")
                        )
                    raise RuntimeError(f"NCP API Error: {res_json}")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait_time = base_delay * (2**attempt)
                    logger.warning(
                        f"NCP Rate Limit (429) hit via exception. Retrying in {wait_time}s... "
                        f"(Attempt {attempt+1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except (httpx.RequestError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                logger.warning(
                    f"NCP Network Error: {e}. Retrying... (Attempt {attempt+1}/{max_retries})"
                )
                await asyncio.sleep(base_delay * (2**attempt))
                continue

        raise RuntimeError(f"NCP API request failed after {max_retries} retries.")

    async def extract_user_data_and_queries(self, text: str) -> CombinedResult:
        """
        Extract structured user data and job queries from portfolio text using NCP Structured Outputs.
        Also extract project strengths(역량) with evidence.
        """
        system_prompt = """
당신은 포트폴리오 분석 전문가입니다.
사용자의 포트폴리오 텍스트를 분석하여 다음을 추출하세요:

1) 사용자 정보: 이름, 직무, 요약, 프로젝트 리스트, 기술 스택
2) 각 프로젝트마다:
   - strengths(강점/역량) 3~7개: tag/claim/evidence/level 포함
   - 채용 공고 검색 쿼리 3개 (A, B, C 타입)

========================
중요 규칙 (매우 중요)
========================
- 텍스트에 근거한 내용만 작성(추측/과장/확장 금지).
- 정보가 부족하면 null 또는 빈 배열로 둔다. 임의로 채우지 않는다.
- strengths / job_queries의 evidence에는 원문에서 근거가 된 구절을 1~3개 "짧게 그대로" 넣어라.
- evidence가 없는 strengths는 생성하지 않는다.
- 각 프로젝트는 가능하면 job_queries A/B/C를 정확히 3개 생성하되, 근거가 부족하면 빈 배열 허용.
  (단, 근거 없는 임의 생성은 금지)

========================
strengths 작성 가이드
========================
- strengths.tag는 아래 목록 중 원문 근거가 있는 것만 선택:
  문제 해결 / 주인의식 / 책임감 / 도전 / 새로운 기술 적용 / 새로운 방법으로 문제 해결 /
  실험/검증 / 설계/구조화 / 품질 개선 / 성능 최적화 / 협업 / 커뮤니케이션 /
  프로젝트 리딩 / 데이터/지표 기반 개선

- claim: "이 프로젝트에서 내가 어떻게 그 역량을 보여줬는지"를 1문장으로 작성.
- level 판단:
  high: 문제-해결 흐름이 구체적이고 핵심 기여가 드러남
  medium: 행동/방법은 있으나 결과/영향이 약함
  low: 사용/참여 언급 수준(그래도 evidence는 반드시 있어야 함)

========================
description_for_embedding 작성 규칙
========================
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

주의:
- "결과/성과"를 원문에 없는데 생성하지 마라.
- 정보가 부족하면 "미기재"로 표시.

========================
job_queries 생성 규칙
========================
각 프로젝트마다 A/B/C 쿼리를 만들되, 프로젝트 기술 스택/역할/문제 해결 맥락에 기반해 작성.
- A: 핵심 기술 + 핵심 역할 중심
- B: 문제 해결/도메인/부가 기술 중심
- C: 프로젝트 맥락(목적/기능/기여) 중심
- 각 query는 한 문장(너무 길지 않게)
- A/B/C는 관점이 겹치지 않게
"""

        user_prompt = f"""
[포트폴리오 텍스트]
{text}
""".strip()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        schema = CombinedResult.model_json_schema()

        try:
            response_text = await self._call_ncp(messages, response_schema=schema)

            # With Structured Outputs, response is guaranteed valid JSON
            result = CombinedResult.model_validate_json(response_text)

            # Safety: Ensure each project has at most 3 queries & evidence rules
            for project in result.user_data.projects:
                if len(project.job_queries) > 3:
                    project.job_queries = project.job_queries[:3]

                # (선택) strengths도 너무 많으면 컷
                if len(project.strengths) > 8:
                    project.strengths = project.strengths[:8]

                # evidence 없는 strengths 제거(안전)
                project.strengths = [
                    s for s in project.strengths if s.evidence and s.claim and s.tag
                ]

                # (선택) A/B/C 중복 타입 정리(앞에서부터 하나씩만 남김)
                seen = set()
                uniq_queries = []
                for q in project.job_queries:
                    if q.type in seen:
                        continue
                    seen.add(q.type)
                    uniq_queries.append(q)
                project.job_queries = uniq_queries

            return result

        except Exception as e:
            logger.error(f"NCP LLM Generation Failed: {e}")
            raw_response = locals().get("response_text", "No response")
            logger.error(f"Raw Response: {raw_response}")

            # Fallback if AI fails (스키마에 맞춰서 최소 구성)
            return CombinedResult(
                user_data=UserData(
                    profile=Profile(summary="AI 분석에 실패했습니다. (원문 참조)"),
                    projects=[
                        Project(
                            project_name="추출 실패",
                            description_for_embedding=(
                                f"AI 응답 오류: {str(e)}\n\n"
                                f"(URL: {self.base_url}/v3/chat-completions/{self.model})\n\n"
                                f"원문 내용:\n{text[:500]}..."
                            ),
                            strengths=[],
                            job_queries=[],
                        )
                    ],
                    skills=[],
                )
            )

    async def update_global_user_profile(
        self, current_summary: str, current_job_title: str, new_project_info: str
    ) -> dict:
        """
        Incrementally update the user's global profile summary and job title based on new project experience.
        """
        system_prompt = """
당신은 커리어 컨설턴트입니다.
사용자의 '기존 프로필 요약'과 '새로운 프로젝트 경험'을 받아서, 이를 통합하여
더욱 전문적이고 포괄적인 새로운 프로필 요약을 작성하세요.

작성 규칙:
1. 상호 보완적 통합: 기존 내용에 새로운 경험을 자연스럽게 녹여내세요.
2. 직무명(Job Title) 업데이트: 가장 적합한 직무명을 제안하세요.
3. 핵심 역량 강조: 기술 스택과 성과를 바탕으로 강점을 부각하세요.
4. 분량: 3~5문장 내외.
5. 어조: 신뢰감 있고 전문적인 어조.

출력 형식(JSON):
{
  "summary": "새롭게 작성된 프로필 요약",
  "job_title": "업데이트된 희망 직무명"
}
""".strip()

        user_prompt = f"""
[기존 프로필]
직무: {current_job_title or '미설정'}
요약: {current_summary or '없음'}

[새로 추가된 프로젝트 경험]
{new_project_info}
""".strip()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "job_title": {"type": "string"},
            },
            "required": ["summary", "job_title"],
        }

        try:
            response_text = await self._call_ncp(messages, response_schema=schema)
            import json

            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Failed to update global profile: {e}")
            return {
                "summary": (
                    (current_summary + "\n\n[New] " + new_project_info[:100] + "...")
                    if current_summary
                    else new_project_info[:200]
                ),
                "job_title": current_job_title,
            }
