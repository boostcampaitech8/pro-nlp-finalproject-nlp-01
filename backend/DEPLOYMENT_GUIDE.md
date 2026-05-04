# System Deployment Guide (Backend & Jobs)

This guide covers the deployment of the split architecture: **Backend API** (Cloud Run Service) and **Async Worker** (Cloud Run Jobs).

## 1. Architecture Overview

- **Backend (`modu-chwieop-backend`)**: Optimized for high-concurrency API requests. Handles Auth, CRUD, and Job Triggering.
- **Jobs (`modu-chwieop-jobs`)**: Optimized for heavy AI/NLP processing (longer timeout, higher memory). Handles Portfolio/Cover Letter generation.
- **Common (`common/`)**: Shared library containing database models and schemas, copied into both images during build.

## 2. Prerequisites

1.  **Google Cloud SDK**
    ```bash
    gcloud auth login
    gcloud config set project [YOUR_PROJECT_ID]
    ```
2.  **APIs Enabled**: Cloud Run, Artifact Registry, Cloud Build.

## 3. Build & Push Images

Both services are built from the **Root Directory** so they can access the `common/` package.

### 3.1 Backend API Image
```bash
# Build context is ROOT (.)
gcloud builds submit --tag asia-northeast3-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/modu-chwieop-backend:latest -f backend/Dockerfile .
```

### 3.2 Jobs Worker Image
```bash
# Build context is ROOT (.)
gcloud builds submit --tag asia-northeast3-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/modu-chwieop-jobs:latest -f jobs/Dockerfile .
```

## 4. Deploy Backend (Cloud Run Service)

```bash
gcloud run deploy modu-chwieop-backend \
  --image asia-northeast3-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/modu-chwieop-backend:latest \
  --region asia-northeast3 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=[YOUR_DB_URL]" \
  --set-env-vars "PYTHONPATH=/app" \
  --set-env-vars "GOOGLE_API_KEY=[KEY]" \
  --set-env-vars "SECRET_KEY=[KEY]" \
  --set-env-vars "ALGORITHM=HS256" \
  --set-env-vars "NCP_CLOVASTUDIO_API_KEY=[KEY]" \
  --set-env-vars "NCP_CLOVASTUDIO_BASE_URL=[KEY]" \
  --set-env-vars "INTERNAL_API_SECRET=[YOUR_INTERNAL_SECRET]"
```

## 5. Deploy Worker (Cloud Run Job)

Cloud Run Job is created once and then executed (triggered) by the backend or manually.

```bash
gcloud run jobs create modu-chwieop-jobs \
  --image asia-northeast3-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/modu-chwieop-jobs:latest \
  --region asia-northeast3 \
  --tasks 1 \
  --parallelism 1 \
  --max-retries 0 \
  --memory 2Gi \
  --cpu 1 \
  --set-env-vars "DATABASE_URL=[YOUR_DB_URL]" \
  --set-env-vars "PYTHONPATH=/app" \
  --set-env-vars "GOOGLE_API_KEY=[KEY]" \
  --set-env-vars "NCP_CLOVASTUDIO_API_KEY=[KEY]" \
  --set-env-vars "GITHUB_TOKEN=[KEY]" \
  --set-env-vars "NOTION_TOKEN=[KEY]" \
  --set-env-vars "INTERNAL_API_SECRET=[YOUR_INTERNAL_SECRET]"
```

### Triggering a Job
The backend triggers this job automatically via API, but you can manually test:
```bash
# Run Portfolio Extraction for ID 1
gcloud run jobs execute modu-chwieop-jobs --args="--task=portfolio_extraction --id=1" --region asia-northeast3
```

## 6. CI/CD Pipeline & Environments

The project uses a dynamic deployment strategy based on GitHub Branches.

### 6.1 Branching Strategy

| Branch | Environment | Cloud Run Service | Vercel Deployment |
| :--- | :--- | :--- | :--- |
| **`develop`** | **Production** | `modu-chwieop-backend` | Production Domain (`--prod`) |
| **`feature/async-architecture-refactor`** | **Preview** | `modu-chwieop-backend-preview` | Preview URL (Generating...) |

*Note: Any branch matching `feature/**` patterns will trigger a Preview deployment.*

### 6.2 Workflows
- **Backend**: `.github/workflows/gcp-deploy.yml`
    - Detects branch name.
    - If `develop`: Deploys to Prod Service.
    - If others: Deploys to Preview Service (creates it if missing).
- **Frontend**: `.github/workflows/frontend-deploy.yml`
    - If `develop`: Deploys to Vercel Prod.
    - If others: Deploys to Vercel Preview.

## 7. GitHub Secrets Configuration

Workflows require the following Secrets to be set in your GitHub repository:

| Secret Name | Description | Required |
| :--- | :--- | :--- |
| `GCP_PROJECT_ID` | GCP Project ID | Yes |
| `GCP_SA_KEY` | GCP Service Account Key (JSON) | Yes |
| `VERCEL_TOKEN` | Vercel API Token | Yes |
| `VERCEL_ORG_ID` | Vercel Org ID | Yes |
### GitHub Secrets Configuration

| Secret Name | Description | Required |
| :--- | :--- | :--- |
| `GCP_PROJECT_ID` | GCP Project ID | Yes |
| `GCP_SA_KEY` | GCP Service Account Key (JSON) | Yes |
| `VERCEL_TOKEN` | Vercel API Token | Yes |
| `VERCEL_ORG_ID` | Vercel Org ID | Yes |
| `VERCEL_PROJECT_ID` | Vercel Project ID | Yes |
| `KAKAO_REST_API_KEY` | Kakao REST API Key | Yes |
| **Production Environment** | | |
| `PROD_BACKEND_URL` | Production Backend URL | Yes |
| `PROD_DATABASE_URL` | Production Database URL | Yes |
| `PROD_SECRET_KEY` | Production JWT Secret Key | Yes |
| `PROD_GOOGLE_API_KEY` | Production Google (Gemini) API Key | Yes |
| `PROD_KAKAO_CLIENT_SECRET` | Production Kakao Client Secret | Yes |
| `PROD_KAKAO_REDIRECT_URI` | Production Kakao Redirect URI | Yes |
| `PROD_NCP_CLOVASTUDIO_BASE_URL` | Production NCP Base URL | Yes |
| `PROD_NCP_CLOVASTUDIO_API_KEY` | Production NCP API Key | Yes |
| `INTERNAL_API_SECRET` | Secret for Internal API communication (Backend <-> Jobs) | Yes |
| **Preview Environment** | | |
| `PREVIEW_BACKEND_URL` | Preview Backend URL | No (Fallback to PROD) |
| `PREVIEW_DATABASE_URL` | Preview Database URL | No (Fallback to PROD) |
| `PREVIEW_SECRET_KEY` | Preview JWT Secret Key | No (Fallback to PROD) |
| `PREVIEW_GOOGLE_API_KEY` | Preview Google API Key | No (Fallback to PROD) |
| `PREVIEW_KAKAO_CLIENT_SECRET` | Preview Kakao Client Secret | No (Fallback to PROD) |
| `PREVIEW_KAKAO_REDIRECT_URI` | Preview Kakao Redirect URI | No (Fallback to PROD) |
| `PREVIEW_NCP_CLOVASTUDIO_BASE_URL`| Preview NCP Base URL | No (Fallback to PROD) |
| `PREVIEW_NCP_CLOVASTUDIO_API_KEY` | Preview NCP API Key | No (Fallback to PROD) |

> [!IMPORTANT]
> **Kakao Login 설정**:
> 1. [Kakao Developers](https://developers.kakao.com/) 콘솔의 **내 애플리케이션 > 제품 설정 > 카카오 로그인**으로 이동합니다.
> 2. **Redirect URI** 항목에 다음 주소들을 모두 추가해야 합니다:
>    - 프로덕션: `https://pro-nlp-finalproject-nlp-01.vercel.app/auth/kakao/callback`
>    - 프리뷰 (현재 브랜치): `https://pro-nlp-finalproject-nlp-01-pileuszu-nlp-01-final.vercel.app/auth/kakao/callback`
>    - 로컬 테스트: `http://localhost:3000/auth/kakao/callback`

> [!TIP]
> **Separating Environments**: To have your Preview Frontend talk to your Preview Backend:
> 1. Push to a feature branch (this creates `modu-chwieop-backend-preview` on Cloud Run).
> 2. Copy the URL of the `modu-chwieop-backend-preview` service.
> 3. Add it as `GCP_PREVIEW_BACKEND_URL` in GitHub Secrets.
> 4. Future Preview deployments will automatically point to this URL.

## 8. Troubleshooting

- **ImportError: No module named 'common'**: ensure `PYTHONPATH=/app` is set and `COPY common/ ./common/` exists in Dockerfile.
- **DB Connection**: Ensure `DATABASE_URL` is correct. If using Supabase, `backend` uses `asyncpg` (auto-configured in code) but `jobs` uses the same. Use Transaction Pooler (port 6543) for best performance in serverless.
