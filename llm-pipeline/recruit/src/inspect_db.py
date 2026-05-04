from recruit_indexer import RecruitIndexer
import json

def main():
    """
    Vector DB에 저장된 전체 데이터를 조회하여 요약 출력하는 예시 스크립트입니다.
    팀원들이 DB 상태를 확인하고자 할 때 사용할 수 있습니다.
    """
    indexer = RecruitIndexer()
    
    print("\n--- [Vector DB 전체 데이터 조회] ---")
    try:
        # 전체 데이터 가져오기
        all_data = indexer.get_all_documents()
        
        ids = all_data.get('ids', [])
        metadatas = all_data.get('metadatas', [])
        
        total_count = len(ids)
        print(f"현재 DB에 저장된 총 공고 수: {total_count}개")

        if total_count == 0:
            print("DB가 비어있습니다. run_recruit_indexer.py를 실행하여 데이터를 먼저 인덱싱해주세요.")
            return

        print("\n--- 전체 공고 목록 ---")
        # 상위 20개만 출력 (데이터가 너무 많을 경우 대비)
        display_limit = 20
        for i in range(min(total_count, display_limit)):
            meta = metadatas[i]
            unique_id = ids[i]
            
            # 메타데이터에 unique_id가 있는지 확인 (업데이트 여부 확인용)
            meta_uid = meta.get('unique_id', 'N/A')
            
            print(f"[{i+1}] {meta.get('company')} - {meta.get('title')}")
            print(f"    - DB ID: {unique_id}")
            print(f"    - Meta Unique_ID: {meta_uid}")
            # print(f"    - Link: {meta.get('link')}")

        if total_count > display_limit:
            print(f"\n... 그 외 {total_count - display_limit}개의 공고가 더 있습니다.")

        # 첫 번째 데이터 상세 JSON 출력 추가
        print("\n--- 첫 번째 데이터 상세 (JSON 형식) ---")
        first_data_detail = {
            "id": ids[0],
            "metadata": metadatas[0],
            "content": all_data.get('documents', [])[0] if all_data.get('documents') else ""
        }
        print(json.dumps(first_data_detail, indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"조회 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
