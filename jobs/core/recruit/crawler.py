import os
import time
import asyncio
import json
import base64
import requests
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Pydantic schema for recruitment data
class RecruitmentItem(BaseModel):
    title: str = Field(..., description="직무명 + 공고제목")
    company: str = Field(..., description="회사명")
    link: str = Field(..., description="지원링크가 있으면 지원링크, 없으면 원본링크")
    start_date: Optional[str] = Field(None, description="모집 시작일 YYYY-MM-DD")
    deadline: Optional[str] = Field(None, description="마감일 YYYY-MM-DD 또는 '상시채용'")
    location: Optional[str] = Field(None, description="근무지")
    experience: Optional[str] = Field(None, description="경력 무관, 3년 이상 등")
    education: Optional[str] = Field(None, description="학력")
    employment_type: Optional[str] = Field(None, description="정규직 등")
    salary: Optional[str] = Field(None, description="급여 (정보 없으면 '면접 후 결정' 또는 '회사 내규에 따름')")
    category: Optional[str] = Field(None, description="카테고리 (리스트: '프론트엔드', '서버/백엔드', '웹 풀스택', 'AI/ML/NLP', '데이터', '모바일', 'DevOps' 중 하나 선택)")
    key_responsibilities: Optional[str] = Field(None, description="주요 업무")
    required_qualifications: Optional[str] = Field(None, description="자격 요건")
    preferred_qualifications: Optional[str] = Field(None, description="우대 사항")
    tags: Optional[List[str]] = Field(None, description="기술 스택 (리스트: React, TypeScript, Next.js, Java, Spring, Python, PyTorch, Node.js, Go, Swift, AWS, Kubernetes 중 해당되는 것 모두 선택)")

class RecruitmentList(BaseModel):
    items: List[RecruitmentItem] = Field(default_factory=list, description="채용 공고 리스트")


class RecruitmentCrawler:
    """
    Crawls recruitment postings from inthiswork.com and processes them with NCP HCX-005.
    """
    
    def __init__(self, target_pages: int = 1):
        self.target_pages = target_pages
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.ncp_api_key = os.getenv("NCP_CLOVASTUDIO_API_KEY")
        
        # Get base URL and ensure it has a proper protocol
        base_url = (os.getenv("NCP_CLOVASTUDIO_BASE_URL") or "").strip()
        if not base_url or not base_url.startswith(('http://', 'https://')):
            if base_url and "." in base_url:
                base_url = f"https://{base_url}"
            else:
                base_url = "https://clovastudio.stream.ntruss.com"
        
        self.ncp_base_url = base_url
        logger.info(f"RecruitmentCrawler initialized with base_url: {self.ncp_base_url}")
        
        if not self.google_api_key:
            logger.warning("GOOGLE_API_KEY not found. OCR will not work.")
        if not self.ncp_api_key:
            logger.warning("NCP_CLOVASTUDIO_API_KEY not found. Parsing will not work.")
    
    def _get_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        }
    
    def _google_vision_ocr(self, image_url: str) -> str:
        """Extract text from image using Google Vision API."""
        if not self.google_api_key:
            return ""
        
        try:
            resp = requests.get(image_url, timeout=10)
            if resp.status_code != 200:
                return ""
            
            image_content = base64.b64encode(resp.content).decode("utf-8")
            
            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.google_api_key}"
            payload = {
                "requests": [{
                    "image": {"content": image_content},
                    "features": [{"type": "TEXT_DETECTION"}]
                }]
            }
            
            vision_resp = requests.post(url, json=payload, timeout=20)
            if vision_resp.status_code != 200:
                logger.error(f"Vision API Error: {vision_resp.text}")
                return ""
            
            result = vision_resp.json()
            text_annotations = result.get("responses", [{}])[0].get("textAnnotations", [])
            if text_annotations:
                return text_annotations[0].get("description", "")
            return ""
        
        except Exception as e:
            logger.error(f"OCR Error ({image_url}): {e}")
            return ""
    
    def _analyze_job_with_ncp(self, job_data: Dict) -> List[Dict]:
        """Analyze job posting with NCP HCX-007 Structured Outputs and return structured data."""
        if not self.ncp_api_key:
            return []
        
        existing_text = job_data.get('content_text', '')
        img_urls = job_data.get('content_images', '').split(',') if job_data.get('content_images') else []
        ocr_text_all = ""
        
        # OCR processing if images are present (unconditional per user request)
        if "(이미지 자동 추출 텍스트)" not in existing_text and img_urls:
            logger.info(f"Triggering OCR for job (found {len(img_urls)} images)")
            for url in img_urls:
                url = url.strip()
                if not url:
                    continue
                text = self._google_vision_ocr(url)
                if text:
                    ocr_text_all += f"\n[이미지 추출 텍스트]:\n{text}\n"
        
        full_text = f"""
        회사명: {job_data.get('company', '')}
        공고 제목: {job_data.get('title', '')}
        원본 링크: {job_data.get('url', '')}
        지원 링크: {job_data.get('apply_url', '')}
        
        [본문 텍스트]:
        {existing_text}
        
        {ocr_text_all}
        """
        
        system_prompt = """
당신은 채용 공고 데이터 파싱 전문가입니다. 입력된 채용 공고 텍스트를 분석하여 구조화된 데이터로 출력하세요.

규칙:
1. 한 공고 내에 여러 직무(예: 백엔드, 프론트엔드)가 있다면 각각 독립된 객체로 분리하여 items 배열에 담으세요.
2. 모든 필드를 최대한 채우세요. 정보가 없으면 null 대신 적절한 기본값을 사용하세요.
   - salary: 정보 없으면 '면접 후 결정' 또는 '회사 내규에 따름'
   - location: 상세 주소가 없으면 구/군 단위까지라도 기재 (예: 서울 강남구)
   - experience/education: 정보 없으면 '경력 무관' / '학력 무관'
3. category는 반드시 다음 중 하나를 선택하세요: ['프론트엔드', '서버/백엔드', '웹 풀스택', 'AI/ML/NLP', '데이터', '모바일', 'DevOps']. 해당되는 것이 없으면 가장 유사한 것을 선택하거나 null로 두세요.
4. tags는 반드시 다음 기술 스택 리스트에서만 선택하세요: [React, TypeScript, Next.js, Java, Spring, Python, PyTorch, Node.js, Go, Swift, AWS, Kubernetes]. 공고에 명시된 것만 선택하세요.
5. key_responsibilities, required_qualifications, preferred_qualifications는 줄바꿈으로 구분된 문자열로 작성하세요.
"""
        
        url = f"{self.ncp_base_url}/v3/chat-completions/HCX-007"
        headers = {
            "Authorization": f"Bearer {self.ncp_api_key}",
            #"X-NCP-CLOVASTUDIO-API-KEY": self.ncp_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Generate JSON Schema from Pydantic model
        schema = RecruitmentList.model_json_schema()
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_text}
            ],
            "maxCompletionTokens": 4096,
            "temperature": 0.1,
            "topP": 0.8,
            "topK": 0,
            "thinking": {"effort": "none"},
            "responseFormat": {
                "type": "json",
                "schema": schema
            }
        }
        
        
        api_retries = 3
        
        for attempt in range(api_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=120)
                
                if resp.status_code == 200:
                    result = resp.json()
                    status_code = result.get("status", {}).get("code")
                    
                    if status_code == "20000":
                        content = result.get("result", {}).get("message", {}).get("content", "")
                        # Parse with Pydantic for validation
                        try:
                            recruitment_list = RecruitmentList.model_validate_json(content)
                            # Convert to dict list
                            return [item.model_dump() for item in recruitment_list.items]
                        except Exception as parse_err:
                            logger.error(f"JSON Parsing Error: {parse_err}")
                            return []

                    elif status_code == "42901":
                        logger.warning(f"NCP Rate Limit (42901) - Attempt {attempt+1}/{api_retries}")
                        time.sleep(5 * (attempt + 1)) # Exponential backoff: 5s, 10s, 15s
                        continue
                    else:
                        logger.error(f"NCP Error Status {status_code}: {result}")
                        return []
                        
                elif resp.status_code == 429:
                    logger.warning(f"HTTP 429 Too Many Requests - Attempt {attempt+1}/{api_retries}")
                    time.sleep(5 * (attempt + 1))
                    continue
                else:
                    logger.error(f"NCP HTTP Error {resp.status_code}: {resp.text}")
                    return []
                    
            except Exception as e:
                logger.error(f"NCP Call Exception: {e}")
                time.sleep(2) # Brief pause on network error
        
        logger.error("Max retries reached for NCP Analysis")
        return []
    
    def get_job_list(self) -> List[Dict]:
        """Crawl job list from inthiswork.com."""
        logger.info("=== Starting job list collection ===")
        all_jobs = []
        session = requests.Session()
        
        for page in range(1, self.target_pages + 1):
            url = "https://inthiswork.com/it" if page == 1 else f"https://inthiswork.com/it?paged1={page}"
            logger.info(f"[Page {page}] {url}")
            
            try:
                resp = session.get(url, headers=self._get_headers(), timeout=15)
                if resp.status_code != 200:
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                entries = soup.select('.dpt-entry') or soup.select('.dpt-entry-wrapper')
                
                logger.info(f"  → Found {len(entries)} postings")
                for entry in entries:
                    link_obj = entry.select_one('a.dpt-title-link') or entry.select_one('.dpt-title a')
                    if not link_obj:
                        continue
                    
                    full_url = link_obj.get('href')
                    full_text = link_obj.get_text(strip=True)
                    
                    if '/archives/' not in full_url:
                        continue
                    
                    parts = full_text.split('|', 1) if '|' in full_text else (full_text.split('｜', 1) if '｜' in full_text else ["-", full_text])
                    company = parts[0].strip() if len(parts) > 1 else "-"
                    title = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                    
                    if company == "-" or "IN THIS WORK" in company.upper():
                        continue
                    
                    if not any(j['url'] == full_url for j in all_jobs):
                        all_jobs.append({'company': company, 'title': title, 'url': full_url})
            
            except Exception as e:
                logger.error(f"  → Error: {e}")
        
        return all_jobs
    
    def get_job_detail(self, url: str) -> tuple:
        """Fetch detailed job posting content."""
        time.sleep(2)  # Politeness delay increased
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=30)
            if resp.status_code != 200:
                return "", "", ""
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            content_area = (
                soup.select_one('.fusion-content-tb') or 
                soup.select_one('.post-content') or 
                soup.select_one('.entry-content') or
                soup.find('body')
            )
            
            # Find apply URL
            apply_url = ""
            for a in content_area.select('a'):
                if "지원하러" in a.get_text() or "지원하기" in a.get_text():
                    apply_url = a.get('href', '')
                    break
            
            # Extract images (limit to reasonable number)
            images = [img.get('src') for img in content_area.select('img') if img.get('src')][:5]
            images_str = ", ".join(images)
            
            # Capture sidebar/metadata if present (often outside main content)
            sidebar = soup.select_one('.fusion-sidebar') or soup.select_one('#sidebar')
            sidebar_text = sidebar.get_text(separator=' ', strip=True) if sidebar else ""
            
            main_text = content_area.get_text(separator='\n', strip=True)
            full_content_text = f"{main_text}\n\n[기타 정보]:\n{sidebar_text}"
            
            return full_content_text[:8000], images_str, apply_url
        
        except Exception as e:
            logger.error(f"  → Detail error: {e}")
            return "", "", ""
    
    async def crawl_and_parse(self, exclude_urls: List[str] = []) -> List[Dict]:
        """Main crawling and parsing logic."""
        loop = asyncio.get_event_loop()

        # 1. Crawl job list
        # job_list = self.get_job_list()
        job_list = await loop.run_in_executor(None, self.get_job_list)
        
        # Filter existing jobs
        original_count = len(job_list)
        job_list = [job for job in job_list if job['url'] not in exclude_urls]
        logger.info(f"Filtered {original_count - len(job_list)} existing jobs. {len(job_list)} new jobs to process.")
        
        full_data = []
        if not job_list:
            logger.info("No new jobs to process.")
            return []

        logger.info(f"\n=== Collecting details for {len(job_list)} jobs ===")
        
        for idx, job in enumerate(job_list):
            logger.info(f"[{idx+1}/{len(job_list)}] {job['company']} - {job['title']}")
            # text, imgs, apply_url = self.get_job_detail(job['url'])
            text, imgs, apply_url = await loop.run_in_executor(None, self.get_job_detail, job['url'])
            
            job['content_text'] = text
            job['content_images'] = imgs
            job['apply_url'] = apply_url
            full_data.append(job)
        
        # 2. Analyze with NCP (OCR + LLM with Structured Outputs)
        logger.info("\n=== Analyzing data with NCP HCX-007 ===")
        final_json_results = []
        
        for idx, row in enumerate(full_data):
            logger.info(f"[{idx+1}/{len(full_data)}] Analyzing...")
            # items = self._analyze_job_with_ncp(row)
            items = await loop.run_in_executor(None, self._analyze_job_with_ncp, row)
            final_json_results.extend(items)
            
            # Rate limiting delay
            time.sleep(2)
        
        logger.info(f"\n[Complete] Parsed {len(final_json_results)} recruitment items")
        return final_json_results
