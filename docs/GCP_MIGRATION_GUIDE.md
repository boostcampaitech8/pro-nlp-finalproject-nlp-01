# Google Cloud Platform (GCP) 마이그레이션 가이드

이 문서는 기존 Render/Supabase 환경에서 **Backend Compute를 Google Cloud Run으로 이전**하기 위한 설정 가이드입니다. Database는 Supabase를 유지합니다.

## 1. 하드웨어/인프라 설정 (Google Cloud Console)

### 1.1 프로젝트 생성 및 API 활성화
1. [Google Cloud Console](https://console.cloud.google.com/) 접속.
2. 새 프로젝트 생성 (예: `pro-nlp-backend`).
3. **Billing(결제)** 계정 연결.
4. 검색창에 다음 API를 검색하여 **Enable(활성화)**:
   - **Cloud Run API**
   - **Artifact Registry API**

### 1.2 Artifact Registry 리포지토리 생성
Docker 이미지를 저장할 저장소입니다.
1. Console에서 **Artifact Registry** 이동.
2. **CREATE REPOSITORY** 클릭.
   - **Name**: `pro-nlp-repo` (워크플로우 파일의 `REPOSITORY` 값과 일치해야 함)
   - **Format**: `Docker`
   - **Region**: `asia-northeast3` (Seoul) 또는 `asia-northeast1` (Tokyo). (워크플로우의 `GAR_LOCATION`과 일치해야 함)
3. **CREATE** 클릭.

### 1.3 Service Account (서비스 계정) 생성
GitHub Actions가 GCP에 접근하기 위한 권한입니다.
1. **IAM & Admin** > **Service Accounts** 이동.
2. **+ CREATE SERVICE ACCOUNT** 클릭.
   - **Name**: `github-actions-deployer`
3. **Grant parts access to this project (권한 부여)** 단계에서 다음 역할(Role) 추가:
   - `Cloud Run Developer`
   - `Service Account User`
   - `Artifact Registry Writer`
4. 완료 후, 생성된 계정 클릭 > **KEYS** 탭 > **ADD KEY** > **Create new key** > **JSON** 선택.
5. 다운로드된 JSON 파일은 보안에 유의하여 보관하세요. (GitHub Secret에 사용)

---

## 2. GitHub Secrets 설정

GitHub 저장소의 **Settings > Secrets and variables > Actions** 로 이동하여 다음 `New repository secret`을 추가합니다.

| Secret 이름 | 값(Value) | 설명 |
| :--- | :--- | :--- |
| `GCP_PROJECT_ID` | `your-project-id` | GCP 프로젝트 ID (이름 아님, ID 확인 필요) |
| `GCP_SA_KEY` | `{ ...json content... }` | 다운로드 받은 JSON 파일 내용 전체 |
| `DATABASE_URL` | `postgresql://...` | 기존 Supabase Connection String (Transaction Pooler 권장) |
| `SECRET_KEY` | `...` | Backend JWT Secret Key |

---

## 3. 배포 방법 (Manual)

이제 배포는 **수동**으로 진행됩니다.

1. GitHub 저장소 > **Actions** 탭 이동.
2. 좌측 메뉴에서 **Backend GCP Deploy** 선택.
3. 우측 **Run workflow** 버튼 클릭 > Branch: `develop` > **Run workflow**.

---

## 4. 참고 사항
- **Cloud Run URL**: 첫 배포가 성공하면 Cloud Run 콘솔에서 생성된 URL을 확인할 수 있습니다.
- **Frontend 연결**: Frontend의 `NEXT_PUBLIC_API_URL` 환경변수를 Cloud Run URL로 변경해주어야 합니다.
- **403 Forbidden 에러 시**: Cloud Run 서비스의 **[보안]** 탭에서 **"공개 액세스 허용 (Allow unauthenticated invocations)"**을 선택해야 외부에서 접속 가능합니다.
