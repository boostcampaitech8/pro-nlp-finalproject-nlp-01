import os
import json
import logging
from typing import Dict, List, Any, Optional

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
            "maxTokens": max_tokens,
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
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                res_json = response.json()
                
                # Check status
                if res_json.get("status", {}).get("code") == "20000":
                    return res_json.get("result", {}).get("message", {}).get("content", "")
                else:
                    logger.error(f"NCP API Error: {res_json}")
                    return ""
        except httpx.HTTPStatusError as e:
            logger.error(f"NCP API HTTP Error: {e.response.status_code} - {e.response.text}")
            return ""
        except Exception as e:
            logger.error(f"NCP API Call Failed: {e}")
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
        
        try:
            # Replaced blocking requests with httpx
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, json=payload)
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
                logger.warning(f"NCP Reranker returned non-20000 code: {res_json.get('status')}")
                return candidates[:top_n]
        except Exception as e:
            logger.error(f"NCP Reranker failed: {e}")
            return candidates[:top_n]

    async def rank_and_reason(self, portfolio_data: Dict, candidates: List[Any]) -> List[Dict]:
        """
        Re-ranks vector search results using NCP HCX and provides personalized recommendation reasons.
        """
        if not candidates:
            return []

        candidate_summaries = []
        # Store index to retrieve full metadata later
        for i, doc in enumerate(candidates):
            meta = doc.metadata
            summary = (
                f"[공고 {i}]\n"
                f"회사: {meta.get('company')}\n"
                f"직무: {meta.get('title')}\n"
                f"주요 업무: {(meta.get('key_responsibilities') or '')[:200]}...\n"
                f"자격 요건: {(meta.get('required_qualifications') or '')[:200]}...\n"
                f"우대 사항: {(meta.get('preferred_qualifications') or '')[:200]}...\n"
                f"경험 수준: {meta.get('experience') or ''}\n"
                f"학력: {meta.get('education') or ''}\n"
                "-------------------\n"
            )
            candidate_summaries.append(summary)

        system_prompt = """
        당신은 전문 채용 컨설턴트입니다. 
        사용자의 포트폴리오와 공고 후보군을 비교하여, 가장 적합한 TOP 3 공고를 선정하고 추천 사유를 작성하세요.
        
        응답은 반드시 'recommendations' 키를 가진 JSON 객체여야 합니다. 
        각 추천 아이템은 'index'와 'reason' 필드를 가져야 합니다.
        """

        user_prompt = f"""
        [사용자 데이터]
        {json.dumps(portfolio_data, ensure_ascii=False)}

        [후보 공고 리스트]
        {"".join(candidate_summaries)}
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
                            "index": {"type": "integer"},
                            "reason": {"type": "string"}
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

        response_text = await self._call_ncp_chat_completion(messages, max_tokens=4096, response_schema=schema)

        try:
            res_json = json.loads(response_text)
            recs = res_json.get("recommendations", [])
            
            final_results = []
            for r in recs:
                idx = r.get("index")
                if idx is not None and 0 <= idx < len(candidates):
                    # Combine original metadata with the AI reason
                    item = dict(candidates[idx].metadata)
                    item["reason"] = r.get("reason", "매칭 사유를 생성하지 못했습니다.")
                    
                    # Calculate Score from distance
                    dist = item.get("distance")
                    if dist is not None:
                        try:
                            # Cosine distance to similarity score
                            # distance usually 0 to 2. Score 0 to 1.
                            # Sim = 1 - dist (approx for normalized). Or 1 - (dist/2)?
                            # Let's use 1 - distance. If distance is small (0.1), score is 0.9.
                            item["score"] = max(0.0, 1.0 - float(dist))
                        except:
                            item["score"] = None
                    else:
                        item["score"] = None # No score available (fallback search)

                    # Also include content if needed
                    item["content_snippet"] = candidates[idx].page_content[:500]
                    final_results.append(item)
            
            return final_results
        except Exception as e:
            logger.error(f"Error in reranking parsing: {e}, Raw: {response_text}")
            return []
