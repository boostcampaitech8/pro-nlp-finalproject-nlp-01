import json

def fill_all_mock_data():
    cl_path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data\cover_letters.json'
    items_path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data\cover_letter_items.json'
    
    DEMO_USER_ID = "6"
    
    with open(cl_path, 'r', encoding='utf-8') as f:
        cls = json.load(f)
    
    cl_ids = [c["id"] for c in cls]
    
    # 1. Update all CLs to be owned by demo user and clean titles
    for cl in cls:
        cl["user_id"] = DEMO_USER_ID
        cl["title"] = cl["title"].replace(" (생성 중)", "").replace(" 자소서", "") + " 자소서"
        cl["processing_status"] = "COMPLETED"
        
    with open(cl_path, 'w', encoding='utf-8') as f:
        json.dump(cls, f, ensure_ascii=False, indent=2)

    # 2. Update Items
    with open(items_path, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    existing_cl_ids_in_items = set([i["cover_letter_id"] for i in items])
    
    # Sample High-Quality Content sets for different roles
    samples = [
        {
            "q": "1. 지원 동기와 포부에 대해 기술해 주세요.",
            "a": "기술적 한계를 극복하고 사용자에게 실질적인 가치를 제공하는 개발자가 되고 싶습니다. 귀사의 혁신적인 환경에서 저의 백엔드 설계 역량을 발휘하여 안정적이고 확장 가능한 시스템을 구축하겠습니다. 입사 후에는 인프라 최적화와 코드 품질 향상에 집중하여 팀의 생산성을 높이는 데 기여하겠습니다."
        },
        {
            "q": "2. 본인의 기술적 강점과 이를 활용한 프로젝트 사례를 설명해 주세요.",
            "a": "저의 강점은 복잡한 데이터 구조를 효율적으로 처리하는 알고리즘 최적화 역량입니다. 지난 프로젝트에서 데이터 처리 파이프라인의 병목 현상을 발견하고, 멀티 프로세싱과 캐싱 전략을 도입하여 처리 속도를 40% 향상시킨 경험이 있습니다. 이러한 경험을 바탕으로 귀사의 대규모 데이터 처리 효율을 극대화하겠습니다."
        },
        {
            "q": "3. 협업 과정에서 겪은 갈등과 해결 방안을 기술해 주세요.",
            "a": "팀 프로젝트 진행 중 설계 방향성에 대한 의견 차이가 있었으나, 각 대안의 장단점을 수치화하여 비교 분석한 자료를 바탕으로 팀원들을 설득했습니다. 결국 데이터 일관성을 보장하면서도 성능을 챙길 수 있는 중재안을 도출하여 프로젝트를 성공적으로 마쳤습니다. 소통과 논리를 바탕으로 팀의 시너지를 이끌어내는 인재가 되겠습니다."
        }
    ]

    new_items = []
    item_id_counter = 6000
    
    # Ensure every CL has items
    for cl_id in cl_ids:
        # If no items or poor items, replace/add
        cl_items = [i for i in items if i["cover_letter_id"] == cl_id]
        
        # If cl_id is in my previous updates (26, 31, 32, 33, 35, 38), keep them but fix encoding/id if needed
        if cl_id in ["26", "31", "32", "33", "35", "38"]:
            for i in cl_items:
                i["user_id"] = DEMO_USER_ID # Ensure consistency
                new_items.append(i)
        else:
            # For others, add sample items
            for idx, s in enumerate(samples):
                new_items.append({
                    "id": str(item_id_counter),
                    "cover_letter_id": cl_id,
                    "question": s["q"],
                    "content": s["a"],
                    "category": "general",
                    "hint": "정보 없음",
                    "max_length": "1000",
                    "order_index": str(idx),
                    "title": s["q"].split(". ")[-1].split(" ")[0]
                })
                item_id_counter += 1

    with open(items_path, 'w', encoding='utf-8') as f:
        json.dump(new_items, f, ensure_ascii=False, indent=2)

fill_all_mock_data()
