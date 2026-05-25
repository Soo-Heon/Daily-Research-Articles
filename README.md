# Daily Research Articles

매일 PubMed에서 신규 논문을 검색하여 Claude로 한국어 요약 및 관련성 점수를 생성하고, Gmail로 발송하는 자동화 시스템.

## 기능

- 매일 한국시간 오전 8시 자동 실행 (GitHub Actions)
- PubMed Boolean 쿼리 10개 (식약처 5 + 데기디바 1 + GDM 4)
- Claude Haiku로 0-10점 관련성 점수 + 한국어 요약
- 임계값(기본 6점) 이상만 Gmail 발송
- archive/ 폴더에 매일 결과 누적 저장 (JSON + HTML 백업)
- 수동 실행 / 이메일만 테스트 등 디버깅 모드 지원

## 디렉터리 구조

```
.
├── .github/workflows/daily.yml   # GitHub Actions
├── scripts/
│   ├── run_daily.py              # 메인 워크플로우
│   └── test_email.py             # 이메일 단독 테스트
├── src/
│   ├── config.py                 # 쿼리, 임계값, 저널 목록
│   ├── pubmed.py                 # PubMed E-utilities
│   ├── scorer.py                 # Claude 점수/요약
│   ├── emailer.py                # Gmail SMTP (디버깅 강화)
│   └── renderer.py               # HTML 본문
├── archive/                      # 일별 결과 (자동 생성)
├── requirements.txt
└── README.md
```

## 셋업 절차 (단계별)

### 1단계: Gmail App Password 발급 ⚠️ 가장 중요

1. https://myaccount.google.com/security 접속
2. **2단계 인증**을 켭니다 (필수)
3. https://myaccount.google.com/apppasswords 접속
4. 앱 이름 입력 (예: `daily-research`) → **생성**
5. 16자 비밀번호가 나타남 (예: `abcd efgh ijkl mnop`)
6. **공백을 제거**한 16자 (`abcdefghijklmnop`) 를 메모 — 이 화면을 닫으면 다시 못 봅니다.

> 일반 Google 계정 비밀번호로는 절대 안 됩니다.
> 코드가 자동으로 공백을 제거하지만, 발급 직후 표시되는 16자를 정확히 복사하세요.

### 2단계: Anthropic API Key 발급

1. https://console.anthropic.com/ → API Keys → Create Key
2. `sk-ant-...` 형식의 키 복사

### 3단계: GitHub Secrets 등록

저장소 → Settings → Secrets and variables → Actions → **New repository secret**

| Secret 이름 | 값 |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `GMAIL_USER` | `yourid@mail.net` |
| `GMAIL_APP_PASSWORD` | 16자 App Password (공백 제거) |
| `NCBI_API_KEY` | (선택) NCBI API 키 — rate limit 완화용 |

수신자가 발송자와 다르면 Variables 탭에 `EMAIL_TO`도 추가하세요 (선택).

### 4단계: 파일 업로드

이 폴더의 모든 파일을 repo에 push:

```bash
git clone https://github.com/Soo-Heon/Daily-Research-Articles.git
cd Daily-Research-Articles

# 이 프로젝트 파일들을 복사한 뒤
git add .
git commit -m "feat: rebuild daily research pipeline"
git push origin main
```

### 5단계: 이메일 단독 테스트 (필수)

GitHub repo → **Actions** 탭 → "Daily Research Articles" → **Run workflow** 클릭

옵션:
- `test_email_only`: **true** ← 일단 메일만 테스트
- 나머지는 기본값

실행 후 Actions 로그를 봅니다.

#### 로그에서 확인할 것

```
[Email] user=k***h@gmail.com password_len=16 host=smtp.gmail.com:465 ssl=True
[Email Test] smtp.gmail.com:465 연결 시도...
[Email Test] 인증 시도...
[Email Test] ✅ 인증 성공
```

이렇게 나오면 OK. 받은편지함을 확인하세요 — `[TEST] Daily Research Articles 발송 테스트` 메일이 와 있어야 합니다.

#### 실패 시 진단

| 로그 메시지 | 원인 | 해결 |
|---|---|---|
| `password_len` 가 16이 아님 | App Password가 아니거나 잘못 복사 | 재발급 |
| `SMTPAuthenticationError: 535` | App Password 오류 또는 2FA 미설정 | 1단계 재시도 |
| `SMTPServerDisconnected` | 포트 차단 | port 587 + STARTTLS로 변경 (아래) |
| `socket.timeout` | 네트워크 일시적 문제 | 재실행 |

`smtp.gmail.com:465` 가 안 되면 `src/emailer.py` 의 기본값을 변경:

```python
EmailSender(user=..., password=..., port=587, use_ssl=False)
```

### 6단계: 메인 워크플로우 테스트

이메일 테스트가 성공했다면, 이번에는:
- **Run workflow** → `test_email_only`: **false** (또는 빈칸)
- `days_back`: `7` (최근 1주일치로 데이터를 충분히)

전체 파이프라인이 돌고 메일이 옵니다.

### 7단계: 스케줄 활성화

`cron: '0 23 * * *'` 가 이미 워크플로우에 들어 있으므로 추가 작업 없음.
다음 날 한국시간 오전 8시(UTC 23:00)에 자동 실행됩니다.

## 디버깅 가이드

### "Archive는 되는데 메일이 안 와요"

```
Actions 탭 → 해당 run → 'Run daily research' step 로그 펼치기
→ "[5/5] Gmail 발송" 부터 끝까지 확인
```

`set_debuglevel(1)` 때문에 SMTP 송수신 전체가 로그에 찍힙니다.
정상이면 `250 2.0.0 OK ...` 응답이 보입니다.

### 받은편지함에 안 왔다면

1. **스팸함 / 모든메일** 확인
2. Gmail에서 `from:yourid@mail.net` 으로 검색 — 자기 자신에게 보낸 메일은 "Sent" 분류로 가서 INBOX에서 안 보일 수 있음
3. archive/ 폴더의 `YYYY-MM-DD.email.html` 파일을 브라우저로 열면 발송된 내용 그대로 확인 가능

### 점수 임계값 조정

`src/config.py` 의 `SCORE_THRESHOLD = 6` 변경.

### 쿼리 추가/수정

`src/config.py` 의 `QUERIES` 리스트에 `("프로젝트", "서브토픽", "PubMed 쿼리")` 형태로 추가.

## 비용 견적

- Claude Haiku: 약 $0.005~0.02/일 (일 50-100편 평가 기준)
- 월 약 $0.5 미만
- GitHub Actions: public repo 무료, private repo는 월 2000분 무료

## 라이선스

개인 사용
