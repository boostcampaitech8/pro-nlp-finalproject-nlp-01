# Git 브랜치 전략 (Simple Flow)

본 프로젝트는 아래의 계층 구조를 따르는 **수직적 브랜치 전략**을 사용합니다.  
상위 브랜치에서 하위 브랜치를 생성하고, 작업 완료 후 다시 상위 브랜치로 병합합니다.

## 1. 브랜치 계층 구조 (Hierarchy)

전체적인 흐름은 `main`을 최상위로 하여 아래로 내려가는 구조입니다.

`main`  
↴  
`release`  
↴  
`develop`  
↴  
`backend` / `frontend`  
↴  
`feature/*`

---

## 2. 브랜치별 역할

### 1단계: Main (`main`)
- **최상위 브랜치**: 언제나 배포 가능한 무결점 상태를 유지합니다.
- **병합 규칙**: 오직 `release` 브랜치에서만 병합됩니다.

### 2단계: Release (`release`)
- **배포 대기 브랜치**: 실서버 배포 전 최종 테스트를 진행합니다.
- **흐름**: `develop`에서 생성 -> 검증 완료 -> `main`으로 병합 (배포)

### 3단계: Develop (`develop`)
- **통합 개발 브랜치**: 백엔드와 프론트엔드 작업이 하나로 합쳐지는 곳입니다.
- **흐름**: `backend`와 `frontend`의 변경 사항을 수시로 병합하여 통합 테스트를 수행합니다.

### 4단계: Part Branches (`backend` / `frontend`)
- **파트별 메인 브랜치**: 각 파트(Server/Client)의 개발 베이스캠프입니다.
- **흐름**: 
  - `develop`에서 분기되어 계속 유지됩니다.
  - 각 파트 개발자들은 이 브랜치를 기준으로 `feature`를 생성합니다.

### 5단계: Feature (`feature/*`)
- **작업 브랜치**: 실제 기능 구현이 이루어지는 곳입니다.
- **작명 규칙**: `feature/기능명` (예: `feature/login`, `feature/api-setup`)
- **흐름**: 
  - Backend 개발자: `backend` -> `feature` -> `backend` (PR)
  - Frontend 개발자: `frontend` -> `feature` -> `frontend` (PR)

---

## 3. 요약 (Summary)

> **"위에서 아래로 분기하고, 아래에서 위로 병합한다."**

1. `main`에서 `release` 준비
2. `release`는 `develop`의 내용을 바탕으로 생성
3. `develop`은 `backend`/`frontend`의 내용을 통합
4. 각 개발자는 `backend` or `frontend`에서 `feature`를 따서 작업 후 복귀
