import os
import json
from pathlib import Path
from typing import Dict, Optional, List, Any

from dotenv import load_dotenv

# 현재 파일 위치: /data/ephemeral/git/pro-nlp-finalproject-nlp-01/llm-pipeline/recruit/query_creator.py
# .env 위치: /data/ephemeral/git/pro-nlp-finalproject-nlp-01/.env
# 현재 파일 위치: .../llm-pipeline/recruit/src/query_creator.py
# .env 위치: .../llm-pipeline/recruit/.env
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

# .env 파일 로드 (절대 경로 지정)
load_dotenv(dotenv_path=env_path)

# 현재 파일 위치: /data/ephemeral/git/pro-nlp-finalproject-nlp-01/llm-pipeline/recruit/query_creator.py
# .env 위치: /data/ephemeral/git/pro-nlp-finalproject-nlp-01/.env
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
env_path = BASE_DIR / ".env"

# .env 파일 로드 (절대 경로 지정)
load_dotenv(dotenv_path=env_path)

from common.clova_client import ClovaStudioClient

class QueryCreator:
    """
    사용자의 포트폴리오 데이터를 분석하여 HyperClovaX를 통해 
    Recruit Indexer 검색에 최적화된 3가지 유형의 쿼리를 생성하는 클래스입니다.
    """
    def __init__(self):
        self.client = ClovaStudioClient()
        
        self.system_prompt = """
        당신은 AI 기반 채용 매칭 전문가입니다. 
        제공된 사용자의 프로젝트 경험을 바탕으로, 검색 엔진(Vector DB)에서 가장 적합한 공고를 찾기 위한 검색 쿼리를 생성해주세요.
        
        각 프로젝트마다 다음 3가지 관점의 쿼리를 생성해야 합니다:
        1. 기술 스택 중심 (type: "tech"): 해당 프로젝트에서 사용된 핵심 기술 및 프레임워크, 프로젝트와 관련된 직무에 특화된 프레임워크를 중심으로 생성 (예: Python, FastAPI, Redis 등)
        2. 문제 해결 중심 (type: "problem"): 프로젝트에서 해결한 주요 과제나 성과 (예: 대용량 트래픽 처리, 쿼리 최적화 등)
        3. 도메인/주제 중심 (type: "domain"): 프로젝트의 산업 분야나 서비스 특성 (예: 이커머스, 핀테크, 금융, 물류 등)

        입력된 모든 프로젝트에 대해 각각 3개씩 쿼리를 생성하여, 총 (프로젝트 수 * 3)개의 쿼리 객체 리스트를 반환하세요.
        출력은 반드시 JSON 포맷이어야 하며, 각 객체는 "query"와 "type" 필드를 가져야 합니다.
        
        예시 포맷:
        [
            {"query": "Python FastAPI 백엔드 개발", "type": "tech"},
            {"query": "대용량 트래픽 처리 경험", "type": "problem"},
            {"query": "이커머스 결제 시스템", "type": "domain"}
        ]
        """

    def generate_queries(self, user_data: Dict) -> List[Dict[str, str]]:
        """
        입력받은 user_data의 프로젝트들을 분석하여 프로젝트당 3개의 검색 쿼리를 생성합니다.
        반환값은 쿼리 정보가 담긴 딕셔너리 리스트입니다.
        예: [{"query": str, "type": str}, ...]
        """
        
        projects = user_data.get("projects", [])
        if not projects:
            return [
                {"query": "백엔드 개발자 채용", "type": "domain"},
                {"query": "서버 개발 경험", "type": "tech"},
                {"query": "Python 웹 개발", "type": "tech"}
            ]

        user_input = f"""
        다음 사용자의 프로젝트 내역을 분석해서 프로젝트별로 검색용 쿼리를 3개씩(기술, 문제해결, 도메인) 생성해줘.
        
        [프로젝트 목록]
        {json.dumps(projects, ensure_ascii=False)}
        
        총 {len(projects) * 3}개의 쿼리가 포함된 JSON 리스트로 반환해줘.
        """

        try:
            # HyperClovaX 호출
            response_text = self.client.generate_content(
                system_prompt=self.system_prompt,
                user_prompt=user_input,
                max_tokens=2000
            )
            
            if not isinstance(response_text, str):
                print(f"Error: Clova API returned non-string response: {response_text}")
                raise ValueError(f"API call failed with status code: {response_text}")

            # JSON 파싱 시도 (Markdown code block 제거 등 전처리)
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text.replace("```json", "").replace("```", "")
            elif clean_text.startswith("```"):
                clean_text = clean_text.replace("```", "")
            
            # Extract JSON list if there's extra text
            start_idx = clean_text.find('[')
            end_idx = clean_text.rfind(']')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                clean_text = clean_text[start_idx:end_idx+1]
                
            queries = json.loads(clean_text)
            
            # 만약 { "queries": [...] } 형태로 올 경우 처리
            if isinstance(queries, dict):
                queries = queries.get("queries", list(queries.values())[0])
            
            if not isinstance(queries, list):
                # 형식이 맞지 않으면 기본값 반환 (강제 변환 시도)
                return [{"query": str(queries), "type": "domain"}]

            # 검증 및 정제
            refined_queries = []
            for q in queries:
                if isinstance(q, str):
                    # 문자열로 온 경우 기본 타입 할당
                    refined_queries.append({"query": q, "type": "domain"})
                elif isinstance(q, dict) and "query" in q:
                    refined_queries.append({
                        "query": q["query"],
                        "type": q.get("type", "domain")
                    })
            
            return refined_queries
            
        except Exception as e:
            print(f"Error generating queries: {e}")
            # Fallback: 간단한 조합으로 생성
            base_queries = []
            for p in projects:
                tech = " ".join(p.get("tech_stack", []))
                base_queries.append({"query": f"{tech} 개발자", "type": "tech"})
                base_queries.append({"query": f"{p.get('project_name')} 경험", "type": "problem"})
                base_queries.append({"query": "백엔드 시스템 구축", "type": "domain"})
            return base_queries

    def rank_final_recommendations(self, user_data: Dict, candidates: List[Any]) -> Dict:
        """
        검색된 후보 공고 리스트와 사용자 데이터를 비교하여 
        최종 추천 TOP 10 공고와 그 선정 사유를 생성합니다.
        unique_id를 포함하여 반환합니다.
        """
        if not candidates:
            return {"recommendations": [], "message": "추천할 후보 공고가 없습니다."}

        # 후보 공고 텍스트 요약 (LLM에게 전달할 양 조절)
        candidate_texts = []
        for i, doc in enumerate(candidates):
            meta = doc.metadata
            summary = (
                f"[공고 {i+1}]\n"
                f"ID: {meta.get('unique_id')}\n"
                f"회사: {meta.get('company')}\n"
                f"직무: {meta.get('title')}\n"
                f"주요업무: {doc.page_content[:1000]}\n"
                "-------------------\n"
            )
            candidate_texts.append(summary)

        prompt = f"""
        아래 사용자의 포트폴리오와 검색된 공고 후보군을 비교하여, 가장 적합한 TOP 10 공고를 선정하고 추천 사유를 작성해주세요.

        [사용자 데이터]
        {json.dumps(user_data, ensure_ascii=False)}

        [후보 공고 리스트]
        {"".join(candidate_texts)}

        ### 요구 사항:
        1. 후보군 중에서 사용자의 기술 스택과 강점(성과)에 가장 잘 맞는 공고를 최대 10개 선정하세요.
        2. 각 추천 공고마다 왜 이 공고가 사용자에게 적합한지 '추천 사유'를 구체적으로 작성하세요.
        3. 각 공고에 부여된 고유 ID(ID 필드값)를 정확히 응답에 포함하세요.
        4. 반드시 아래 JSON 형식으로만 응답하세요.

        ### 응답 형식:
        {{
            "recommendations": [
                {{
                    "rank": 1,
                    "unique_id": "해당 공고의 고유 ID(예: 회사명_공고제목)",
                    "company": "회사명",
                    "title": "공고 제목",
                    "reason": "추천 사유 (사용자의 어떤 경험이 이 공고의 어떤 부분에 기여할 수 있는지)"
                }}
            ]
        }}
        """

        try:
            response_text = self.client.generate_content(
                system_prompt="당신은 정교한 매칭을 수행하는 채용 컨설턴트입니다.",
                user_prompt=prompt,
                max_tokens=15000
            )
            
            if not isinstance(response_text, str):
                print(f"Error: Clova API returned non-string response: {response_text}")
                return {"recommendations": [], "error": f"API call failed with status code: {response_text}"}

            # JSON 파싱 시도
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text.replace("```json", "").replace("```", "")
            elif clean_text.startswith("```"):
                clean_text = clean_text.replace("```", "")

            return json.loads(clean_text)
        except Exception as e:
            print(f"Error in ranking: {e}")
            return {"recommendations": [], "error": str(e)}
