import json

def update_items_data():
    path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data\cover_letter_items.json'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Define full content for items
    item_updates = {
        "26": [
            {
                "question": "1. 본인이 ML Engineer로서 기여할 수 있는 핵심 역량과 이를 증명할 수 있는 구체적인 프로젝트 사례를 기술해 주세요.",
                "content": "[데이터 중심 접근법으로 모델의 실전 성능을 극대화하다]\n\n저는 단순히 최신 모델 아키텍처를 적용하는 것에 그치지 않고, 데이터의 품질과 분포를 분석하여 근본적인 성능 향상을 이끌어내는 역량을 갖추고 있습니다. 'Korean Text Classification Cup' 참가 당시, 초기 모델의 성능이 특정 클래스에서 유독 낮은 것을 발견했습니다. 저는 모델을 바꾸는 대신 훈련 데이터의 레이블 노이즈를 수작업으로 전수 조사하여 오분류된 데이터를 정제하고, 클래스별 가중치를 동적으로 조절하는 손실 함수를 도입했습니다. 그 결과 F1-score를 기존 대비 18% 향상시켰으며, 이는 모델 아키텍처 변경보다 데이터 정제가 더 큰 파급효과를 가짐을 실증한 사례였습니다.\n\n또한 'Efficient Transformer' 프로젝트를 통해 대규모 언어 모델의 연산 복잡도를 줄이는 연구를 진행했습니다. 슬라이딩 윈도우 어텐션 구조를 설계하고 RoPE 스케일링 기법을 적용하여, 기존 대비 40% 적은 GPU 메모리만으로도 동일한 길이의 문맥을 처리할 수 있도록 최적화했습니다. 이러한 '실무적 최적화'와 '데이터 중심 사고'는 Superb AI의 R&D 팀이 추구하는 고효율 AI 시스템 구축에 핵심적인 기여가 될 것입니다."
            },
            {
                "question": "2. AI 기술을 실제 서비스에 적용하는 과정에서 겪었던 기술적 한계와 이를 극복한 과정을 구체적으로 설명해 주세요.",
                "content": "[LLM 서비스의 신뢰성을 확보하기 위한 예외 처리 프레임워크 설계]\n\nResumeGap AI 서비스를 개발하며 LLM이 생성하는 응답의 불안정성이라는 기술적 한계에 부딪혔습니다. 특히 복잡한 JSON 형식을 출력해야 하는 상황에서 괄호 누락이나 따옴표 오류로 인해 전체 파싱이 실패하는 경우가 빈번했습니다. 저는 이를 해결하기 위해 Pydantic 스키마를 활용한 'Schema-first' 프롬프트 설계를 도입했습니다. 사전에 정의된 데이터 구조 외의 출력은 허용하지 않도록 제약을 걸고, 그럼에도 발생하는 파싱 에러에 대해서는 '수리 전용 프롬프트'를 통해 오류 부분만 정정하여 재시도하는 자동 복구 로직을 구현했습니다.\n\n이 과정에서 LLM의 자유도를 적절히 제한하면서도 신뢰도를 높이는 것이 서비스화의 핵심임을 깨달았습니다. 결과적으로 파싱 오류율을 40%에서 2% 미만으로 낮추었으며, 사용자에게 항상 일관된 결과를 제공할 수 있게 되었습니다. Superb AI에서도 모델의 생성 능력과 시스템의 견고함 사이의 균형을 맞추는 엔지니어가 되겠습니다."
            }
        ],
        "31": [
            {
                "question": "1. 네이버클라우드 인턴십에 지원한 동기와 해당 직무를 통해 얻고자 하는 바를 기술해 주세요.",
                "content": "[대한민국 AI 생태계의 중심, 네이버클라우드에서 VLOps의 실무를 익히고 싶습니다]\n\n하이퍼클로바X를 필두로 글로벌 수준의 AI 경쟁력을 갖춘 네이버클라우드는 제가 꿈꾸는 VLOps 전문가로 성장하기 위한 최적의 장소입니다. 저는 그동안 다수의 NLP 프로젝트를 진행하며 모델 개발만큼이나 중요한 것이 '데이터 파이프라인의 자동화'와 '학습 실험의 재현성'임을 절감했습니다. 특히 'Collaborative Troubleshooting' 프로젝트에서 팀원들 간의 실험 지표를 통일하고 W&B를 통해 가시화하는 체계를 구축하며, 협업 효율성이 30% 이상 증가하는 것을 목격했습니다.\n\n이번 인턴십을 통해 네이버클라우드의 대규모 멀티모달 데이터를 처리하는 실제 파이프라인 운영 방식을 배우고 싶습니다. 특히 수백만 건의 데이터를 효율적으로 전처리하고, 모델 서빙 시 발생하는 레이턴시와 비용 문제를 해결하는 실전 노하우를 습득하겠습니다. 단순히 업무를 보조하는 것을 넘어, 제가 가진 실험 설계 역량을 바탕으로 VLOps 프로세스의 개선 포인트를 제안하고 기여하는 인재가 되겠습니다."
            }
        ],
        "32": [
            {
                "question": "1. LLM의 효율적인 학습과 운영을 위해 본인이 시도했던 구체적인 기술적 노력과 성과에 대해 작성해 주세요.",
                "content": "[Efficient Transformer: 연산 복잡도 개선을 통한 장문 처리 최적화]\n\n대규모 언어 모델의 활용도가 높아짐에 따라 장문 문맥 처리 효율성은 필수적인 요소가 되었습니다. 저는 'Efficient Transformer for Long-Context Korean QA' 연구를 통해 트랜스포머의 O(n²) 연산 복잡도를 개선하는 프로젝트를 주도했습니다. 핵심 접근법은 '슬라이딩 윈도우 어텐션(Sliding Window Attention)'과 '글로벌 토큰 혼합 구조'의 결합이었습니다. 지역적인 정보는 윈도우 기반으로 처리하여 연산량을 줄이고, 전역적인 문맥은 선별된 글로벌 토큰을 통해 유지하도록 설계했습니다.\n\n실험 결과, 동일한 V100 GPU 환경에서 기존 모델이 1024 토큰에서 메모리 부족(OOM)이 발생했던 반면, 제가 개선한 모델은 4096 토큰까지 안정적으로 처리가 가능했습니다. 또한 한국어 QA 벤치마크 점수에서도 성능 하락 없이 처리 속도를 2배 이상 향상시키는 성과를 거두었습니다. 이러한 '하드웨어 친화적 최적화' 경험은 디노티시아가 추구하는 고성능 저비용 LLM 솔루션 개발에 큰 밑거름이 될 것입니다."
            }
        ]
    }

    # Apply updates
    # We'll replace items for these specific cover_letter_ids
    # First, filter out existing items for these IDs to avoid duplicates if we run multiple times
    updated_ids = set(item_updates.keys())
    new_data = [item for item in data if item["cover_letter_id"] not in updated_ids]
    
    # Add new items with proper incrementing IDs (starting from a safe high number)
    current_item_id = 5000
    for cl_id, items in item_updates.items():
        for i, item_info in enumerate(items):
            new_item = {
                "id": str(current_item_id),
                "cover_letter_id": cl_id,
                "question": item_info["question"],
                "content": item_info["content"],
                "category": "general",
                "hint": "정보 없음",
                "max_length": "1000",
                "key_points": "[]",
                "suggested_improvements": "[]",
                "created_at": "2026-02-05 10:00:00.000000+00",
                "updated_at": "2026-02-05 10:00:00.000000+00",
                "order_index": str(i),
                "title": "정보 없음"
            }
            new_data.append(new_item)
            current_item_id += 1

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

update_items_data()
