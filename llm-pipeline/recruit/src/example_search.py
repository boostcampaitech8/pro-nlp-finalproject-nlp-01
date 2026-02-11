import sys
import os
import json
import traceback
import asyncio 
import httpx
import random
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from query_creator import QueryCreator
from recruit_indexer import RecruitIndexer

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, "..", "..", ".env") # src/../.. -> recruit/.env
load_dotenv(dotenv_path=env_path)

class Tee(object):
    """터미널 출력과 파일 쓰기를 동시에 수행하는 클래스"""
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

class ClovaMatcher:
    """
    Handles AI-powered matching between user portfolios and recruitment postings using NCP HyperCLOVA X.
    """
    def __init__(self, model_id: str = "HCX-007"):
        self.ncp_api_key = os.getenv("CLOVA_STUDIO_API_KEY")
        base_url = os.getenv("NCP_CLOVASTUDIO_BASE_URL", "").strip()
        
        # Ensure URL has proper protocol
        if not base_url or not base_url.startswith(("http://", "https://")):
            base_url = "https://clovastudio.stream.ntruss.com"
            # print(f"Warning: NCP_CLOVASTUDIO_BASE_URL is missing or invalid. Using default: {base_url}")
        
        self.ncp_base_url = base_url
        self.model_id = model_id
        
        if not self.ncp_api_key:
            print("Warning: CLOVA_STUDIO_API_KEY is not set. AI features will be disabled.")

    async def _call_ncp_chat_completion(self, messages: List[Dict], max_tokens: int = 4096, **kwargs) -> str:
        """
        Helper to call NCP Chat Completion v3 API.
        """
        url = f"{self.ncp_base_url}/v3/chat-completions/{self.model_id}"
        headers = {
            "Authorization": f"Bearer {self.ncp_api_key}",
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

        max_retries = 3
        base_delay = 2.0

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            print(f"NCP Matcher API returned {response.status_code}. Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        
                    response.raise_for_status()
                    res_json = response.json()
                    
                    if res_json.get("status", {}).get("code") == "20000":
                        return res_json.get("result", {}).get("message", {}).get("content", "")
                    else:
                        status_code = res_json.get("status", {}).get("code")
                        if status_code == "42901" and attempt < max_retries:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            print(f"NCP Matcher business error {status_code}. Retrying in {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            continue
                            
                        print(f"NCP API Error: {res_json}")
                        return ""
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"NCP Matcher connection error: {e}. Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    print(f"NCP Matcher API Call Final Failure: {e}")
                    return ""
        return ""

    async def rerank_with_ncp(self, query: str, candidates: List[Any], top_n: int = 5) -> List[Any]:
        """
        Refines candidate list using NCP Clova Reranker.
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
        
        max_retries = 3
        base_delay = 2.0

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(url, headers=headers, json=payload)
                    
                    if res.status_code == 429 or res.status_code >= 500:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            print(f"NCP Reranker API returned {res.status_code}. Retrying in {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            continue
                    
                    res.raise_for_status()
                    res_json = res.json()
                    
                if res_json.get("status", {}).get("code") == "20000":
                    result_data = res_json.get("result", {})
                    
                    # Get cited documents
                    cited = result_data.get("citedDocuments", [])

                    if not cited:
                        print(f"No cited documents found in NCP Reranker response. (Attempt{attempt + 1}/{max_retries})")
                        if attempt < max_retries:
                            await asyncio.sleep(base_delay)
                            continue
                        else:
                            return [] # 3회 연속 빈 칸일 경우 빈 리스트 반환
                    
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
                    if status_code == "42901" and attempt < max_retries:
                         delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                         print(f"NCP Reranker business error {status_code}. Retrying in {delay:.2f}s...")
                         await asyncio.sleep(delay)
                         continue

                    print(f"NCP Reranker returned non-20000 code: {res_json.get('status')}")
                    if attempt < max_retries:
                        await asyncio.sleep(base_delay)
                        continue
                    return []
            except Exception as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"NCP Reranker technical error: {e}. Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    print(f"NCP Reranker final failure: {e}")
                    return []
        return []

    async def rank_and_reason(self, portfolio_data: Dict, candidates: List[Any]) -> List[Dict]:
        """
        Re-ranks vector search results using NCP HCX and provides personalized recommendation reasons.
        """
        if not candidates:
            return []

        if not self.ncp_api_key:
            print("Warning: API Key missing, skipping AI reasoning.")
            fallback = []
            for doc in candidates[:3]:
                item = dict(doc.metadata)
                item['reason'] = "AI reasoning unavailable (No API Key)"
                fallback.append(item)
            return fallback

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
        사용자의 포트폴리오와 공고 후보군을 비교하여, 가장 적합한 TOP 5 공고를 선정하고 추천 사유를 작성하세요.
        
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
                    
                    # Also include content if needed
                    item["content_snippet"] = candidates[idx].page_content[:500]
                    final_results.append(item)
            
            return final_results
        except Exception as e:
            print(f"Error in reranking parsing: {e}, Raw: {response_text}")
            return []

def aggregate_by_rrf_variant(all_candidates, threshold=1.2, k=1.0):
    """
    3. RRF(Reciprocal Rank Fusion) 변형 방식
    - 여러 쿼리에서의 순위와 점수를 종합적으로 고려 (가장 정교함)
    """
    temp_map = {}
    for doc, score in all_candidates:
        if score > threshold: continue
        uid = doc.metadata.get('unique_id')
        if not uid: continue
        
        if uid not in temp_map:
            temp_map[uid] = {'doc': doc, 'scores': [score]}
        else:
            temp_map[uid]['scores'].append(score)
            
    unique_candidates = {}
    for uid, data in temp_map.items():
        # RRF 점수 계산: Σ(1 / (k + score_i))
        rrf_sum = sum(1.0 / (k + s) for s in data['scores'])
        
        # 다시 '낮을수록 좋음' 체계로 맞추기 위해 역수를 취함
        final_score = 1.0 / rrf_sum if rrf_sum > 0 else threshold
        unique_candidates[uid] = {'doc': data['doc'], 'score': final_score}
        
    return unique_candidates

async def run_search():
    # 1. 사용자 데이터 정의 (예시)
    user_data = {
    "profile": {
        "user_id": "USER_001",
        "name": "김준비",
        "job_title": "Backend Developer (3년차)",
        "summary": "트래픽이 몰리는 상황에서의 시스템 안정성을 최우선으로 생각하며, 비동기 아키텍처를 통해 성능을 극대화한 경험이 있습니다."
    },
    "projects": [
        {
            "project_name": "이커머스 타임세일 선착순 시스템 구축",
            "period": "2024.01 - 2024.06",
            "role": "Backend Lead",
            "tech_stack": ["Python", "FastAPI", "Redis", "Kafka", "Docker"],
            # RAG 임베딩의 핵심이 될 상세 설명 (Chunking 대상)
            "description_for_embedding": """
            [문제 상황]
            특가 이벤트 오픈 시 순간적으로 트래픽이 몰려 서버가 다운되고, 동기 방식의 주문 처리로 인해 응답 지연(Latency)이 3초 이상 발생하는 문제가 있었습니다.

            [해결 과정: 대용량 트래픽 처리]
            초당 10,000건(10,000 TPS)의 동시 접속 요청을 감당하기 위해 Redis Sorted Set 기반의 '대기열 시스템'을 설계했습니다. 
            이를 통해 DB에 직접적인 부하가 가는 것을 막고, 유량 제어(Flow Control)를 구현하여 시스템 다운을 방지했습니다.

            [해결 과정: 비동기 아키텍처 도입]
            기존 Django의 동기(Synchronous) 방식 주문 로직을 FastAPI와 Asyncio를 활용한 비동기 논블로킹(Asynchronous Non-blocking) 구조로 전면 전환했습니다.
            그 결과, I/O 대기 시간을 획기적으로 줄여 평균 응답 속도를 200ms 이내로 50% 이상 단축시켰습니다.
            또한, 주문 완료 후 알림 발송 로직은 Kafka 메시지 큐로 분리하여 메인 트랜잭션의 부하를 덜어냈습니다.
            """
        },
        {
            "project_name": "레거시 결제 모듈 리팩토링",
            "period": "2023.05 - 2023.11",
            "role": "Backend Developer",
            "tech_stack": ["Python", "Django", "PostgreSQL"],
            "description_for_embedding": """
            [문제 상황]
            5년 넘게 운영된 레거시 모놀리식 코드에서 결제 로직이 여러 곳에 산재되어 있어, 수정 시 사이드 이펙트(Side Effect)가 빈번하게 발생했습니다.

            [해결 과정: 리팩토링]
            결제 로직을 별도의 모듈로 응집시키고, 의존성을 주입(Dependency Injection)하는 방식으로 구조를 개선했습니다. 
            복잡하게 얽힌 중복 쿼리를 ORM 최적화하여 쿼리 실행 계획(Explain Analyze) 기준으로 비용을 30% 절감했습니다.
            """
        }
    ],
    "skills": ["High Traffic Handling", "Async/Await", "System Architecture", "Performance Tuning"]
    }
    # user_data = {
    #     "profile": {
    #         "user_id": "AI_CANDIDATE_002",
    #         "name": "박연구",
    #         "job_title": "AI/ML Engineer (신입/석사 졸업)",
    #         "summary": "자연어 처리(NLP) 및 거대 언어 모델(LLM) 최적화를 전공한 공학 석사입니다. 이론적 연구에 그치지 않고, 실제 서비스 환경에서의 추론 속도 개선과 데이터 불균형 문제를 해결하는 엔지니어링 역량을 보유하고 있습니다."
    #     },
    #     "projects": [
    #         {
    #             "project_name": "LLM 기반 도메인 특화 지식 추출 시스템 (RAG) 고도화",
    #             "period": "2025.03 - 2025.12",
    #             "role": "ML Researcher & Backend Engineer",
    #             "tech_stack": ["Python", "PyTorch", "LangChain", "ChromaDB", "FastAPI"],
    #             "description_for_embedding": """
    #             [문제 상황]
    #             사내 기술 문서를 기반으로 한 질의응답 시스템에서, LLM의 할루시네이션(Hallucination) 현상과 특정 전문 용어에 대한 이해도 부족으로 인해 답변 정확도가 60% 미만에 머무는 문제가 있었습니다.

    #             [해결 과정: 하이브리드 검색 및 Reranking]
    #             단순 벡터 검색의 한계를 극복하기 위해 키워드 기반 BM25와 시맨틱 기반 Dense Retrieval을 결합한 하이브리드 검색 아키텍처를 설계했습니다. 
    #             검색 결과의 정밀도를 높이기 위해 Cross-Encoder 기반의 Re-ranker 모델을 도입하여, 상위 5개 문서의 관련성을 재평가함으로써 최종 답변 정확도를 85%까지 끌어올렸습니다.

    #             [해결 과정: 모델 경량화 및 서빙]
    #             실제 서비스 적용을 위해 7B 파라미터 모델을 FP16에서 4-bit Quantization(AWQ)으로 양자화하여 적용했습니다. 
    #             V100 GPU 환경에서 추론 속도를 기존 대비 3배 이상 단축시켰으며, FastAPI를 활용해 비동기 스트리밍 API를 구축하여 사용자 대기 시간을 최소화했습니다.
    #             """
    #         },
    #         {
    #             "project_name": "데이터 불균형 해결을 위한 합성 데이터 생성 모델 연구 (석사 학위 논문)",
    #             "period": "2024.01 - 2025.02",
    #             "role": "Main Researcher",
    #             "tech_stack": ["Python", "HuggingFace", "Scikit-learn", "Matplotlib"],
    #             "description_for_embedding": """
    #             [문제 상황]
    #             특정 레이블이 전체의 5% 미만인 극심한 데이터 불균형 환경에서 분류 모델의 재현율(Recall)이 현저히 떨어지는 문제를 정의했습니다.

    #             [해결 과정: LLM 기반 데이터 증강]
    #             단순한 오버샘플링 대신, LLM(Llama-3)을 활용하여 소수 클래스 데이터를 생성하는 'LLM-based Data Augmentation' 기법을 제안했습니다. 
    #             생성된 데이터가 실제 언어 패턴을 해치지 않도록 필터링 로직을 구축하였고, 이를 통해 소수 클래스에 대한 F1-Score를 기존 대비 22% 향상시켰습니다.
    #             이 연구 결과를 바탕으로 국내 인공지능 학술대회(KCC)에서 우수 논문상을 수상하였습니다.
    #             """
    #         }
    #     ],
    #     "skills": ["LLM Fine-tuning", "RAG Optimization", "Model Quantization", "NLP Research", "Vector DB"]
    # }           
    # user_data = {
    #     "profile": {
    #         "user_id": "SEC_CANDIDATE_003",
    #         "name": "최보안",
    #         "job_title": "Security Engineer / DevSecOps (4년차)",
    #         "summary": "인프라 구축 단계부터 보안을 내재화하는 DevSecOps 실현을 목표로 합니다. AWS 환경에서의 클라우드 보안 거버넌스 수립과 SIEM을 활용한 실시간 침해 사고 분석에 강점이 있습니다."
    #     },
    #     "projects": [
    #         {
    #             "project_name": "금융권 클라우드 전환을 위한 제로 트러스트(Zero Trust) 보안 아키텍처 설계",
    #             "period": "2024.06 - 2025.01",
    #             "role": "Security Architect",
    #             "tech_stack": ["AWS", "Terraform", "Vault", "Istio", "Python"],
    #             "description_for_embedding": """
    #             [문제 상황]
    #             기존 온프레미스(On-premise) 방식의 경계 기반 보안 모델로는 동적으로 변화하는 클라우드 환경의 자원 접근 제어와 데이터 유출 방지가 불가능한 구조적 한계가 있었습니다.

    #             [해결 과정: 제로 트러스트 아키텍처 구현]
    #             '절대 신뢰하지 않고 항상 검증한다'는 원칙 아래, HashiCorp Vault를 도입하여 정적 자격 증명을 동적 자격 증명(Dynamic Credentials) 방식으로 전면 교체했습니다. 
    #             Istio 서비스 메쉬를 활용하여 마이크로서비스(MSA) 간의 상호 TLS(mTLS) 인증을 강제함으로써 내부망 이동(Lateral Movement) 공격 위협을 90% 이상 차단했습니다.

    #             [해결 과정: 인프라 코드 보안(IaC Security)]
    #             Terraform 코드 내 보안 취약점을 배포 전 검사하기 위해 Checkov를 CI/CD 파이프라인(GitHub Actions)에 통합했습니다. 
    #             이를 통해 잘못된 설정(Misconfiguration)으로 인한 S3 버킷 노출 및 과도한 IAM 권한 부여를 사전에 100% 방지하는 프로세스를 구축했습니다.
    #             """
    #         },
    #         {
    #             "project_name": "ELK Stack 기반 실시간 이상 징후 탐지 및 대응(SOAR) 시스템 구축",
    #             "period": "2023.08 - 2024.03",
    #             "role": "Security Operations Engineer",
    #             "tech_stack": ["Elasticsearch", "Logstash", "Kibana", "Suricata", "Ansible"],
    #             "description_for_embedding": """
    #             [문제 상황]
    #             일 평균 1억 건 이상의 보안 로그가 발생했으나, 수동 분석 위주의 체계로 인해 실제 침해 시도 발견부터 대응까지 평균 48시간(MTTR)이 소요되는 심각한 지연이 발생했습니다.

    #             [해결 과정: 자동화된 탐지 및 대응]
    #             Elasticsearch와 Suricata(IDS)를 연동하여 알려진 공격 패턴(SQL Injection, Brute Force)을 실시간 탐지하는 대시보드를 구축했습니다. 
    #             비정상적인 대량 트래픽이나 해외 IP 접근 발생 시 Ansible 플레이북을 자동으로 실행하여 공격 IP를 방화벽에서 즉시 차단하는 SOAR(Security Orchestration, Automation and Response) 로직을 구현했습니다.
    #             그 결과, 침해 사고 초기 대응 시간(MTTR)을 48시간에서 15분 이내로 단축시켰습니다.
    #             """
    #         }
    #     ],
    #     "skills": ["Cloud Security (AWS/Azure)", "DevSecOps", "Penetration Testing", "SIEM/SOAR", "Compliance (ISMS-P)"]
    # }
    
    # Init Matcher
    matcher = ClovaMatcher()
    
    # 2. Query Creator 초기화 및 쿼리 생성
    try:
        query_gen = QueryCreator()
        generated_queries = query_gen.generate_queries(user_data)
        
        print(f"\\n--- [RAG 테스트] 생성된 검색 쿼리: 총 {len(generated_queries)}개 ---")
        for i, q_obj in enumerate(generated_queries):
            print(f"[{i+1}] [{q_obj.get('type')}] {q_obj.get('query')}")

        # 3. Recruit Indexer를 통한 검색
        indexer = RecruitIndexer()
        
        # 쿼리 유형별 가중치 정의
        QUERY_WEIGHTS = {
            "tech": 1,
            "problem": 1, 
            "domain": 1
        }

        # 3-1. 통합 검색 및 필터링/중복 제거 로직
        all_candidates = []
        SCORE_THRESHOLD = 1.2  # 기준 완화
        
        print(f"\\n--- 통합 검색 시작 ---")
        for idx, q_obj in enumerate(generated_queries):
            search_query = q_obj.get("query")
            q_type = q_obj.get("type", "domain")
            weight = QUERY_WEIGHTS.get(q_type, 1.0)
            
            print(f"\\n[쿼리 {idx+1}] ({q_type}) '{search_query}' 검색 중... (가중치: {weight})")
            
            # Hybrid Search (returns List[Tuple[Document, float]])
            results = indexer.search_hybrid(search_query, k=15)
            
            for rank, (doc, score) in enumerate(results):
                final_score = score / weight
                
                # 점수 확인용 로그
                print(f"  -> (Raw: {score:.4f} / Final: {final_score:.4f}) [Hybrid Rank {rank}] {doc.metadata.get('company')} - {doc.metadata.get('title')}")
                # 임시로 모든 결과 수집
                all_candidates.append((doc, final_score))
        
        # 3-2. 중복 제거 및 가중치 합산 전략 선택
        # RRF(Reciprocal Rank Fusion) 변형
        unique_candidates = aggregate_by_rrf_variant(all_candidates, SCORE_THRESHOLD, k=1.0)
        
        # 딕셔너리 값들만 추출 후 점수순 정렬
        sorted_candidates = sorted(
            unique_candidates.values(), 
            key=lambda x: x['score']
        )
        
        # 상위 50개만 추출 (Reranking 대상)
        final_candidates = [item['doc'] for item in sorted_candidates[:50]]
        
        print(f"\\n--- 1차 필터링 완료: {len(final_candidates)}개 후보군 추출 (Top 50) ---")
        for i, doc in enumerate(final_candidates[:50]):
            print(f"  {i+1}. {doc.metadata.get('company')} - {doc.metadata.get('title')}")
            
        if not final_candidates:
            print("⚠️ 필터링 조건을 만족하는 공고가 없습니다.")
            return

        # 4. NCP Reranker로 20개로 압축
        print("\n--- NCP Hyperclova Reranker 실행 (50 -> 20) ---")
        # user_data 전부와 생성된 쿼리들을 포함한 상세 쿼리 생성
        gen_queries_text = ", ".join([q.get('query', '') for q in generated_queries])
        rerank_query = (
            f"사용자 데이터: {json.dumps(user_data, ensure_ascii=False)}\n"
            f"생성된 쿼리: {gen_queries_text}\n"
            "사용자 정보와 생성된 쿼리를 기반으로 가장 적합한 공고를 20개 추출해줘. 최소 10개 이상의 공고를 추출해줘"
        )
        
        refined_candidates = await matcher.rerank_with_ncp(rerank_query, final_candidates, top_n=20)
        
        if refined_candidates:
            print(f"✅ Reranking 완료: {len(refined_candidates)}개 선정")
            recommendations = []
            for doc in refined_candidates[:]:
                item = dict(doc.metadata)
                item["reason"] = "NCP Reranker 추천 결과입니다."
                recommendations.append(item)
        else:
            # 5. LLM 최종 추천 (Top 5) - Reranker 3회 실패 시 실행
            print("\n--- Reranker 응답 없음: LLM 최종 추천 및 사유 생성 (Top 5) ---")
            recommendations = await matcher.rank_and_reason(user_data, final_candidates)
        
        print("\n🎯 [최종 추천 TOP 5 공고]")
        for i, rec in enumerate(recommendations):
            print(f"\n[{i+1}위] {rec.get('company', 'Unknown')} - {rec.get('title', 'Unknown')}")
            print(f"🔗 링크: {rec.get('link', 'Link not found')}")
            print(f"✅ 추천 사유: {rec.get('reason', 'N/A')}")

    except Exception as e:
        traceback.print_exc()
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    # 로깅 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "..", "results")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file_path = os.path.join(output_dir, "search_results.txt")
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        original_stdout = sys.stdout
        sys.stdout = Tee(sys.stdout, f)
        try:
            print(f"=== 실행 결과 기록 시작 (저장 경로: {output_file_path}) ===")
            asyncio.run(run_search())
        finally:
            sys.stdout = original_stdout
            print(f"\\n=== 실행 결과가 성공적으로 저장되었습니다: {output_file_path} ===")
