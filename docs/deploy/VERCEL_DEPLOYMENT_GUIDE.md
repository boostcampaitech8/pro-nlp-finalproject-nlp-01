# Vercel CI/CD 배포 가이드 (GitHub Actions 연동)

이 문서는 GitHub Organization 리포지토리에서 Vercel Pro(유료) 플랜 없이 **Hobby(무료) 플랜**으로 자동 배포를 설정하는 방법을 설명합니다.

---

## 1. 사전 준비항목

GitHub Actions에서 Vercel로 명령을 보내기 위해 다음 3가지 값이 필요합니다.

### A. Vercel Access Token 발급
1. [Vercel Token 설정 페이지](https://vercel.com/account/tokens)에 접속합니다.
2. **Create** 버튼을 클릭합니다.
3. 이름(예: `github-actions-token`)을 입력하고 범위를 지정한 후 발급받은 문자열을 따로 복사해둡니다. (**`VERCEL_TOKEN`**)

### B. Project ID & Org ID 확인 (CLI 방식)
이미 프로젝트를 한 번 수동 배포(link)했다면 로컬 파일에서 바로 확인 가능합니다.

1. 프로젝트 폴더 내 `frontend/.vercel/project.json` 파일을 엽니다.
2. 다음 값을 확인합니다:
    - `"orgId"`: **`VERCEL_ORG_ID`**
    - `"projectId"`: **`VERCEL_PROJECT_ID`**

---

## 2. GitHub Secrets 등록

발급받은 값들을 GitHub 리포지토리에 등록하여 노출되지 않도록 설정합니다.

1. GitHub 리포지토리 페이지 상단 탭에서 **Settings** 클릭
2. 왼쪽 사이드바에서 **Secrets and variables** -> **Actions** 클릭
3. **New repository secret** 버튼을 눌러 총 3개를 등록합니다.

| Name | Secret Value |
| :--- | :--- |
| `VERCEL_TOKEN` | Vercel에서 발급받은 Access Token |
| `VERCEL_ORG_ID` | `project.json`의 `orgId` 값 |
| `VERCEL_PROJECT_ID` | `project.json`의 `projectId` 값 |

---

## 3. 배포 워크플로우 작동 확인

설정이 완료되면 `frontend` 브랜치에 코드가 `push`될 때마다 다음 과정이 자동으로 수행됩니다.

1. **Lint & Test**: 코드 품질 및 단위 테스트 검증
2. **Vercel Deploy**: 테스트 통과 시에만 Vercel 프로덕션 환경으로 자동 배포

### 트러블슈팅
- **Error: Input required and not supplied: vercel-token**: GitHub Secrets에 `VERCEL_TOKEN`이 정확히 등록되지 않았을 때 발생합니다.
- **Project not found**: `VERCEL_PROJECT_ID`가 본인 계정의 실제 프로젝트 ID와 일치하는지 확인하십시오.

---

## 4. (참고) 새로운 환경에서 프로젝트 연결하기
만약 `project.json` 파일이 없는 새로운 환경에서 프로젝트를 연결해야 한다면:

```bash
cd frontend
npx vercel link
```
위 명령어를 실행하고 **개인 계정(Hobby Scope)**을 선택하여 프로세스를 완료하면 파일이 다시 생성됩니다.
