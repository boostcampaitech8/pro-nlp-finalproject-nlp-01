import os
import json
import logging
from typing import Dict, List, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

logger = logging.getLogger(__name__)

class RecruitMatcher:
    """
    Handles AI-powered matching between user portfolios and recruitment postings.
    Generates optimized search queries and re-ranks results with reasoning using NCP HyperCLOVA X.
    """
    def __init__(self, model_id: str = "HCX-007"):
        self.ncp_api_key = os.getenv("NCP_CLOVASTUDIO_API_KEY")
        base_url = os.getenv("NCP_CLOVASTUDIO_BASE_URL", "").strip()
        
        # Ensure URL has proper protocol
        if not base_url or not base_url.startswith(("http://", "https://")):
            base_url = "https://clovastudio.stream.ntruss.com"
            logger.warning(f"NCP_CLOVASTUDIO_BASE_URL is missing or invalid. Using default: {base_url}")
        
        self.ncp_base_url = base_url
        self.model_id = model_id # Default to HCX-005
        
        if not self.ncp_api_key:
            logger.warning("NCP_CLOVASTUDIO_API_KEY is not set. AI features will be disabled.")

    async def _call_ncp_chat_completion(self, messages: List[Dict], max_tokens: int = 4096, **kwargs) -> str:
        """
        Helper to call NCP Chat Completion v3 API.
        """
        url = f"{self.ncp_base_url}/v3/chat-completions/{self.model_id}"
        headers = {
            "Authorization": f"Bearer {self.ncp_api_key}",
            # "X-NCP-CLOVASTUDIO-API-KEY": self.ncp_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "messages": messages,
            "maxCompletionTokens": max_tokens,
            "temperature": 0.5,
            "topP": 0.8,
            "topK": 0
        }
        
        # Add Structured Outputs if requested (for HCX-007)
        if "response_schema" in kwargs:
            payload["responseFormat"] = {
                "type": "json",
                "schema": kwargs["response_schema"]
            }
            payload["thinking"] = {"effort": "none"}

        import httpx
        import asyncio
        import random

        return await self._execute_chat_completion(url, headers, payload)

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, RuntimeError)), 
        stop=stop_after_attempt(5), 
        wait=wait_exponential(multiplier=4, min=4, max=60)
    )
    async def _execute_chat_completion(self, url: str, headers: dict, payload: dict) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 429 or response.status_code >= 500:
                 response.raise_for_status()

            response.raise_for_status()
            res_json = response.json()
            
            if res_json.get("status", {}).get("code") == "20000":
                return res_json.get("result", {}).get("message", {}).get("content", "")
            else:
                status_code = res_json.get("status", {}).get("code")
                if status_code == "42901":
                     raise RuntimeError(f"NCP Rate Limit (42901)")
                    
                logger.error(f"NCP API Error: {res_json}")
                return ""

    async def generate_search_queries(self, portfolio_data: Dict) -> Dict[str, str]:
        """
        Analyzes portfolio to generate 3 types of search queries using NCP.
        """
        system_prompt = """
        당신은 AI 기반 채용 매칭 전문가입니다. 
        사용자의 정보를 분석하여 검색 엔진에서 가장 적합한 공고를 찾기 위한 3가지 검색 쿼리를 생성하세요.
        
        필수 유형:
        1. query_a (기술 스택 중심): 언어, 프레임워크, 기술 도구 및 핵심 역량
        2. query_b (성과 중심): 프로젝트 성과, 문제 해결 경험, 수치적 성과
        3. query_c (경험 요약): 주요 도메인 경험 및 전반적인 업무 요약
        
        응답은 반드시 아래 JSON 형식으로만 작성하세요. 다른 말은 포함하지 마세요.
        {
            "query_a": "...",
            "query_b": "...",
            "query_c": "..."
        }
        """
        
        user_input = f"사용자 포트폴리오 데이터:\n{json.dumps(portfolio_data, ensure_ascii=False)}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        response_text = await self._call_ncp_chat_completion(messages)
        
        try:
            # Clean up potential markdown formatting
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned_text)
        except Exception as e:
            logger.error(f"Error parsing NCP response: {e}, Raw: {response_text}")
            # Fallback
            job_title = portfolio_data.get("extracted_job_title", "개발자")
            return {
                "query_a": f"{job_title} 기술 스택 역량",
                "query_b": f"{job_title} 프로젝트 해결 성과",
                "query_c": f"{job_title} 업무 경험 요약"
            }

    async def rerank_with_ncp(self, query: str, candidates: List[Any], top_n: int = 5) -> List[Any]:
        """
        Refines candidate list using NCP Clova Reranker.
        Documentation: https://guide.ncloud-docs.com/docs/clovastudio-reranker
        """
        if not candidates or not self.ncp_api_key:
            return candidates[:top_n]
            
        url = f"{self.ncp_base_url}/v1/api-tools/reranker"
        
        # Prepare documents for NCP (id, doc)
        ncp_docs = []
        for i, doc in enumerate(candidates):
            ncp_docs.append({
                "id": str(i),
                "doc": doc.page_content[:5000] # Limiting size per doc
            })
            
        payload = {
            "documents": ncp_docs,
            "query": query,
            "maxTokens": 4096
        }
        
        headers = {
            "Authorization": f"Bearer {self.ncp_api_key}",
            "Content-Type": "application/json"
        }
        
        import httpx
        import asyncio
        import random

        try:
            return await self._execute_rerank(url, headers, payload, candidates, top_n)
        except Exception as e:
            logger.error(f"NCP Reranker final failure: {e}")
            return candidates[:top_n]

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, RuntimeError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=4, min=4, max=60)
    )
    async def _execute_rerank(self, url, headers, payload, candidates, top_n):
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            
            if res.status_code == 429 or res.status_code >= 500:
                res.raise_for_status()
            
            res.raise_for_status()
            res_json = res.json()
        
        if res_json.get("status", {}).get("code") == "20000":
            # Get cited documents
            cited = res_json.get("result", {}).get("citedDocuments", [])
            if not cited:
                return candidates[:top_n]
            
            cited_indices = []
            for c in cited:
                try:
                    idx = int(c.get("id"))
                    cited_indices.append(idx)
                except:
                    continue
            
            # Filter original candidates while maintaining order of citation
            refined = []
            seen_idx = set()
            for idx in cited_indices:
                if idx < len(candidates) and idx not in seen_idx:
                    refined.append(candidates[idx])
                    seen_idx.add(idx)
            
            return refined[:top_n]
        else:
            status_code = res_json.get("status", {}).get("code")
            if status_code == "42901":
                 raise RuntimeError(f"NCP Reranker Rate Limit (42901)")

            logger.warning(f"NCP Reranker returned non-20000 code: {res_json.get('status')}")
            return candidates[:top_n]

    async def rank_final_recommendations(self, portfolio_data: Dict, candidates: List[Any], top_n: int = 10) -> List[Dict]:
        """
        Final ranking of candidates using LLM with personalized reasoning.
        Ported/Adapted from llm-pipeline's rank_final_recommendations.
        """
        if not candidates:
            return []

        # Limit candidates for LLM context window
        candidates = candidates[:30]

        candidate_texts = []
        for i, doc in enumerate(candidates):
            meta = doc.metadata
            summary = (
                f"[공고 {i+1}]\n"
                f"회사: {meta.get('company')}\n"
                f"직무: {meta.get('title')}\n"
                f"주요업무: {doc.page_content[:800]}\n"
                "-------------------\n"
            )
            candidate_texts.append(summary)

        system_prompt = """
        당신은 정교한 매칭을 수행하는 IT 전문 채용 컨설턴트입니다. 
        사용자의 포트폴리오와 검색된 공고 후보군을 비교하여, 사용자의 성장에 가장 도움이 될 만한 최적의 공고를 선정하고 추천 사유를 작성하세요.
        """

        user_prompt = f"""
        아래 사용자의 포트폴리오와 검색된 공고 후보군을 비교하여, 가장 적합한 TOP {top_n} 공고를 선정하고 추천 사유를 작성해주세요.

        [사용자 데이터]
        {json.dumps(portfolio_data, ensure_ascii=False)}

        [후보 공고 리스트]
        {"".join(candidate_texts)}

        ### 요구 사항:
        1. 후보군 중에서 사용자의 기술 스택, 프로젝트 성과, 강점에 가장 잘 맞는 공고를 최대 {top_n}개 선정하세요.
        2. 각 추천 공고마다 왜 이 공고가 사용자에게 적합한지 '추천 사유'를 매우 구체적으로 작성하세요. 
           (예: "사용자의 Redis 캐싱 최적화 경험이 이 공고의 '대규모 트래픽 처리' 요구사항에 매우 적합합니다")
        3. 반드시 JSON 형식으로 응답하세요.
        """

        # Define schema for HCX-007 Structured Outputs
        schema = {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer", "description": "공고 리스트에서의 인덱스 (1부터 시작)"},
                            "reason": {"type": "string", "description": "구체적인 추천 사유"}
                        },
                        "required": ["index", "reason"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["recommendations"],
            "additionalProperties": False
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response_text = await self._call_ncp_chat_completion(messages, max_tokens=8000, response_schema=schema)
            res_json = json.loads(response_text)
            recs = res_json.get("recommendations", [])
            
            final_results = []
            for r in recs:
                # index is 1-based in prompt
                idx = r.get("index", 0) - 1
                if 0 <= idx < len(candidates):
                    # Combine original metadata with the AI reason
                    item = dict(candidates[idx].metadata)
                    item["reason"] = r.get("reason", "매칭 사유를 생성하지 못했습니다.")
                    
                    # Ensure reason is stored as a list if the database expects it
                    # In common/models.py, Recommendation.reason is JSON (List of strings)
                    if isinstance(item["reason"], str):
                        item["reason"] = [item["reason"]]
                        
                    final_results.append(item)
            
            return final_results
        except Exception as e:
            logger.error(f"Error in rank_final_recommendations parsing: {e}, Raw: {response_text}")
            return []
