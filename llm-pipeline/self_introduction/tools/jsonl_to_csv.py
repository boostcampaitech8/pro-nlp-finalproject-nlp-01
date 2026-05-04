import json
import csv
import pandas as pd
from pathlib import Path

def convert_jsonl_to_csv(jsonl_path, csv_path):
    data = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    
    df = pd.DataFrame(data)
    
    # instruction에서 직무와 문항 분리 (선택 사항)
    # 현재 형식: "지원 직무: ...\n문항: ..."
    def split_instruction(text):
        try:
            role = text.split("지원 직무:")[1].split("문항:")[0].strip()
            question = text.split("문항:")[1].strip()
            return role, question
        except:
            return "N/A", text

    df[['role', 'question']] = df['instruction'].apply(lambda x: pd.Series(split_instruction(x)))
    
    # 보기 좋게 열 순서 재배치
    df = df[['role', 'question', 'output']]
    df.columns = ['직무', '문항', '답변(자소서)']
    
    df.to_csv(csv_path, index=False, encoding='utf-8-sig') # Excel 호환을 위해 utf-8-sig 사용
    print(f"✅ 변환 완료: {csv_path}")

if __name__ == "__main__":
    jsonl_file = Path("data/finetune/hcx_finetune_data.jsonl")
    csv_file = Path("data/finetune/hcx_finetune_data_review.csv")
    
    if jsonl_file.exists():
        convert_jsonl_to_csv(jsonl_file, csv_file)
    else:
        print(f"❌ 파일을 찾을 수 없습니다: {jsonl_file}")
