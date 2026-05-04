import json
import os

mock_data_dir = 'frontend/public/mock-data'

def fill_empty_values(data, filename):
    if not isinstance(data, list):
        return data

    for item in data:
        if not isinstance(item, dict):
            continue
        
        for key, value in item.items():
            # 1. Convert JSON-encoded strings to real arrays/objects
            if key in ['tags', 'questions', 'tech_stack', 'strengths'] and isinstance(value, str):
                try:
                    if value.strip():
                        item[key] = json.loads(value)
                    else:
                        item[key] = []
                except:
                    # If parsing fails, default to empty list
                    item[key] = []

            # 2. Fill empty values with defaults
            curr_value = item.get(key)
            if curr_value == "" or curr_value is None:
                if filename == 'recruitments.json':
                    if key == 'company_description':
                        item[key] = "기업 상세 정보가 등록되지 않았습니다."
                    elif key == 'preferred_qualifications':
                        item[key] = "별도의 우대사항 정보가 없습니다."
                    elif key == 'start_date':
                        item[key] = "상시채용"
                    elif key == 'location':
                        item[key] = "지역 정보 없음"
                    elif key == 'experience':
                        item[key] = "경력 무관"
                    elif key == 'education':
                        item[key] = "학력 무관"
                    elif key == 'salary':
                        item[key] = "회사 내규에 따름"
                    elif key in ['tags', 'questions']:
                        item[key] = []
                    elif key == 'embedding':
                        item[key] = []
                    else:
                        item[key] = "정보 없음"
                
                elif filename == 'portfolios.json':
                    if key == 'content' and item.get('description'):
                        item[key] = item['description']
                    elif key == 'embedding':
                        item[key] = []
                    else:
                        item[key] = "정보 없음"
                
                elif filename == 'users.json':
                    if key == 'profile_summary':
                        item[key] = "등록된 프로필 요약이 없습니다."
                    elif key == 'desired_job_title':
                        item[key] = "미지정"
                    else:
                        item[key] = "정보 없음"
                
                elif key in ['tags', 'questions', 'tech_stack']:
                    item[key] = []
                else:
                    item[key] = "정보 없음"
            
            # Final safety check for list fields
            if key in ['tags', 'questions', 'tech_stack'] and item[key] == "":
                item[key] = []

    return data

if __name__ == "__main__":
    for filename in os.listdir(mock_data_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(mock_data_dir, filename)
            print(f"Processing {filename}...")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                filled_data = fill_empty_values(data, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(filled_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    print("Done!")
