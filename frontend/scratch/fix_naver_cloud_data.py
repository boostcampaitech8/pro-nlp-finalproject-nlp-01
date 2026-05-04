import json

def fix_naver_cloud_data():
    cl_path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data\cover_letters.json'
    items_path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data\cover_letter_items.json'
    
    DEMO_USER_ID = "6"
    TARGET_CL_ID = "35"

    # 1. Update Cover Letter ownership and title
    with open(cl_path, 'r', encoding='utf-8') as f:
        cls = json.load(f)
    for cl in cls:
        if cl["id"] == TARGET_CL_ID:
            cl["user_id"] = DEMO_USER_ID
            cl["title"] = "NAVER Cloud - LLM Studio Backend Engineer (경력) 자소서"
            cl["content"] = "[대규모 AI 인프라 혁신을 꿈꾸는 백엔드 엔지니어]\n\n네이버클라우드의 LLM Studio는 초거대 AI 시대를 선도하는 핵심 인프라입니다. 저는 이전 프로젝트에서 Redis 분산 락을 활용한 고가용성 시스템 구축과 Spring Batch 기반의 대용량 ETL 최적화를 통해 시스템 신뢰성을 확보한 경험이 있습니다. 이러한 기술적 배경을 바탕으로 LLM Studio의 안정적인 운영과 비용 효율적인 자원 관리 아키텍처 설계에 기여하고자 합니다. 입사 후에는 Kubernetes 기반의 탄력적 서빙 인프라 고도화에 집중하여, 전 세계 사용자들이 끊김 없는 AI 경험을 누릴 수 있도록 뒷받침하겠습니다."
    
    with open(cl_path, 'w', encoding='utf-8') as f:
        json.dump(cls, f, ensure_ascii=False, indent=2)

    # 2. Update Items with full content
    with open(items_path, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    # Remove old corrupted items for ID 35
    items = [i for i in items if i["cover_letter_id"] != TARGET_CL_ID]
    
    # Add new high-quality items
    new_items = [
        {
            "id": "5100",
            "cover_letter_id": TARGET_CL_ID,
            "question": "1. 지원 동기와 입사 후 네이버클라우드에서 실현하고 싶은 커리어 비전을 작성해 주시기 바랍니다.",
            "content": "[LLM Studio의 안정성을 책임지는 백엔드 전문가]\n\n네이버클라우드가 보유한 국내 최대 규모의 AI 컴퓨팅 리소스와 하이퍼클로바X의 기술력에 매료되어 지원했습니다. 저는 대규모 트래픽 환경에서 백엔드 시스템의 정합성을 유지하고 성능을 최적화하는 데 강점이 있습니다. 'QueueNow' 프로젝트에서 초당 수천 건의 요청이 몰리는 환경을 Redis 분산 락으로 제어하며 데이터 무결성을 100% 확보한 경험이 있으며, 이는 LLM Studio의 동시 접속 처리와 리소스 할당 로직에 직접적으로 응용될 수 있습니다.\n\n입사 후에는 첫째, Kubernetes 기반의 마이크로서비스 아키텍처를 고도화하여 모델 서빙의 탄력성을 극대화하겠습니다. 둘째, MLOps 관점에서 모델 배포부터 실시간 모니터링까지의 전 과정을 자동화하여 운영 효율성을 높이겠습니다. 셋째, 클라우드 네이티브 기술을 활용해 추론 비용을 절감할 수 있는 효율적 아키텍처를 연구하여 네이버클라우드의 경쟁력을 높이는 엔지니어가 되겠습니다.",
            "category": "general",
            "hint": "정보 없음",
            "max_length": "1000",
            "key_points": "[\"분산 시스템 동시성 제어\",\"Kubernetes 기반 인프라 최적화\",\"MLOps 자동화 의지\"]",
            "suggested_improvements": "[]",
            "created_at": "2026-02-06 05:16:04+00",
            "updated_at": "2026-02-06 05:16:04+00",
            "order_index": "0",
            "title": "지원 동기 및 비전"
        },
        {
            "id": "5101",
            "cover_letter_id": TARGET_CL_ID,
            "question": "2. 지원 직무와 관련하여 본인이 가진 강점을 구체적인 사례와 함께 기술해 주세요.",
            "content": "[데이터 중심 사고로 시스템 장애 인지 시간을 30% 단축시키다]\n\n저는 백엔드 시스템에서 발생하는 방대한 로그 데이터를 자산화하여 운영 가시성을 확보하는 데 능숙합니다. 'OpsHelper' 프로젝트 당시, 시스템 로그의 급격한 증가로 인해 분석 속도가 저하되는 병목 현상이 발생했습니다. 저는 단순히 서버 사양을 높이는 대신, 로그 수집 주기와 저장 방식을 재설계했습니다. 시간별 로그 파티셔닝과 병렬 배치 처리를 도입하여 분석 속도를 개선했고, 에러 패턴 감지 알고리즘을 최적화하여 장애 인지 시간을 평균 25분에서 17분으로 단축시켰습니다.\n\n이 과정에서 대량의 비정형 데이터를 효율적으로 처리하기 위한 인덱싱 전략과 스트리밍 처리 방식에 대한 깊은 통찰력을 얻었습니다. LLM Studio 운영 시에도 모델 추론 과정에서 발생하는 방대한 로그를 실시간으로 모니터링하고, 이상 징후를 선제적으로 감지하는 지능형 모니터링 시스템 구축에 기여하겠습니다. 기술적 문제 해결을 넘어, 비즈니스 연속성을 보장하는 견고한 시스템을 만드는 것이 저의 핵심 강점입니다.",
            "category": "general",
            "hint": "정보 없음",
            "max_length": "1000",
            "key_points": "[\"대규모 로그 분석 시스템 구축\",\"시스템 가시성 확보 능력\",\"성능 병목 지점 해결 역량\"]",
            "suggested_improvements": "[]",
            "created_at": "2026-02-06 05:16:04+00",
            "updated_at": "2026-02-06 05:16:04+00",
            "order_index": "1",
            "title": "직무 강점"
        }
    ]
    items.extend(new_items)
    
    with open(items_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

fix_naver_cloud_data()
