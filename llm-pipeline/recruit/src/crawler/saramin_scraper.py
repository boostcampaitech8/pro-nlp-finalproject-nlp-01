import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import argparse
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse
from pathlib import Path

class SaraminScraper:
    def __init__(self):
        self.base_url = "https://www.saramin.co.kr"
        self.api_url = "https://www.saramin.co.kr/zf_user/search/get-recruit-list"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.detail_base_url = "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx="

    def get_job_details(self, rec_idx):
        if rec_idx == 'N/A':
            return "N/A"
        
        detail_url = f"{self.detail_base_url}{rec_idx}"
        full_context = ""
        image_urls = []

        try:
            # Add a small delay
            time.sleep(0.5)
            # Add Referer to avoid blocking
            headers = self.headers.copy()
            headers['Referer'] = self.base_url
            
            response = requests.get(detail_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # List to hold all text fragments
            text_fragments = []

            # 1. Main Page Extraction
            user_content = soup.select_one('div.user_content')
            if user_content:
                # Extract text
                text_fragments.append(user_content.get_text(" ", strip=True))
                # Extract img tags
                for img in user_content.select('img'):
                    # Alt text
                    alt = img.get('alt')
                    if alt:
                        text_fragments.append(alt)
                    # Image URL
                    src = img.get('src')
                    if src:
                        image_urls.append(urljoin(detail_url, src))

            # 2. Iframe Extraction
            iframes = soup.select('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if not src:
                    continue
                
                # Resolve absolute URL
                iframe_url = urljoin(detail_url, src)
                
                # Domain safety check
                parsed_url = urlparse(iframe_url)
                if 'saramin.co.kr' not in parsed_url.netloc:
                    # Skip external unsafe domains
                    continue

                try:
                    time.sleep(0.2) # polite delay for sub-requests
                    iframe_headers = self.headers.copy()
                    iframe_headers['Referer'] = detail_url
                    
                    iframe_resp = requests.get(iframe_url, headers=iframe_headers, timeout=5)
                    iframe_resp.raise_for_status()
                    iframe_soup = BeautifulSoup(iframe_resp.text, 'html.parser')
                    
                    # Extract text from body
                    text_fragments.append(iframe_soup.get_text(" ", strip=True))
                    
                    # Extract img tags from iframe
                    for img in iframe_soup.select('img'):
                        # Alt text
                        alt = img.get('alt')
                        if alt:
                            text_fragments.append(alt)
                        # Image URL
                        src = img.get('src')
                        if src:
                            image_urls.append(urljoin(iframe_url, src))
                            
                except Exception as e:
                    # Log but continue if one iframe fails
                    print(f"    [Warning] Failed to fetch iframe {iframe_url}: {e}")
                    continue

            # 3. Aggregation and Cleaning
            combined_text = " ".join(text_fragments)
            # Remove HTML tags (already done by get_text, but good mental check)
            # Normalize whitespace: collapse multiple spaces/newlines to single space
            cleaned_text = re.sub(r'\s+', ' ', combined_text).strip()
            
            # 4. OCR Trigger Logic
            needs_ocr = False
            if len(cleaned_text) < 150:
                needs_ocr = True

            # Deduplicate image URLs
            unique_image_urls = list(set(image_urls))
            
            return cleaned_text if cleaned_text else "N/A", unique_image_urls, needs_ocr

        except Exception as e:
            print(f"Error fetching details for {rec_idx}: {e}")
            return "Error", [], False

    def _extract_list_text(self, block):
        # Helper to extract text from the list part of the block
        # Usually div.info-block__list > p or ul > li
        # Let's simple get all text from the sibling list container
        list_container = block.select_one('div.info-block__list, ul.info-block__list')
        if list_container:
            # Get text lines
            lines = [t.strip() for t in list_container.get_text("\n").split("\n") if t.strip()]
            return ", ".join(lines)
        return "N/A"


    def fetch_jobs(self, keyword, pages=1):
        all_jobs = []
        
        for page in range(1, pages + 1):
            print(f"Fetching page {page}...")
            params = {
                "searchword": keyword,
                "recruitPage": page,
                "recruitSort": "relation",
                "recruitPageCount": 20,
                "inner_com_type": "",
                "company_cd": 0,
                "show_applied": "",
                "quick_apply": "",
                "except_read": "",
                "ai_head_hunting": "",
                "mainSearch": "y"
            }
            
            try:
                response = requests.get(self.api_url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                if 'innerHTML' in data:
                    jobs = self.parse_jobs(data['innerHTML'])
                    all_jobs.extend(jobs)
                    print(f"Found {len(jobs)} jobs on page {page}.")
                else:
                    print(f"No data found on page {page}.")
                    break
                
                time.sleep(1)  # Be polite
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                
        return all_jobs

    def parse_jobs(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        job_list = []
        
        items = soup.select('div.item_recruit')
        
        for item in items:
            try:
                # Basic Fields
                job_id = item.get('value', 'N/A')
                title_tag = item.select_one('h2.job_tit a')
                company_tag = item.select_one('strong.corp_name a')
                dead_date_tag = item.select_one('div.job_date span.date')
                
                title = title_tag.get_text(strip=True) if title_tag else "N/A"
                link = self.base_url + title_tag['href'] if title_tag else "N/A"
                company = company_tag.get_text(strip=True) if company_tag else "N/A"
                deadline = dead_date_tag.get_text(strip=True) if dead_date_tag else "N/A"
                
                # Conditions (Location, Exp, Edu, EmpType, Salary)
                conditions = item.select('div.job_condition span')
                condition_texts = [c.get_text(strip=True) for c in conditions]
                
                location = condition_texts[0] if len(condition_texts) > 0 else "N/A"
                experience = condition_texts[1] if len(condition_texts) > 1 else "N/A"
                education = condition_texts[2] if len(condition_texts) > 2 else "N/A"
                employment_type = condition_texts[3] if len(condition_texts) > 3 else "N/A"
                
                # Check for Salary in conditions
                salary = "N/A"
                for cond in condition_texts:
                    if '만원' in cond or '연봉' in cond:
                        salary = cond
                        break
                
                # Sector
                # job_day is inside job_sector, so we need to remove it from sector text
                # Extract only text from <a> tags to avoid messy commas and "others" text
                sector_tag = item.select_one('div.job_sector')
                sector = "N/A"
                
                if sector_tag:
                     # Remove the date span just in case, though selecting 'a' avoids it
                    job_day_tag = sector_tag.select_one('span.job_day')
                    if job_day_tag:
                        job_day_tag.extract()
                    
                    # Extract text from link tags
                    sector_links = sector_tag.select('a')
                    if sector_links:
                        sector = ", ".join([link.get_text(strip=True) for link in sector_links])

                
                # Fetch Details
                # Fetch Details
                print(f"  Fetching details for job {job_id}...")
                full_context, image_urls, needs_ocr = self.get_job_details(job_id)

                job_list.append({
                    "Job ID": job_id,
                    "Title": title,
                    "Company": company,
                    "Link": link,
                    "Deadline": deadline,
                    "Location": location,
                    "Experience": experience,
                    "Education": education,
                    "Employment Type": employment_type,
                    "Salary": salary,
                    "Sector": sector,
                    "Qualifications": "Extract from context",
                    "Preferred": "Extract from context",
                    "Full_Context": full_context,
                    "Image_URLs": ", ".join(image_urls),
                    "Needs_OCR": needs_ocr
                })


            except Exception as e:
                print(f"Error parsing job item: {e}")
                continue
                
        return job_list

    def save_to_csv(self, data, filename):
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Saved {len(data)} jobs to {filename}")

if __name__ == "__main__":
    # 프로젝트 구조에 따른 기본 저장 경로 설정
    # 위치: recruit/src/crawler/saramin_scraper.py -> recruit/data/recruit_data/
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE_DIR / "data" / "recruit_data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT = DATA_DIR / "saramin.csv"

    parser = argparse.ArgumentParser(description="Saramin Job Scraper")
    parser.add_argument("--keyword", type=str, required=True, help="Search keyword")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output CSV filename")
    
    args = parser.parse_args()
    
    scraper = SaraminScraper()
    jobs = scraper.fetch_jobs(args.keyword, args.pages)
    scraper.save_to_csv(jobs, args.output)
