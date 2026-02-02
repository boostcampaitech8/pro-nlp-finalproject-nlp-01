
# 🚀 HyperCLOVA X Fine-tuning Pipeline

이 모듈은 **HyperCLOVA X (HCX-007)** 모델을 파인튜닝하기 위한 고품질 자소서 데이터셋 생성 및 검증 파이프라인입니다.
실제 기업의 채용 프로세스를 시뮬레이션(RAG)하여, 단순한 문장 생성이 아닌 **"직무 적합성 분석 및 논리적 서술"**을 학습시키는 것을 목표로 합니다.

---

## 📂 디렉토리 구조 및 핵심 파일
```bash
llm-pipeline/self_introduction/
├── generate_dataset.py    # [메인] 데이터 생성 실행 스크립트 (CLI)
├── validate_dataset.py    # [검증] 데이터 포맷 및 품질 점검 스크립트
├── deep_verify.py         # [심화] 중복 및 다양성 정밀 분석 스크립트
├── src/finetune/          # [모듈] 파이프라인 핵심 로직
│   ├── generator.py       # 데이터 생성 클래스 (FinetuneDataGenerator)
│   ├── comparison.py      # A/B 테스트 로직
│   └── ...
└── data/finetune/         # [결과] 생성된 데이터 저장소
    ├── hcx_finetune_data.jsonl        # (Raw) 생성된 원본 데이터
    └── hcx_finetune_train_ready.jsonl # (Final) 학습용 변환 데이터
```

---

## 🛠️ 사용 방법 (How to Use)

### 1. 데이터 생성 (Generate)
가장 핵심적인 명령어로, 설정한 개수만큼 고품질 자소서 데이터를 생성합니다.
기존 데이터가 있다면 **자동으로 이어쓰기(Append)** 모드로 동작합니다.

```bash
# 기본 실행 (100개 목표)
python generate_dataset.py generate

# 개수 지정 실행 (예: 총 400개 목표)
python generate_dataset.py generate --count 400

# 대량 생성 (예: 총 2,000개 목표)
python generate_dataset.py generate --count 2000
```
> **Tip**: `--count` 옵션은 **"최종적으로 도달하고자 하는 총 개수"**를 의미합니다.
> (예: 이미 100개가 있는데 `--count 400`을 실행하면, 300개를 추가 생성하여 400개를 맞춥니다.)

### 2. A/B 테스트 (Compare)
모델(예: DeepSeek vs Gemini) 성능을 비교하고 싶을 때 사용합니다.
```bash
python generate_dataset.py compare
```

### 3. 데이터 검증 (Validate)
생성된 데이터가 HyperCLOVA X 포맷에 맞는지, 품질에 문제가 없는지 확인합니다.
이 명령어를 실행하면 학습용 최종 파일(`hcx_finetune_train_ready.jsonl`)이 함께 생성됩니다.
```bash
python validate_dataset.py
```

### 4. 정밀 분석 (Deep Verify)
중복 데이터 유무, 직무/기업 다양성 분포 등을 심층 분석합니다.
```bash
python deep_verify.py
```

---

## 📊 데이터 포맷 설명 (HCX 규격)

HyperCLOVA X Studio 학습을 위해 다음과 같은 필드로 구성됩니다.

| 필드명 | 설명 | 예시 |
| :--- | :--- | :--- |
| **C_ID** | Conversation ID (대화 고유 번호) | `0`, `1`, `2` ... |
| **T_ID** | Turn ID (대화 내 순서) | `0` (단일 턴이므로 항상 0) |
| **System_Prompt** | AI의 역할(Persona) 정의 | "당신은 IT 개발 직군 전문 자소서 도우미입니다..." |
| **Text** | 사용자 입력 (User Input) | `[핵심 경험 요약]` + `[기업 분석 정보]` + `[문항]`을 하나로 합친 텍스트 |
| **Completion** | AI의 이상적인 답변 (Target) | 전문가 수준으로 작성된 고품질 자소서 본문 |

---

## 💡 주요 특징

1.  **RAG 시뮬레이션**: 단순히 "자소서 써줘"가 아니라, **[경험]**과 **[기업 정보]**를 입력으로 주어, AI가 이를 분석하고 반영하는 능력을 기르도록 설계되었습니다.
2.  **다양성 확보**:
    *   **직무**: 백엔드, 프론트엔드, AI, 데이터, DevOps, 보안, 앱 개발, 기획 등 전 직군 커버
    *   **도메인**: 핀테크, 커머스, 제조, 게임, 모빌리티, AI 스타트업 등 다양한 산업군 반영
3.  **Human-like Quality**:
    *   성공 경험뿐만 아니라 **"실패와 갈등(The Struggle)"**, **"구체적 수치"**, **"기술적 의사결정 과정"**을 포함하도록 프롬프트가 고도화되었습니다.

---

## ⚠️ 주의사항
*   **API 비용**: DeepSeek V3 모델 사용 시 토큰 비용이 발생합니다. (단, 성능 대비 매우 저렴함)
*   **생성 속도**: 고품질 데이터를 위해 Chain of Thought(생각하는 과정)를 거치므로, 1개 생성에 약 30~60초가 소요됩니다. 400개 생성 시 약 3~4시간을 예상해 주세요.
*   **중단/재개**: 생성 도중 중단하더라도(Ctrl+C), 다시 명령어를 실행하면 마지막 지점부터 이어서 생성합니다.
