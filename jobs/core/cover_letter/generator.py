import json
import logging
import re
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from common.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai
from jobs.core.cover_letter.prompts import (
    GAP_ANALYSIS_PROMPT, 
    RESUME_GENERATION_PROMPT, 
    SIMPLE_RESUME_PROMPT,
    QUESTION_BASED_RESUME_PROMPT,
    QUESTION_BASED_OUTLINE_PROMPT,
    HEADLINE_GENERATION_PROMPT,
    SUBHEADING_REFINEMENT_PROMPT
)
from jobs.core.cover_letter.schemas import GapAnalysisResult, ResumeGenerationResult, ResumeOutlineResult, HeadlineGenerationResult
from jobs.core.cover_letter.config import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    LLM_REPETITION_PENALTY,
    LLM_MAX_TOKENS,
    LLM_USE_THINKING,
    LLM_THINKING_LEVEL
)

logger = logging.getLogger(__name__)

class CoverLetterGenerator:
    """
    Handles AI interactions for Cover Letter generation using HyperCLOVA X.
    Migrated from llm-pipeline to use ChatOpenAI (OpenAI-compatible API).
    """
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            api_key = settings.NCP_CLOVASTUDIO_API_KEY
            if not api_key:
                logger.error("NCP_CLOVASTUDIO_API_KEY is not set. AI features will not work.")
                raise ValueError("NCP API Key is missing")
            
            # Use ChatOpenAI with HyperCLOVA OpenAI-compatible endpoint
            # 설정값은 jobs/core/cover_letter/config.py에서 관리
            extra_params = {
                "topP": LLM_TOP_P,
                "repetitionPenalty": LLM_REPETITION_PENALTY,
                "maxTokens": LLM_MAX_TOKENS
            }

            # Thinking 기능 활성화 (HCX-007)
            if LLM_USE_THINKING:
                # v3 API 명세 반영
                # 1. maxTokens 사용 불가 -> 제거
                if "maxTokens" in extra_params:
                    del extra_params["maxTokens"]
                    
                # 2. maxCompletionTokens 설정 (High 기준 권장값 20480 또는 사용자 설정)
                extra_params["maxCompletionTokens"] = LLM_MAX_TOKENS # 또는 20480
                
                # 3. thinking.effort 설정
                extra_params["thinking"] = {
                    "effort": LLM_THINKING_LEVEL  # v3 명세: 'effort' (low, medium, high)
                }

            self._llm = ChatOpenAI(
                model=LLM_MODEL,
                api_key=api_key,
                base_url="https://clovastudio.stream.ntruss.com/v1/openai",
                temperature=LLM_TEMPERATURE,
                extra_body=extra_params
            )
        return self._llm

    def _parse_json_response(self, response_text: str, pydantic_class):
        """
        LLM 응답에서 JSON을 추출하여 Pydantic 객체로 변환
        (llm-pipeline의 parse_json_response와 동일)
        """
        text = response_text
        
        # 1. JSON 블록 추출 시도 (```json ... ``` 또는 ``` ... ```)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        else:
            # 2. 중괄호로 시작하고 끝나는 부분 추출
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group(0)
        
        try:
            data = json.loads(text)
            return pydantic_class(**data)
        except (json.JSONDecodeError, Exception) as e:
            raise ValueError(f"JSON 파싱 실패: {str(e)}\n원본: {response_text[:500]}")

    def _format_experiences(self, documents: List) -> str:
        """
        문서 리스트를 LLM 입력용 텍스트로 포맷팅
        (llm-pipeline의 format_experiences와 동일)
        """
        from langchain_core.documents import Document
        
        formatted_parts = []
        for doc in documents:
            if isinstance(doc, Document):
                project_name = doc.metadata.get('project_name', 'N/A')
                role = doc.metadata.get('role', 'N/A')
                tech_stack = doc.metadata.get('stack', doc.metadata.get('tech_stack', 'N/A'))
                
                # tech_stack이 리스트인 경우 문자열로 변환
                if isinstance(tech_stack, list):
                    tech_stack = ', '.join(tech_stack)
                
                formatted_parts.append(
                    f"[프로젝트: {project_name}]\n"
                    f"역할: {role}\n"
                    f"기술스택: {tech_stack}\n"
                    f"내용:\n{doc.page_content}"
                )
            else:
                # Document가 아닌 경우 그냥 문자열로 처리
                formatted_parts.append(str(doc))
        
        return "\n\n---\n\n".join(formatted_parts)

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=20)
    )
    def analyze_gap(self, user_context: str, job_req: str) -> Dict[str, Any]:
        """
        Analyzes the gap between user experience and job requirements.
        Returns a dict compatible with GapAnalysisResult schema.
        """
        parser = PydanticOutputParser(pydantic_object=GapAnalysisResult)
        
        prompt = PromptTemplate(
            template=GAP_ANALYSIS_PROMPT,
            input_variables=["job_req", "user_context"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        # LLM 호출 후 수동 파싱 (llm-pipeline 방식)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({"job_req": job_req, "user_context": user_context})
            response_text = response.content if hasattr(response, 'content') else str(response)
            result = self._parse_json_response(response_text, GapAnalysisResult)
            return result.model_dump()
        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            # Return empty/safe default to prevent crash
            return {
                "is_gap_found": False, 
                "matching_points": [], 
                "missing_elements": [], 
                "question_to_user": "", 
                "reasoning": "분석에 실패했습니다."
            }

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=20)
    )
    def generate_answer(
        self, 
        company_name: str, 
        job_title: str, 
        question: str, 
        context: str, 
        gap_analysis: Dict[str, Any], 
        tone: str,
        core_values: str = "",
        max_length: int = 1000,
        used_experiences: List[str] = None,
        subheading: bool = False,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generates a cover letter answer for a specific question.
        Supports 3-way prompt selection based on question and gap analysis.
        """
        # used_experiences 경고 텍스트 생성 (llm-pipeline 방식)
        used_exp_warning = ""
        if used_experiences:
            used_exp_warning = f"\n\n⚠️ 다음 경험/프로젝트는 이전 문항에서 이미 사용했으므로 다른 경험을 우선 사용하세요: {', '.join(used_experiences)}"
        
        # 소제목 지침 설정 (llm-pipeline 방식)
        subheading_instruction = ""
        if subheading:
            subheading_instruction = """
### [소제목 필수 작성]
- 답변의 핵심 성과나 가치를 요약하는 매력적인 소제목을 작성하세요.
- 소제목은 JSON 출력의 **'title'** 필드에 넣으세요.
- **매우 중요**: 소제목에 대괄호 `[` `]`나 특수문자를 절대 사용하지 마세요. (코드에서 자동으로 추가합니다)
- **주의**: 본문('content')의 첫 줄에 소제목을 중복해서 적지 마세요. 본문은 바로 내용으로 시작하세요.
- 예시: 'title': "데이터 기반의 의사결정으로 결제 전환율 15% 개선"
"""
        else:
            subheading_instruction = """
### [소제목 작성 금지]
- 소제목을 작성하지 마세요.
- JSON 출력의 **'title'** 필드는 빈 문자열("")로 비워두세요.
"""

        # Determine which prompt to use
        if question:
            # Question-based prompt
            template = QUESTION_BASED_RESUME_PROMPT
            input_vars = {
                "company_name": company_name,
                "core_values": core_values,
                "job_title": job_title,
                "user_experiences": context + used_exp_warning,  # 경고 추가
                "question": question,
                "max_length": max_length,
                "matching_points": ", ".join(gap_analysis.get("matching_points", [])) if gap_analysis.get("matching_points") else "해당 없음",
                "missing_elements": ", ".join(gap_analysis.get("missing_elements", [])) if gap_analysis.get("missing_elements") else "해당 없음",
                "subheading_instruction": subheading_instruction
            }
        elif gap_analysis.get("is_gap_found"):
            # Gap analysis-based prompt
            template = RESUME_GENERATION_PROMPT
            input_vars = {
                "company_name": company_name,
                "core_values": core_values,
                "job_title": job_title,
                "user_experiences": context + used_exp_warning,  # 경고 추가
                "max_length": max_length,
                "matching_points": ", ".join(gap_analysis.get("matching_points", [])),
                "missing_elements": ", ".join(gap_analysis.get("missing_elements", [])),
                "subheading_instruction": subheading_instruction
            }
        else:
            # Simple prompt
            template = SIMPLE_RESUME_PROMPT
            input_vars = {
                "company_name": company_name,
                "core_values": core_values,
                "job_title": job_title,
                "user_experiences": context + used_exp_warning,  # 경고 추가
                "max_length": max_length,
                "subheading_instruction": subheading_instruction
            }
        
        parser = PydanticOutputParser(pydantic_object=ResumeGenerationResult)
        prompt = PromptTemplate(
            template=template,
            input_variables=list(input_vars.keys()),
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        # LLM 호출 후 수동 파싱
        chain = prompt | self.llm
        
        try:
            response = chain.invoke(input_vars)
            response_text = response.content if hasattr(response, 'content') else str(response)
            result = self._parse_json_response(response_text, ResumeGenerationResult)
            return result.model_dump()
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=20)
    )
    def generate_outline(
        self, 
        company_name: str, 
        job_title: str, 
        question: str, 
        context: str, 
        gap_analysis: Dict[str, Any],
        core_values: str = ""
    ) -> Dict[str, Any]:
        """
        Generates a structural outline for the cover letter instead of full text.
        """
        parser = PydanticOutputParser(pydantic_object=ResumeOutlineResult)
        
        # Format gap analysis for prompt
        matching_points = ", ".join(gap_analysis.get("matching_points", []))
        missing_elements = ", ".join(gap_analysis.get("missing_elements", []))

        prompt = PromptTemplate(
            template=QUESTION_BASED_OUTLINE_PROMPT,
            input_variables=["company_name", "job_title", "question", "user_experiences", "matching_points", "missing_elements", "core_values"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        # LLM 호출 후 수동 파싱
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "company_name": company_name,
                "job_title": job_title,
                "question": question,
                "user_experiences": context,
                "matching_points": matching_points,
                "missing_elements": missing_elements,
                "core_values": core_values
            })
            response_text = response.content if hasattr(response, 'content') else str(response)
            result = self._parse_json_response(response_text, ResumeOutlineResult)
            return result.model_dump()
        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=20)
    )
    def generate_headline(self, content: str) -> str:
        """
        Generates a compelling headline for a cover letter content.
        """
        parser = PydanticOutputParser(pydantic_object=HeadlineGenerationResult)
        
        prompt = PromptTemplate(
            template=HEADLINE_GENERATION_PROMPT,
            input_variables=["content"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({"content": content})
            response_text = response.content if hasattr(response, 'content') else str(response)
            result = self._parse_json_response(response_text, HeadlineGenerationResult)
            return result.headline
        except Exception as e:
            logger.error(f"Headline generation failed: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=20)
    )
    def refine_with_subheadings(self, text: str) -> str:
        """
        Refines the text by adding subheadings using AI.
        Returns the refined text with markdown headers.
        """
        prompt = PromptTemplate(
            template=SUBHEADING_REFINEMENT_PROMPT,
            input_variables=["text"]
        )
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({"text": text})
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Refinement with subheadings failed: {e}")
            raise
