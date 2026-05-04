import logging
import httpx
import asyncio
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class SaraminScraper:
    """
    Asynchronous scraper for Saramin (saramin.co.kr).
    Ported and adapted from llm-pipeline.
    """
    def __init__(self):
        self.base_url = "https://www.saramin.co.kr"
        self.api_url = "https://www.saramin.co.kr/zf_user/search/get-recruit-list"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Referer": "https://www.saramin.co.kr"
        }
        self.detail_base_url = "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx="

    async def get_job_details(self, rec_idx: str) -> Tuple[str, List[str]]:
        """
        Fetches detailed job description, including content inside iframes.
        """
        if not rec_idx or rec_idx == 'N/A':
            return "", []
        
        detail_url = f"{self.detail_base_url}{rec_idx}"
        image_urls = []
        text_fragments = []

        async with httpx.AsyncClient(headers=self.headers, timeout=20.0, follow_redirects=True) as client:
            try:
                # 1. Main Page
                resp = await client.get(detail_url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')

                user_content = soup.select_one('div.user_content')
                if user_content:
                    text_fragments.append(user_content.get_text(" ", strip=True))
                    for img in user_content.select('img'):
                        alt = img.get('alt')
                        if alt: text_fragments.append(alt)
                        src = img.get('src')
                        if src: image_urls.append(urljoin(detail_url, src))

                # 2. Extract Iframes (Crucial for Saramin)
                iframes = soup.select('iframe')
                for iframe in iframes:
                    src = iframe.get('src')
                    if not src: continue
                    
                    iframe_url = urljoin(detail_url, src)
                    parsed_url = urlparse(iframe_url)
                    
                    # Only fetch if it belongs to saramin to avoid external issues
                    if 'saramin.co.kr' not in parsed_url.netloc:
                        continue

                    try:
                        iframe_resp = await client.get(iframe_url)
                        iframe_resp.raise_for_status()
                        iframe_soup = BeautifulSoup(iframe_resp.text, 'html.parser')
                        
                        text_fragments.append(iframe_soup.get_text(" ", strip=True))
                        for img in iframe_soup.select('img'):
                            alt = img.get('alt')
                            if alt: text_fragments.append(alt)
                            src = img.get('src')
                            if src: image_urls.append(urljoin(iframe_url, src))
                    except Exception as e:
                        logger.warning(f"Failed to fetch Saramin iframe {iframe_url}: {e}")

                combined_text = " ".join(text_fragments)
                cleaned_text = re.sub(r'\s+', ' ', combined_text).strip()
                
                return cleaned_text, list(set(image_urls))

            except Exception as e:
                logger.error(f"Error fetching Saramin details for {rec_idx}: {e}")
                return "", []

    async def scrape(self, keyword: str = "개발자", pages: int = 1, exclude_links: set = set()) -> List[Dict]:
        """
        Scrapes job list and details for a given keyword.
        """
        logger.info(f"Starting Saramin scrape for keyword '{keyword}', pages={pages}")
        all_results = []
        
        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            for page in range(1, pages + 1):
                params = {
                    "searchword": keyword,
                    "recruitPage": page,
                    "recruitPageCount": 20,
                    "mainSearch": "y"
                }
                
                try:
                    resp = await client.get(self.api_url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if 'innerHTML' not in data:
                        logger.warning(f"No innerHTML in Saramin response for page {page}")
                        continue
                        
                    soup = BeautifulSoup(data['innerHTML'], 'html.parser')
                    items = soup.select('div.item_recruit')
                    
                    for item in items:
                        try:
                            job_id = item.get('value')
                            title_tag = item.select_one('h2.job_tit a')
                            company_tag = item.select_one('strong.corp_name a')
                            
                            if not job_id or not title_tag:
                                continue
                                
                            link = urljoin(self.base_url, title_tag['href'])
                            
                            # Optimization: Skip if link is already in database
                            if link in exclude_links:
                                continue

                            title = title_tag.get_text(strip=True)
                            company = company_tag.get_text(strip=True) if company_tag else "N/A"
                            
                            # Fetch details in-line (can be parallelized later if needed)
                            content, images = await self.get_job_details(job_id)
                            
                            all_results.append({
                                "id": job_id,
                                "title": title,
                                "company": company,
                                "link": link,
                                "content": content,
                                "image_urls": images,
                                "source": "saramin"
                            })
                            
                            await asyncio.sleep(0.5) # Polite delay
                            
                        except Exception as e:
                            logger.error(f"Error parsing Saramin job item: {e}")
                            
                except Exception as e:
                    logger.error(f"Error fetching Saramin page {page}: {e}")
        
        return all_results
