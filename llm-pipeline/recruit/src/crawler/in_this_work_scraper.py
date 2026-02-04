import os
import time
import random
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv

# OCR 관련 라이브러리 (surya-ocr)
from surya.detection import DetectionPredictor
from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor
from surya.common.surya.schema import TaskNames

# .env 로드 (프로젝트 루트의 .env 탐색)
# 파일 위치: /data/ephemeral/git/pro-nlp-finalproject-nlp-01/llm-pipeline/recruit/src/crawler/in_this_work_scraper.py
# .parent: crawler/
# .parent.parent: src/
# .parent.parent.parent: recruit/
# .parent.parent.parent.parent: llm-pipeline/
# .parent.parent.parent.parent.parent: pro-nlp-finalproject-nlp-01/
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# 경로 설정
RECRUIT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = RECRUIT_DIR / "data" / "recruit_data"

# 파일명 설정
SAVE_FILE_CSV = DATA_DIR / "in_this_work.csv"
SAVE_FILE_OCR_CSV = DATA_DIR / "in_this_work_ocr.csv"

# 디렉토리 생성
DATA_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------
# 설정 및 모델 로드
# -----------------------------------------------------
TARGET_PAGES = 3

# Surya OCR 모델 로드 (전역 로드)
print("Surya OCR 모델 로딩 중...")
foundation_predictor = FoundationPredictor()
det_predictor = DetectionPredictor()
rec_predictor = RecognitionPredictor(foundation_predictor)
print("모델 로딩 완료.")

# -----------------------------------------------------
# 크롤링 함수들
# -----------------------------------------------------

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Referer': 'https://inthiswork.com/'
    }

def get_job_list(pages=1):
    print("=== 공고 목록 수집 시작 ===")
    all_jobs = []
    session = requests.Session()
    
    for page in range(1, pages + 1):
        if page == 1:
            url = "https://inthiswork.com/it"
        else:
            url = f"https://inthiswork.com/it/?paged1={page}"
            
        time.sleep(random.uniform(20, 45))
        print(f"[{page}페이지] 목록 수집 중... ({url})")
        
        success = False
        for attempt in range(3):
            try:
                resp = session.get(url, headers=get_headers(), timeout=15)
                if resp.status_code == 200:
                    success = True
                    break
                elif resp.status_code == 429:
                    wait_time = random.uniform(40, 70)
                    print(f"  → [429] 너무 많은 요청. {wait_time:.1f}초 대기 후 재시도... ({attempt + 1}/3)")
                    time.sleep(wait_time)
                else:
                    print(f"  → 에러: 접속 실패 (상태 코드 {resp.status_code}) ({attempt + 1}/3)")
                    time.sleep(random.uniform(5, 10))
            except Exception as e:
                print(f"  → 에러 발생: {e} ({attempt + 1}/3)")
                time.sleep(random.uniform(5, 10))
                
        if not success:
            print(f"  → {url} 접속에 3회 실패하여 건너뜁니다.")
            continue
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        entries = soup.select('.sub-entry')
        if not entries:
            entries = soup.select('.dpt-entry')
        if not entries:
            entries = soup.select('.dpt-entry-wrapper')
        
        print(f"  → {len(entries)}개 공고 발견")
        for entry in entries:
            link_obj = entry.select_one('a.dpt-title-link') or entry.select_one('.dpt-title a')
            
            if link_obj and link_obj.get('href'):
                full_url = link_obj.get('href')
                full_text = link_obj.get_text(strip=True)
                
                if '/archives/' not in full_url: 
                    continue
                
                if '｜' in full_text:
                    parts = full_text.split('｜', 1)
                elif '|' in full_text:
                    parts = full_text.split('|', 1)
                else:
                    parts = ["-", full_text]
                
                company = parts[0].strip() if len(parts) > 1 else "-"
                title = parts[1].strip() if len(parts) > 1 else parts[0].strip()

                # 회사명이 없거나(-) 혹은 "IN THIS WORK"를 포함하는 경우(인터뷰/콘텐츠) 제외
                if company == "-" or "IN THIS WORK" in company.upper():
                    print(f"  → 제외: {company} | {title}") # 제외되는 공고 로그 출력 (선택 사항)
                    continue
                
                if not any(j['url'] == full_url for j in all_jobs):
                    all_jobs.append({
                        'company': company,
                        'title': title,
                        'url': full_url
                    })
                    
    return all_jobs

def get_job_detail(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            # 기본 대기 시간
            time.sleep(random.uniform(2, 5))
            
            resp = requests.get(url, headers=get_headers(), timeout=15)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                content_area = (
                    soup.select_one('.fusion-content-tb') or 
                    soup.select_one('.fusion-content-tb-1') or 
                    soup.select_one('.fusion-content-tb-2') or 
                    soup.select_one('.post-content') or 
                    soup.select_one('.entry-content')
                )
                
                if not content_area:
                    if len(resp.text) > 2000:
                        content_area = soup.find('body')
                    else:
                        return "", "", ""
                
                apply_link_obj = content_area.select_one('a.maxbutton')
                if not apply_link_obj:
                    for a in content_area.select('a'):
                        if "지원하러" in a.get_text() or "지원하기" in a.get_text():
                            apply_link_obj = a
                            break
                
                apply_url = ""
                if apply_link_obj:
                    apply_url = apply_link_obj.get('href', '')
                    apply_link_obj.decompose()

                images = content_area.select('img')
                image_links = [img.get('src') for img in images if img.get('src')]
                images_str = ", ".join(image_links)

                text_content = content_area.get_text(separator='\n', strip=True)
                return text_content[:5000], images_str, apply_url
                
            elif resp.status_code == 429:
                wait_time = (attempt + 1) * 30  # 429 발생 시 더 오래 대기 (30, 60, 90초)
                print(f"  → [429] 너무 많은 요청. {wait_time}초 대기 후 재시도... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"  → 접속 실패 ({resp.status_code}): {url}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return "", "", ""
                    
        except Exception as e:
            print(f"  → 상세 에러({url}) - 시도 {attempt+1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return "", "", ""
                
    return "", "", ""

# -----------------------------------------------------
# OCR 관련 함수
# -----------------------------------------------------

def read_text_from_image_url(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return ""
        
        image_bytes = BytesIO(response.content)
        image = Image.open(image_bytes).convert("RGB")
        
        predictions = rec_predictor(
            [image], 
            [TaskNames.ocr_with_boxes], 
            det_predictor=det_predictor
        )
        
        if predictions and predictions[0].text_lines:
            full_text = "\n".join([line.text for line in predictions[0].text_lines])
            return full_text
        
        return ""
    except Exception as e:
        print(f"OCR 에러 ({url}): {e}")
        return ""

# -----------------------------------------------------
# 메인 실행 흐름
# -----------------------------------------------------

def main():
    # 1. 공고 목록 및 상세 수집
    job_list = get_job_list(pages=TARGET_PAGES)
    
    full_data = []
    if job_list:
        print("\n=== 상세 정보 수집 시작 ===")
        for idx, job in enumerate(job_list):
            print(f"[{idx+1}/{len(job_list)}] {job['title'][:15]}...")
            text, imgs, apply_url = get_job_detail(job['url'])
            
            job['content_text'] = text
            job['content_images'] = imgs
            job['apply_url'] = apply_url
            full_data.append(job)

        # 2. 결과 저장 (CSV)
        df = pd.DataFrame(full_data)
        if os.path.exists(SAVE_FILE_CSV):
            df.to_csv(SAVE_FILE_CSV, mode='a', header=False, index=False, encoding='utf-8-sig')
            print(f"\n[추가 완료] {SAVE_FILE_CSV}에 {len(df)}건 추가됨.")
        else:
            df.to_csv(SAVE_FILE_CSV, mode='w', header=True, index=False, encoding='utf-8-sig')
            print(f"\n[저장 완료] {SAVE_FILE_CSV} 생성됨.")

        # 3. 텍스트 부족 시 OCR 수행
        print("\n=== OCR 처리 시작 (필요 시) ===")
        df['content_text'] = df['content_text'].fillna('')
        target_mask = (df['content_text'].str.len() < 50) & (df['content_images'] != "")
        
        for idx, row in df[target_mask].iterrows():
            print(f"[{idx}] '{row['title']}' OCR 수행 중...")
            img_urls = str(row['content_images']).split(',')
            ocr_text_all = []
            for img_url in img_urls:
                img_url = img_url.strip()
                if not img_url: continue
                text = read_text_from_image_url(img_url)
                if text: ocr_text_all.append(text)
            
            if ocr_text_all:
                full_ocr_text = "(이미지 자동 추출 텍스트)\n" + "\n---\n".join(ocr_text_all)
                df.at[idx, 'content_text'] = full_ocr_text
                print("  -> 변환 완료")

        if os.path.exists(SAVE_FILE_OCR_CSV):
            df.to_csv(SAVE_FILE_OCR_CSV, mode='a', header=False, index=False, encoding='utf-8-sig')
            print(f"[추가 완료] {SAVE_FILE_OCR_CSV}에 {len(df)}건 추가됨.")
        else:
            df.to_csv(SAVE_FILE_OCR_CSV, mode='w', header=True, index=False, encoding='utf-8-sig')
            print(f"[저장 완료] {SAVE_FILE_OCR_CSV} 생성됨.")

if __name__ == "__main__":
    main()
