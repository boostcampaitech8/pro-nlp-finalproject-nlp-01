# Git 커밋 컨벤션 (Git Commit Convention)

일관된 커밋 히스토리 관리를 위해 아래의 규칙을 준수하여 커밋 메시지를 작성합니다.

## 1. 커밋 메시지 구조
기본적인 구조는 **제목(Subject)**, **본문(Body)**, **꼬리말(Footer)** 로 구성됩니다.

```text
type: key changes

body (optional)

footer (optional)
```

---

## 2. Type (태그 종류)
커밋의 성격을 나타내는 태그입니다. 제목의 가장 앞에 소문자로 작성합니다.

| 태그 | 설명 | 예시 |
|:---:|---|---|
| `feat` | 새로운 기능 추가 | `feat: implement login API` |
| `fix` | 버그 수정 | `fix: fix search result error` |
| `docs` | 문서 수정 (README, 가이드 등) | `docs: update API specification` |
| `style` | 코드 포맷팅, 세미콜론 누락 등 (로직 변경 없음) | `style: apply code formatting` |
| `refactor` | 코드 리팩토링 (기능 변경 없음) | `refactor: rename variables and split functions` |
| `test` | 테스트 코드 추가/수정 | `test: add signup test cases` |
| `chore` | 빌드 업무, 패키지 매니저 설정 등 (프로덕션 코드 변경 없음) | `chore: update package versions` |

---

## 3. 작성 규칙

### 제목 (Subject)
- **명령문**으로 작성합니다. (예: "수정했음" -> "수정")
- 끝에 마침표(`.`)를 찍지 않습니다.
- 50자를 넘기지 않도록 노력합니다.
- 영문일 경우 첫 글자는 소문자로 작성하는 것을 권장합니다. (팀 규칙에 따름)

### 본문 (Body)
- 선택 사항입니다.
- 제목으로 표현할 수 없는 상세한 내용을 적습니다.
- **무엇을**, **왜** 변경했는지 설명합니다.

### 꼬리말 (Footer)
- 선택 사항입니다.
- 이슈 트래커 ID를 적을 때 사용합니다. (예: `Fixes: #123`, `Related to: #45`)

---

## 4. 예시 (Examples)

**간단한 커밋 (제목만 있는 경우)**
```
fix: fix token expiration error during login
```

**상세 커밋 (본문과 꼬리말 포함)**
```
feat: add user profile image upload feature

Integrate API to allow users to change profile image on My Page
- Include image resizing logic
- Implement AWS S3 upload functionality

Resolves: #42
```
