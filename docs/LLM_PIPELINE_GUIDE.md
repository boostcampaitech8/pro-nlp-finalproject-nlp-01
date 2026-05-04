# HTTP 기반 LLM 파이프라인 개발 가이드

이 문서는 **Podman, LangGraph, LangFuse**를 활용하여 고도화된 LLM 파이프라인을 구축하고, 이를 **HTTP 프로토콜**을 통해 프론트엔드와 연결하는 방법을 설명합니다.

---

## 1. 아키텍처 개요

전체 시스템은 가벼운 HTTP 통신을 기반으로 하며, 단순한 LLM 호출을 넘어 **상태 관리(State Management)**와 **관측성(Observability)**에 초점을 맞춥니다.

- **Frontend**: 바닐라 JS (Fetch API) + CSS (Premium UI)
- **Backend API**: FastAPI (Python)
- **Orchestration**: LangGraph (LangChain 기반의 복잡한 워크플로우 제어)
- **Infrastructure**: Podman (도커 호환 컨테이너 환경)
- **Monitoring**: LangFuse (Trace, Cost, Latency 분석)

---

## 2. 프론트엔드: 비동기 HTTP 통신 (JS)

프론트엔드는 복잡한 프레임워크 없이도 Fetch API를 통해 LLM 백엔드와 통신할 수 있습니다.

```javascript
// LLM 스트리밍 또는 일반 호출 예시
async function askLLM(prompt) {
    const response = await fetch('http://localhost:8000/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt })
    });

    const data = await response.json();
    console.log('LLM 응답:', data.reply);
    return data.reply;
}
```

### 2.1 Premium UI Tip (CSS)
사용자 경험을 높이기 위한 단순하면서도 세련된 CSS 예시입니다.
```css
.chat-container {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
}
```

---

## 3. 백엔드: Podman & LangGraph

### 3.1 Podman 설정
Docker 대신 오픈소스인 **Podman**을 사용하여 환경을 격리합니다. `docker-compose`와 호환되는 `podman-compose`를 추천합니다.

```bash
# 로컬 개발 환경 실행
podman-compose up -d
```

### 3.2 LangGraph 워크플로우 (LangChain < LangGraph)
단순한 Chain 구조보다 순환(Cycle)과 상태(State)를 지원하는 **LangGraph**를 사용하여 '생각하는 에이전트'를 구현합니다.

```python
from langgraph.graph import StateGraph, END

# 1. 상태 정의
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# 2. 노드 정의 (LLM 호출, 도구 사용 등)
def call_model(state):
    # LLM 로직
    return {"messages": [response]}

# 3. 그래프 구성
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

app = workflow.compile()
```

---

## 4. 관측성: LangFuse (LangSmith < LangFuse)

개발 단계부터 운영까지 LLM의 응답 품질과 비용을 추적하기 위해 **LangFuse**를 사용합니다.

### 4.1 LangSmith vs LangFuse

| 특징 | LangSmith | LangFuse |
| :--- | :--- | :--- |
| **접근성** | SaaS 중심, 초기 설정 매우 쉬움 | SaaS 및 Self-hosting 지원 |
| **비용** | 상용화 시 비용 상승폭이 큼 | 오픈소스 기반으로 유연한 비용 구조 |
| **기능** | 데이터셋 및 평가(Eval) 특화 | 트레이싱, 피드백 관리, UI/UX 최적화 |
| **결론** | 실험적 단계에서 적합 | **커스텀 배포 및 확장성**을 고려한다면 LangFuse 추천 |

```python
from langfuse.callback import CallbackHandler

# LangChain/LangGraph 연동
handler = CallbackHandler(
    public_key="pk-lf-...",
    private_key="sk-lf-...",
    host="https://cloud.langfuse.com"
)

# 실행 시 핸들러 주입
app.invoke(input_data, config={"callbacks": [handler]})
```

---

## 5. 파이프라인 배포 팁

1. **RESTful API**: FastAPI를 사용하여 `/chat`, `/analyze` 등 명확한 엔드포인트를 설계하세요.
2. **Environment Variables**: API Key, DB URL 등은 `.env` 파일로 분리하여 Podman 실행 시 주입합니다.
3. **CORS 설정**: 프론트엔드(HTML)와 백엔드 간의 도메인이 다를 경우 반드시 CORS 미들웨어를 설정해야 합니다.

---

## 결론
이 조합은 **확장성(LangGraph)**과 **투명성(LangFuse)**을 동시에 확보할 수 있는 현대적인 LLM 애플리케이션의 정석입니다. 간단한 HTTP 프로토콜로 시작하여 필요에 따라 WebSocket이나 Streaming으로 확장해 보세요.
