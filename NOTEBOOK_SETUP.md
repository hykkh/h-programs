# 노트북에서 hyt.kr/hp 카탈로그 편집 · 배포

**노트북 담당 (전담)**: Hesla — 비밀 다운로드 URL(`tesla.hyt.kr/o/…`),
Hesla APK, Hesla 카드 문구/버전. 이 URL 은 TLS 개인키가 담긴 APK 를 가리키므로
운영 PC 나 공개되는 곳에 절대 두지 않는다.

**이 PC(운영) 에서도 가능**: Hesla 이외 카드 추가·수정, 비번 변경 등 일반 편집.
다만 잠금 안쪽에 Hesla 다운로드 URL 이 이미 들어 있으므로 그 카드 자체는
노트북에서만 손댄다.

---

## 1. 노트북 사전 준비 (한 번만)

### 1-1. 필수 설치

| 도구 | 다운로드 | 확인 |
|---|---|---|
| Git | https://git-scm.com/download/win | `git --version` |
| Python 3.10+ | https://www.python.org/downloads/ (Add to PATH 체크) | `python --version` |
| GitHub CLI | https://cli.github.com/ | `gh --version` |

### 1-2. 폴더 클론

```powershell
mkdir C:\catalog
cd C:\catalog
git clone https://github.com/hykkh/h-programs.git
cd h-programs
```

### 1-3. Python 의존성

```powershell
pip install cryptography requests
```

### 1-4. GitHub 인증 (push 하려면 필수)

```powershell
gh auth login
```
프롬프트: `GitHub.com` → `HTTPS` → `Y` (git 인증 사용) → `Login with a web browser`
→ 뜬 8자리 코드 복사 → 브라우저에서 authorize

### 1-5. 잠금 비밀번호 저장 (선택, 편의)

```powershell
[Environment]::SetEnvironmentVariable('HP_CATALOG_PW', 'hy0511!!', 'User')
```
이후 새 PowerShell 창부터 `--pw` 인자 생략 가능. 개인 노트북에만 저장(공용 X).

---

## 2. 매번 편집 절차

### 2-1. 최신 상태 pull

```powershell
cd C:\catalog\h-programs
git pull
```

### 2-2. 원하는 편집

- **카드 하나 추가** (URL 또는 파일에서):
  ```powershell
  python add_card.py --url "https://tesla.hyt.kr/o/397a2c29c488f053de2d/hesla-card.txt" --pw hy0511!!
  ```
  또는
  ```powershell
  python add_card.py --file some-card.html --pw hy0511!!
  ```

- **문구 치환**:
  ```powershell
  python catalog_edit.py replace "옛문구" "새문구" --pw hy0511!!
  ```

- **현재 내용 확인** (복호화):
  ```powershell
  python catalog_edit.py decrypt --pw hy0511!! | Out-File check.html -Encoding utf8
  # check.html 열어서 확인 후 반드시 삭제 (평문 흔적 남기지 말 것)
  Remove-Item check.html
  ```

- **특정 키워드 검색**:
  ```powershell
  python catalog_edit.py grep "Hesla" --pw hy0511!!
  ```

### 2-3. 커밋 · 푸시

```powershell
git add docs/index.html
git commit -m "Hesla 카드 추가"
git push
```

1-2분 후 hyt.kr/hp 반영 (GitHub Pages 자동 배포).

### 2-4. 배포 확인

```powershell
# 라이브 페이지 fetch (잠금 화면만 보임 — 정상)
Invoke-WebRequest https://hykkh.github.io/h-programs/ -UseBasicParsing | Select-Object -ExpandProperty Content | Select-String "const ENC"
```

브라우저에서 https://hyt.kr/hp 열고 `hy0511!!` 입력 → 추가한 카드 확인.

---

## 3. 절대 금지

1. **평문 index.html 커밋 금지** — `catalog_edit.py` / `add_card.py` 만 사용
2. **`.bak` 파일 커밋 금지** — 이미 `.gitignore` 처리됨
3. **비밀번호 코드에 하드코딩 금지** — `--pw` 인자나 환경변수
4. **비밀 다운로드 URL (`tesla.hyt.kr/o/…` 같은 것) 을 잠금 밖 (shell HTML) 에 두지 말 것**
   - 카드 안 (ENC 내부) 에만
   - shell HTML (평문) 은 잠금 화면만 있어야 함

---

## 4. 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `!! 복호화 실패` | `--pw` 틀림 | 비밀번호 확인 |
| `!! 옛 문구를 평문에서 못 찾음` | 문자열 오타 | `grep` 으로 정확 문자열 먼저 확인 |
| `git push` 거부 | 인증 만료 | `gh auth login` 재실행 |
| 라이브 반영 안 됨 (1-2분 후에도) | GitHub Pages 배포 지연/실패 | `gh run list --repo hykkh/h-programs --limit 3` 로 확인 |

---

## 5. Hesla 카드 추가 (지금 대기 중)

```powershell
cd C:\catalog\h-programs
git pull
python add_card.py --url "https://tesla.hyt.kr/o/397a2c29c488f053de2d/hesla-card.txt" --pw hy0511!!
git add docs/index.html
git commit -m "Hesla 카드 추가 (테슬라 화면 미러링 + 단속 카메라)"
git push
```

푸시 후 https://hyt.kr/hp 접속 → `hy0511!!` → Hesla 카드 확인 → 다운로드 버튼 클릭 → `hesla.apk` 59MB 받아지면 성공.
