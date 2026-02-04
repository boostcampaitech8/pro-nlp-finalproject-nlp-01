
import os
import sys
import json
import argparse
import random
import time
import re
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# 모듈 경로 추가 (src 디렉토리를 sys.path에 추가하여 common 패키지 import 가능하게 함)
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
sys.path.append(str(SRC_DIR))

from common.clova_client import ClovaStudioClient

# .env 로드
BASE_DIR = SRC_DIR.parent.parent.parent  # pro-nlp-finalproject-nlp-01
RECRUIT_DIR = Path(__file__).resolve().parent.parent.parent
env_path = RECRUIT_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# 경로 설정 (기본값)
DATA_DIR = SRC_DIR.parent / "data" / "recruit_data"

SYSTEM_PROMPT = """채용 공고 전문가로서 다음 지침에 따라 공고 데이터를 분석하여 JSON 리스트로 변환하세요.
1. 한 공고 내에 여러 직무(백엔드, 프론트엔드 등)가 있다면 각각 독립된 JSON 객체로 분리하여 리스트로 만드세요. 이 경우, 공고 제목은 원래 공고제목 뒤에 세부직무 (공고명 - 세부직무) 형식으로 작성하세요.
2. 표(Table) 형식의 데이터는 행과 열의 관계를 정확히 파악하여 각 직무에 맞게 할당하세요.
3. deadline이 정확하게 표현되지 않은 경우 '상시채용'으로 반환하세요. 날짜가 정확할 경우 'yyyy-mm-dd HH:mm' 형식으로 반환하세요.
4. link에는 지원 링크를 반환하세요. 없을 경우에만 원본 링크를 반환하세요.
5. 출력 형식은 반드시 아래 키를 포함하는 JSON 리스트여야 합니다 (Code Block 없이 순수 JSON만 출력):
   keys: [title, company, link, deadline, location, experience, education, employment_type, salary, job_sector, key_responsibilities, required_qualifications, preferred_qualifications]
6. **중요**: 반드시 유효한 JSON 형식을 지키세요. 모든 문자열은 반드시 큰따옴표(")를 사용하고, 작은따옴표(')를 섞어서 사용하지 마세요. 리스트의 마지막 항목 뒤에 쉼표(,)를 붙이지 마세요.
"""

def repair_json(s):
    """
    LLM이 생성한 JSON의 흔한 실수들을 보정합니다.
    """
    if not s: return s
    
    # 1. 혼용된 따옴표 수정 (예: "text' -> "text")
    s = re.sub(r'(")([^"]*?)(\')', r'\1\2"', s)
    s = re.sub(r"(')([^']*?)(\")", r'"\2\3', s)
    
    # 2. 문자열 전체가 작은따옴표로 감싸진 경우 큰따옴표로 교체 (조심스럽게)
    # 쉼표, 콜론, 대괄호 주변의 작은따옴표를 타겟팅
    s = re.sub(r"(?<=[:\[,])\s*'([^']*)'(?=\s*[:\],])", r' "\1"', s)
    
    # 3. 마지막 항목 뒤의 불필요한 쉼표(Trailing Comma) 제거
    s = re.sub(r",\s*([\]}])", r"\1", s)
    
    return s

def get_row_content(row):
    """
    다양한 크롤러 포맷(InThisWork, Saramin 등)에 맞춰 필드를 통합하여 반환
    """
    # 1. 공통 필드 시도
    company = row.get('company', '') or row.get('Company', '')
    title = row.get('title', '') or row.get('Title', '')
    url = row.get('url', '') or row.get('Link', '')
    apply_url = row.get('apply_url', '')
    
    # apply_url이 비어있다면 원본 url로 대체 (Saramin 등)
    if not apply_url:
        apply_url = url
    
    # 2. 본문 텍스트 통합
    content_text = ""
    
    # CASE A: InThisWork (content_text)
    if 'content_text' in row:
        content_text = str(row['content_text'])
    
    # CASE B: Saramin (Main Text, Qualifications, Preferred)
    parts = []
    # CASE B: Saramin (Main Text or Full_Context, Qualifications, Preferred)
    parts = []
    
    # Saramin Scraper는 'Full_Context'를 사용, 일부 버전이나 다른 크롤러가 'Main Text'를 쓸 수 있으므로 둘 다 확인
    main_text = row.get('Main Text') or row.get('Full_Context')
    
    if main_text and pd.notna(main_text) and main_text != 'N/A':
        parts.append(f"[상세 본문]\n{main_text}")
    if 'Qualifications' in row and pd.notna(row['Qualifications']) and row['Qualifications'] != 'N/A':
        parts.append(f"[자격 요건]\n{row['Qualifications']}")
    if 'Preferred' in row and pd.notna(row['Preferred']) and row['Preferred'] != 'N/A':
        parts.append(f"[우대 사항]\n{row['Preferred']}")
        
    if parts:
        content_text += "\n\n".join(parts)

    return company, title, url, apply_url, content_text

def analyze_job(client: ClovaStudioClient, row):
    company, title, url, apply_url, content_text = get_row_content(row)
    
    # NaN 처리
    if pd.isna(content_text): content_text = ""
    
    user_prompt = f"""
    회사명: {company}
    공고 제목: {title}
    원본 링크: {url}
    지원 링크: {apply_url}
    
    [본문 텍스트]:
    {content_text}
    """
    
    max_retries = 3
    result_text = ""
    for attempt in range(max_retries):
        print(f"  -> Clova 분석 요청: {company} - {title} (시도 {attempt + 1}/{max_retries})")
        res = client.generate_content(SYSTEM_PROMPT, user_prompt)
        
        if res == 200: # 혹시 성공 시 200이 올 경우 대비 (기존 로직 호환성)
            break
        elif res == 429:
            if attempt < max_retries - 1:
                wait_time = random.randint(30, 60)
                print(f"  -> [429 Error] Too Many Requests. {wait_time}초 대기 후 재시도합니다...")
                time.sleep(wait_time)
            else:
                print("  -> [429 Error] 최대 재시도 횟수(3회)를 초과했습니다.")
        elif isinstance(res, str):
            result_text = res
            if result_text: # 내용이 있으면 성공으로 간주
                break
        else:
            # 기타 에러 코드 (500, 401 등)
            break
    
    # JSON 파싱 전처리: 정규표현식을 사용하여 [ ] 사이의 내용만 추출
    try:
        # 가장 바깥쪽의 [ ] 블록을 찾음 (JSON 리스트)
        match = re.search(r'(\[.*\])', result_text.strip(), re.DOTALL)
        if match:
            clean_text = match.group(1)
        else:
            # 만약 리스트 형태가 아니라면 { } 블록이라도 시도
            match = re.search(r'(\{.*\})', result_text.strip(), re.DOTALL)
            if match:
                clean_text = match.group(1)
            else:
                clean_text = result_text.strip()
    except Exception as e:
        print(f"  -> 전처리 중 에러: {e}")
        clean_text = result_text.strip()
        
    return clean_text

def main():
    parser = argparse.ArgumentParser(description="Recruit Data Analyzer (Clova Studio)")
    parser.add_argument("--input", "-i", type=str, required=False, help="Input CSV file path")
    parser.add_argument("--output", "-o", type=str, required=False, help="Output JSON file path")
    args = parser.parse_args()

    # 기본값 설정
    # 기본값 설정 (기본적으로 InThisWork의 OCR 결과 파일을 바라봄)
    input_csv = Path(args.input) if args.input else DATA_DIR / "jasoseol_recruit_ocr.csv"
    output_json = Path(args.output) if args.output else DATA_DIR / "final_recruitment_all_items.json"

    if not input_csv.exists():
        print(f"입력 파일이 없습니다: {input_csv}")
        return

    print(f"=== 채용 공고 분석기 (Clova Studio) 시작 ===")
    print(f"입력: {input_csv}")
    print(f"출력: {output_json}")
    
    # CSV 로드
    df = pd.read_csv(input_csv)
    df = df.fillna('')
    
    # Client 초기화
    client = ClovaStudioClient()
    
    final_json_results = []
    
    for idx, row in df.iterrows():
        print(f"[{idx+1}/{len(df)}] 분석 중...")
        
        # API 부하 방지를 위한 랜덤 지연 (1~5초)
        delay = random.uniform(1, 5)
        print(f"  -> {delay:.2f}초 대기 중...")
        time.sleep(delay)
        
        json_str = analyze_job(client, row)
        print(f"  -> 분석 결과: {json_str}")
        
        if not json_str:
            print("  -> 결과 없음 (API 에러 또는 빈 응답)")
            continue
            
        try:
            # JSON 수리 로직 적용
            repaired_json = repair_json(json_str)
            job_data = json.loads(repaired_json)
            
            if isinstance(job_data, list):
                final_json_results.extend(job_data)
            elif isinstance(job_data, dict):
                final_json_results.append(job_data)
            else:
                print(f"  -> 파싱 실패: 리스트나 객체가 아님. ({repaired_json[:500]}...)")
        except json.JSONDecodeError:
            print(f"  -> JSON 디코딩 에러. 보정된 응답 내용: {repaired_json[:] if 'repaired_json' in locals() else json_str[:]}")
        except Exception as e:
            print(f"  -> 알 수 없는 에러: {e}")

    # 결과 저장 (기존 파일이 있으면 불러와서 추가)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    if output_json.exists():
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                if isinstance(old_data, list):
                    all_results.extend(old_data)
                else:
                    all_results.append(old_data)
            print(f"기존 파일({output_json})에서 {len(all_results)}건을 불러왔습니다.")
        except Exception as e:
            print(f"기존 파일 읽기 에러: {e}. 새로 생성합니다.")
    
    all_results.extend(final_json_results)
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n[최종 완료] {output_json}에 저장되었습니다. (신규: {len(final_json_results)}건, 총: {len(all_results)}건)")

if __name__ == "__main__":
    main()
