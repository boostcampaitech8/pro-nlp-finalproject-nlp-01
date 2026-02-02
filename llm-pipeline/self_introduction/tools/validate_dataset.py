import json
from pathlib import Path

def validate_and_clean_dataset(input_path, output_path):
    stats = {
        "total_records": 0,
        "valid_json": 0,
        "avg_char_count": 0,
        "max_char_count": 0,
        "min_char_count": 99999,
        "metadata_records": 0
    }
    
    clean_data = []
    total_chars = 0
    
    print(f"🧐 데이터셋 점검 시작: {input_path}")
    
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            stats["total_records"] += 1
            try:
                data = json.loads(line)
                stats["valid_json"] += 1
                
                # 메타데이터 확인
                if "metadata" in data:
                    stats["metadata_records"] += 1
                
                # 출력 텍스트(답변) 길이 점검
                output_text = data.get("output", "")
                length = len(output_text)
                total_chars += length
                stats["max_char_count"] = max(stats["max_char_count"], length)
                stats["min_char_count"] = min(stats["min_char_count"], length)
                
                # 학습용 클린 데이터 생성 (HyperCLOVA X 전용 포맷 변환)
                # HCX 포맷: C_ID, T_ID, Text(User), Completion(AI), System_Prompt(Optional)
                
                # System Prompt는 고정값 사용
                system_prompt = (
                    "당신은 IT 개발 직군 전문 자기소개서 작성 도우미입니다. "
                    "지원자의 경험(Context)과 기업 정보(Target)를 분석하여, "
                    "해당 기업의 인재상에 부합하는 논리적이고 전문적인 자소서를 작성하세요."
                )
                
                # Text 필드 조합: [기업정보/핵심경험/문항] 통합
                input_context = data.get("input", "")
                instruction = data.get("instruction", "")
                
                combined_text = f"{input_context}\n\n{instruction}"
                
                clean_entry = {
                    "System_Prompt": system_prompt,      # 가이드 준수: 첫 번째 열
                    "C_ID": stats["total_records"] - 1,  # 0부터 시작
                    "T_ID": 0,                           # Single turn
                    "Text": combined_text,
                    "Completion": output_text
                }
                clean_data.append(clean_entry)
                
            except Exception as e:
                print(f"❌ 라인 {stats['total_records']} 파싱 에러: {e}")

    if stats["total_records"] > 0:
        stats["avg_char_count"] = total_chars / stats["total_records"]

    # 결과 리포트 출력
    print("\n--- 📊 데이터셋 품질 리포트 ---")
    print(f"✅ 전체 레코드 수: {stats['total_records']}")
    print(f"✅ 정상 JSON 수: {stats['valid_json']}")
    print(f"✅ 메타데이터 포함 수: {stats['metadata_records']}")
    print(f"📏 평균 글자 수: {stats['avg_char_count']:.1f}자")
    print(f"📏 최대/최소 길이: {stats['max_char_count']}자 / {stats['min_char_count']}자")
    print("------------------------------\n")

    # 학습 전용 파일 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in clean_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"🚀 학습 전용 클린 데이터셋 저장 완료: {output_path}")

if __name__ == "__main__":
    base_dir = Path("../data/finetune")
    input_file = base_dir / "hcx_finetune_data.jsonl"
    output_file = base_dir / "hcx_finetune_train_ready.jsonl"
    
    if input_file.exists():
        validate_and_clean_dataset(input_file, output_file)
    else:
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
