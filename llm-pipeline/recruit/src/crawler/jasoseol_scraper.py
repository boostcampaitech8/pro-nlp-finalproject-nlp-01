import requests
import json
import time
import os
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup
import pandas as pd
import sys

# 경로 설정
# 현재 파일 위치: .../recruit/src/crawler/jasoseol_scraper.py
# RECRUIT_DIR: .../recruit/
RECRUIT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(RECRUIT_DIR / "src"))

from crawler.ocr_processor import OCRProcessor
env_path = RECRUIT_DIR / ".env"
load_dotenv(dotenv_path=env_path)

DATA_DIR = RECRUIT_DIR / "data" / "recruit_data"
SAVE_FILE_JSON = DATA_DIR / "jasoseol_questions.json"
SAVE_FILE_CSV = DATA_DIR / "jasoseol_recruit.csv"
SAVE_FILE_OCR_CSV = DATA_DIR / "jasoseol_recruit_ocr.csv"

# 저장 디렉토리 생성
DATA_DIR.mkdir(parents=True, exist_ok=True)


class JasoseolScraper:
    def __init__(self):
        self.base_url = "https://jasoseol.com"
        self.session = requests.Session()
        
        # .env에서 쿠키 가져오기
        self.cookies_str = os.getenv("JASOSEOL_COOKIE")
        if not self.cookies_str:
            raise ValueError(".env 파일에 'JASOSEOL_COOKIE'가 설정되어 있지 않습니다.")
        
        # 공통 헤더 설정
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://jasoseol.com",
            "referer": "https://jasoseol.com/recruit",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "cookie": self.cookies_str
        }
        self.session.headers.update(self.headers)

    def get_calendar_list(self, start_time, end_time):
        """특정 기간의 공고 리스트와 employment_id를 가져옴"""
        url = f"{self.base_url}/employment/calendar_list.json"
        payload = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                employment = data.get('employment')
                if isinstance(employment, list):
                    return employment
                else:
                    print(f"Warning: 'employment' is not a list. Got: {employment}")
                    return []
            else:
                print(f"Failed to fetch calendar list: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error occurred while fetching calendar list: {e}")
            return []

    def get_questions(self, employment_id):
        """특정 employment_id에 대한 질문 상세 정보를 가져옴"""
        url = f"{self.base_url}/employment/employment_question.json"
        payload = {"employment_id": employment_id}
        
        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                questions = data.get('employment_question')
                if isinstance(questions, list):
                    return questions
                else:
                    print(f"Warning: 'employment_question' is not a list for ID {employment_id}. Got: {questions}")
                    return []
            else:
                print(f"Failed to fetch questions for ID {employment_id}: {response.status_code}")
                # 세션 만료 여부 확인을 위해 응답 내용 일부 출력
                if response.status_code == 401 or response.status_code == 403:
                    print("세션이 만료되었거나 권한이 없는 것 같습니다. 쿠키를 확인해주세요.")
                return []
        except Exception as e:
            print(f"Error occurred while fetching questions for ID {employment_id}: {e}")
            return []

    def get_recruit_detail(self, recruit_id):
        """특정 recruit_id에 대한 상세 공고 정보(이미지 포함)를 가져옴"""
        url = f"{self.base_url}/employment/get.json"
        payload = {
            "employment_company_id": recruit_id,
            "skip_read_log": True
        }
        
        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get('ret'):
                    content_html = data.get('content', '')
                    soup = BeautifulSoup(content_html, 'html.parser')
                    
                    # 텍스트 추출
                    content_text = soup.get_text(separator='\n', strip=True)
                    
                    # 이미지 URL 추출
                    images = []
                    for img in soup.find_all('img'):
                        src = img.get('src')
                        if src:
                            images.append(src)
                    
                    content_images = ",".join(images)
                    
                    return {
                        "company": data.get('name'),
                        "title": data.get('title'),
                        "url": f"https://jasoseol.com/recruit/{recruit_id}",
                        "content_text": content_text,
                        "content_images": content_images,
                        "apply_url": data.get('employment_page_url'),
                        "Needs_OCR": True if images else False
                    }
                else:
                    print(f"Failed to get recruit detail for ID {recruit_id}: ret is false")
                    return None
            else:
                print(f"Failed to fetch recruit detail for ID {recruit_id}: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error occurred while fetching recruit detail for ID {recruit_id}: {e}")
            return None

    def run(self):
        # 날짜 범위 설정: 오늘 00시 ~ 일주일 후 00시
        now = datetime.utcnow()
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=1)
        
        # API 형식에 맞게 문자열 변환 (Z 포맷)
        start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        print(f"[{datetime.now()}] 스크래핑을 시작합니다... ({start_str} ~ {end_str})")
        recruitments = self.get_calendar_list(start_str, end_str)
        print(f"총 {len(recruitments)}개의 공고를 발견했습니다.")
        
        all_questions_data = []
        csv_columns = ["company", "title", "url", "content_text", "content_images", "apply_url", "Needs_OCR"]
        
        # CSV 파일 초기화 (헤더 작성)
        with open(SAVE_FILE_CSV, "w", encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
        
        processed_recruit_ids = set()
        
        try:
            for idx, recruit in enumerate(recruitments):
                recruit_id = recruit.get('id')
                company_name = recruit.get('name')
                recruit_title = recruit.get('title')
                
                # 공고 정보 상세 수집 및 CSV 저장 (한 번만 수행)
                if recruit_id not in processed_recruit_ids:
                    print(f"[{idx+1}/{len(recruitments)}] {company_name} - 공고 상세 정보 추출 중...")
                    detail = self.get_recruit_detail(recruit_id)
                    if detail:
                        with open(SAVE_FILE_CSV, "a", encoding='utf-8-sig', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=csv_columns)
                            writer.writerow(detail)
                        processed_recruit_ids.add(recruit_id)
                        time.sleep(2) # 상세 정보 요청 간 지연
                
                employments = recruit.get('employments', [])
                for emp in employments:
                    emp_id = emp.get('id')
                    print(f"  - {company_name} (ID: {emp_id}) 자소서 문항 추출 중...")
                    
                    try:
                        questions = self.get_questions(emp_id)
                        
                        processed_questions = []
                        if isinstance(questions, list):
                            for q in questions:
                                total_count = q.get('total_count')
                                max_length = total_count if total_count and total_count > 0 else "글자수 제한 없음"
                                
                                processed_questions.append({
                                    "question": q.get('question'),
                                    "max_length": max_length
                                })
                        
                        item = {
                            "recruit_id": recruit_id,
                            "employment_id": emp_id,
                            "company_name": company_name,
                            "title": recruit_title,
                            "end_time": recruit.get('end_time'),
                            "questions": processed_questions
                        }
                        all_questions_data.append(item)
                        
                        # 질문 출력
                        if processed_questions:
                            for i, q_item in enumerate(processed_questions, 1):
                                q_text = q_item["question"] or ""
                                limit_str = f"{q_item['max_length']}자" if isinstance(q_item['max_length'], int) else q_item['max_length']
                                print(f"    Q{i} ({limit_str}): {q_text[:50]}...")
                        else:
                            print("    (질문 정보 없음)")
                        
                        # JSON 중간 저장
                        with open(SAVE_FILE_JSON, "w", encoding='utf-8') as f:
                            json.dump(all_questions_data, f, ensure_ascii=False, indent=4)
                            
                    except Exception as e:
                        print(f"Error processing employment {emp_id}: {e}")
                        continue
                        
                    # 요청 간 지연 시간
                    time.sleep(3)
                    
        except KeyboardInterrupt:
            print("\n사용자에 의해 스크래핑이 중단되었습니다.")
        except Exception as e:
            print(f"\n치명적인 에러 발생: {e}")
        finally:
            if all_questions_data:
                with open(SAVE_FILE_JSON, "w", encoding='utf-8') as f:
                    json.dump(all_questions_data, f, ensure_ascii=False, indent=4)
                print(f"\n완료! 자소서 문항: {SAVE_FILE_JSON}, 공고 정보: {SAVE_FILE_CSV}")
            else:
                print("\n저장할 데이터가 없습니다.")

        # OCR 처리 추가
        if os.path.exists(SAVE_FILE_CSV):
            print("\n=== OCR 처리 시작 ===")
            try:
                processor = OCRProcessor()
                processor.process_csv(
                    input_csv=str(SAVE_FILE_CSV), 
                    output_csv=str(SAVE_FILE_OCR_CSV),
                    needs_ocr_col='Needs_OCR',
                    image_urls_col='content_images',
                    context_col='content_text'
                )
                print(f"OCR 완료! 결과 저장: {SAVE_FILE_OCR_CSV}")
            except Exception as e:
                print(f"OCR 처리 중 에러 발생: {e}")

if __name__ == "__main__":
    scraper = JasoseolScraper()
    scraper.run()
