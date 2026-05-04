import logging
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from common.config import settings

logger = logging.getLogger(__name__)

class JasoseolScraper:
    def __init__(self):
        self.base_url = "https://jasoseol.com"
        self.cookies_str = settings.JASOSEOL_COOKIE
        
        if not self.cookies_str:
            logger.warning("JASOSEOL_COOKIE is not set. Scraper might fail for some endpoints.")

        self.headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://jasoseol.com",
            "referer": "https://jasoseol.com/recruit",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "cookie": self.cookies_str or ""
        }
        
    async def get_calendar_list(self, start_time: str, end_time: str) -> List[Dict]:
        """Fetch recruitment list for a date range."""
        url = f"{self.base_url}/employment/calendar_list.json"
        payload = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('employment', [])
                else:
                    logger.error(f"Failed to fetch calendar list: {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Error fetching calendar list: {e}")
                return []

    async def get_questions(self, employment_id: int) -> List[Dict]:
        """Fetch self-intro questions for a specific employment ID."""
        url = f"{self.base_url}/employment/employment_question.json"
        payload = {"employment_id": employment_id}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    questions = data.get('employment_question', [])
                    return questions if isinstance(questions, list) else []
                else:
                    logger.error(f"Failed to fetch questions for {employment_id}: {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Error fetching questions for {employment_id}: {e}")
                return []

    async def get_recruit_detail(self, recruit_id: int) -> Optional[Dict]:
        """Fetch detailed recruitment info including images."""
        url = f"{self.base_url}/employment/get.json"
        payload = {
            "employment_company_id": recruit_id,
            "skip_read_log": True
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    if not data.get('ret'):
                        return None
                        
                    content_html = data.get('content', '')
                    soup = BeautifulSoup(content_html, 'html.parser')
                    content_text = soup.get_text(separator='\n', strip=True)
                    
                    images = [img.get('src') for img in soup.find_all('img') if img.get('src')]
                    
                    return {
                        "company": data.get('name'),
                        "title": data.get('title'),
                        "url": f"https://jasoseol.com/recruit/{recruit_id}",
                        "content_text": content_text,
                        "image_urls": images,
                        "apply_url": data.get('employment_page_url'),
                        "start_time": data.get('start_time'),
                        "end_time": data.get('end_time')
                    }
                return None
            except Exception as e:
                logger.error(f"Error fetching detail for {recruit_id}: {e}")
                return None

    async def scrape(self, days: int = 2, exclude_links: set = set()) -> List[Dict]:
        """Main entry point to scrape recruitments for the next N days."""
        now = datetime.utcnow()
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=days)
        
        start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        logger.info(f"Starting Jasoseol scrape from {start_str} to {end_str}")
        
        recruitments = await self.get_calendar_list(start_str, end_str)
        results = []
        
        processed_recruit_ids = set()
        
        for recruit in recruitments:
            recruit_id = recruit.get('id')
            if not recruit_id or recruit_id in processed_recruit_ids:
                continue
                
            processed_recruit_ids.add(recruit_id)
            
            # Optimization: Skip if link is already in database
            recruit_url = f"https://jasoseol.com/recruit/{recruit_id}"
            if recruit_url in exclude_links:
                continue

            # Get Request Detail
            detail = await self.get_recruit_detail(recruit_id)
            if not detail:
                continue
            
            # Get Questions (Iterate over employments inside the recruitment group)
            employments = recruit.get('employments', [])
            all_questions = []
            seen_questions = set()
            
            for emp in employments:
                emp_id = emp.get('id')
                raw_qs = await self.get_questions(emp_id)
                
                # Format questions
                for q in raw_qs:
                    q_text = q.get('question', '').strip()
                    if not q_text or q_text in seen_questions:
                        continue
                    
                    seen_questions.add(q_text)
                    total_count = q.get('total_count')
                    max_len = total_count if total_count and total_count > 0 else None
                    
                    all_questions.append({
                        "question": q_text,
                        "limit": max_len,
                        "employment_category": emp.get('name')
                    })
                
                await asyncio.sleep(0.5) # Polite delay
                
            # Combine
            final_item = {
                "title": detail['title'],
                "company": detail['company'],
                "link": detail['url'],
                "content": detail['content_text'],
                "image_urls": detail['image_urls'],
                "questions": all_questions,
                "apply_url": detail['apply_url'],
                "deadline": detail['end_time'],
                "start_date": detail['start_time']
            }
            results.append(final_item)
            await asyncio.sleep(1.0) 
            
        return results
