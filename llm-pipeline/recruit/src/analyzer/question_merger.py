import json
import os
import re
from pathlib import Path
from difflib import SequenceMatcher

# 경로 설정
RECRUIT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = RECRUIT_DIR / "data" / "recruit_data"

# 파일명 설정
RECRUIT_FILE = DATA_DIR / "final_recruitment_all_items.json"
QUESTION_FILE = DATA_DIR / "jasoseol_questions.json"
OUTPUT_FILE = DATA_DIR / "final_recruitment_with_questions.json"

def normalize_text(text):
    """비교를 위해 텍스트 정규화 (공백 제거, 대소문자 통일, 특수문자 제거)"""
    if not text:
        return ""
    # 불필요한 수식어 및 특수문자 제거 (자소설과 사람인의 표기 차이 극복용)
    removals = ["(주)", "주식회사", "(유)", "유한회사", " ", "\t", "\n"]
    text = text.lower()
    for r in removals:
        text = text.replace(r, "")
    
    # 추가적인 특수문자 제거 (괄호, 마침표, 슬래시, 중점 등)
    special_chars = ["(", ")", "[", "]", "/", "·", "&", ",", "-", "_", ".", "｜", "|"]
    for char in special_chars:
        text = text.replace(char, "")
    return text

def merge_questions():
    print("=== 질문 데이터 병합 시작 ===")
    
    if not RECRUIT_FILE.exists() or not QUESTION_FILE.exists():
        print("필요한 파일이 없습니다.")
        return

    with open(RECRUIT_FILE, "r", encoding="utf-8") as f:
        recruit_data = json.load(f)
    with open(QUESTION_FILE, "r", encoding="utf-8") as f:
        question_data = json.load(f)

    print(f"공고 데이터: {len(recruit_data)}건")
    print(f"질문 데이터: {len(question_data)}건")

    question_map = {}
    for q_item in question_data:
        norm_company = normalize_text(q_item.get("company_name", ""))
        if norm_company not in question_map:
            question_map[norm_company] = []
        question_map[norm_company].append(q_item)

    merged_count = 0
    for r_item in recruit_data:
        # DB 일관성을 위해 기본값으로 빈 리스트 설정
        r_item["self_intro_questions"] = []
        
        company = r_item.get("company", "")
        norm_company = normalize_text(company)
        title = r_item.get("title", "")
        norm_title = normalize_text(title)

        if norm_company in question_map:
            potential_matches = question_map[norm_company]
            
            best_match = None
            max_score = 0
            
            for p_match in potential_matches:
                p_title = normalize_text(p_match.get("title", ""))
                
                if norm_title in p_title or p_title in norm_title:
                    score = 1.0
                else:
                    score = SequenceMatcher(None, norm_title, p_title).ratio()
                
                if score > max_score:
                    max_score = score
                    best_match = p_match
            
            if best_match and max_score > 0.5:
                # 질문 텍스트와 글자 수 제한을 함께 추출
                questions = []
                for q in best_match.get("questions", []):
                    if q.get("question"):
                        questions.append({
                            "question": q.get("question"),
                            "max_length": q.get("max_length")
                        })
                
                r_item["self_intro_questions"] = questions
                merged_count += 1
                if max_score < 1.0:
                    print(f"  [유사 매칭 ({max_score:.2f})] {company} - {title} <-> {best_match.get('title')}")
                else:
                    print(f"  [매칭 성공] {company} - {title}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(recruit_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 병합 완료 ===")
    print(f"최종 저장 위치: {OUTPUT_FILE}")
    print(f"질문이 추가된 공고: {merged_count}건 / 전체 {len(recruit_data)}건")

if __name__ == "__main__":
    merge_questions()
