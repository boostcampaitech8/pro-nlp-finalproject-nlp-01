# 프론트엔드 구현 계획 (Frontend Implementation Plan)

본 문서는 **모두취업: 취업/자소서/포트폴리오 관리형 AI 서비스** 구축을 위한 프론트엔드 기술 스택 및 구현 전략을 정의합니다.

## 1. 기술 스택 (Tech Stack)

### 🏗️ 프레임워크 및 언어
- **Framework**: Next.js 14 (App Router)
  - **이유**: SEO 최적화(공고 페이지), 복잡한 라우팅 구조 관리, SSR/RSC를 통한 성능 이점, AI 기능 연동의 유연성.
- **Language**: TypeScript
  - **이유**: 데이터(자소서, 공고, 포트폴리오 등)의 명확한 타입 정의로 안정적인 개발 및 협업 효율 증대.

### 🗃️ 상태 관리
- **Server State**: TanStack Query (React Query)
  - **용도**: 기업 공고 리스트, 자소서 조회, 포트폴리오 목록 등 서버 데이터 동기화 및 캐싱.
- **Client State**: Zustand
  - **용도**: 로그인 세션, 모달 UI 상태, 단계별 폼 진행 상태 등 가벼운 전역 상태 관리.

### 🎨 스타일링 및 애니메이션
- **CSS Framework**: Tailwind CSS
- **UI Component Library**: shadcn/ui
- **Icons**: Lucide React
- **Animation**: Framer Motion
  - **이유**: 프리미엄 UI 경험을 위한 부드러운 전환 효과(Fade-in, Staggering, Hover interaction) 제공.

### 📝 폼 처리 및 검증
- **Library**: React Hook Form + Zod
  - **용도**: 자소서 작성, 포트폴리오 등록, 설정 등 복잡한 입력 폼의 상태 관리 및 실시간 유효성 검증.

---

## 2. 폴더 구조 (Directory Structure)

`src/app` 폴더 내에서 **Route Groups**를 활용하여 서비스 성격에 따라 레이아웃을 분리했습니다.

```text
src/
 ├── app/
 │   ├── (auth)/                 # 로그인/회원가입 (헤더가 없는 집중형 레이아웃)
 │   │   ├── login/
 │   │   └── signup/
 │   │
 │   └── (main)/                 # 메인 서비스 공간 (내비게이션 바 포함)
 │       ├── recruit/            # 채용 공고 리스트 및 상세
 │       └── my/                 # 마이페이지 (워크스페이스)
 │           ├── portfolios/     # 포트폴리오 관리 (GitHub/Notion 연동)
 │           └── cover-letters/  # 자기소개서 관리 및 AI 첨삭 에디터
 │
 ├── components/                 # 공통 컴포넌트
 │   ├── ui/                     # shadcn/ui 기반 원자적 컴포넌트
 │   └── ...                     # 도메인별 복합 컴포넌트
 ├── hooks/                      # 커스텀 훅
 ├── lib/                        # 유틸리티 및 설정 (utils, providers)
 └── mocks/                      # MSW 핸들러 및 모의 데이터
```

---

## 3. 핵심 디자인 원칙

1.  **Clean & Premium**: 불필요한 장식을 배제하고 여백과 타이포그래피를 활용한 깔끔한 UI를 지향합니다.
2.  **AI Interaction**: AI 분석 중(Loading)이나 결과 확인 시 사용자에게 진행 상황을 명확히 전달하고 자연스러운 애니메이션을 제공합니다.
3.  **Responsive**: 데스크탑 환경에서의 생산성을 최우선으로 하되, 모바일에서도 정보를 명확히 확인할 수 있는 반응형 레이아웃을 제공합니다.

---

## 4. 비동기 처리 전략 (Async Handling)

백엔드의 AI 분석 작업(포트폴리오 분석, 자소서 생성)은 `Cloud Run Jobs`를 통해 비동기로 처리되므로, 프론트엔드는 **Polling** 패턴을 사용합니다.

- **Polling Hook**: `usePolling` 커스텀 훅을 구현하여 `state`가 `PENDING`인 동안 주기적으로 상태를 확인합니다.
- **Optimistic UI**: 미리보기가 가능한 경우 결과 화면을 먼저 보여주거나, 진행률(Progress)을 표시하여 체감 대기 시간을 줄입니다.
- **Notification**: 작업이 완료되면 Toast 알림을 통해 사용자에게 결과를 알립니다.
