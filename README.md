# Daily Research Articles

매일 PubMed에서 신규 논문을 자동 검색하고, Anthropic Claude로 한국어 요약 및 관련성 점수를 생성한 뒤, Gmail로 받아보는 자동화 도구. GitHub Actions에서 매일 정해진 시각에 실행됩니다.

연구실/연구자 본인의 관심 주제와 대상 저널에 맞춰 쉽게 customize할 수 있도록 설계되었습니다.

---

## 기능

- **자동 실행**: GitHub Actions cron으로 매일 정해진 시각에 (기본: 한국시간 오전 8시) 실행  
- **멀티 쿼리 검색**: 여러 개의 PubMed Boolean 쿼리를 한 번에 처리하여 다양한 주제를 한 번에 추적  
- **대상 저널 제한**: high-impact journal만 검색하도록 hard filter 적용 (PubMed `[ta]` 필드 활용, 27개 저널 기본 등록)  
- **AI 평가**: Claude Haiku로 0-10점 관련성 점수 \+ 3-5문장 한국어 요약 \+ 핵심 포인트 자동 생성  
- **선택 발송**: 임계값 이상 점수의 논문만 Gmail로 발송하여 메일 노이즈 최소화  
- **누적 저장**: 모든 평가 결과를 `archive/YYYY-MM-DD.json` 으로 저장. 메일 본문 HTML도 백업  
- **수동 실행 지원**: workflow\_dispatch로 즉시 실행, 검색 기간 조정, 이메일 발송 테스트 등 디버깅 모드 제공

---

## 동작 흐름

1\. PubMed 검색

   ├─ 사용자 정의 쿼리 × 검색 기간 × 대상 저널 필터

   └─ 중복 제거된 PMID 리스트 확보

2\. 논문 상세정보 가져오기

   └─ 제목, 저널, 초록, 저자, DOI, 발행일

3\. Claude로 점수 \+ 요약 (논문별)

   ├─ 0-10점 관련성 점수

   ├─ 한국어 요약 (3-5문장)

   └─ 핵심 포인트 \+ 점수 부여 근거

4\. archive 저장

   └─ JSON으로 전체 결과 (임계값 미만 포함) 누적

5\. 임계값 이상만 HTML 렌더링 → Gmail 발송

   └─ 프로젝트별로 그룹화, 점수 내림차순

---

## 셋업

### 필요한 것

- GitHub 계정 (Actions 사용)  
- Gmail 계정 (메일 발송용. 2단계 인증 필수)  
- Anthropic API 키 ([console.anthropic.com](https://console.anthropic.com))

### 1\. Repository 준비

이 repo를 fork하거나 clone한 뒤, 본인 GitHub repository에 push.

### 2\. Gmail App Password 발급

일반 Gmail 비밀번호로는 SMTP 인증이 불가능합니다. **App Password** (16자) 가 필요합니다.

1. [myaccount.google.com/security](https://myaccount.google.com/security) → 2단계 인증 ON  
2. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) → 새 App Password 생성  
3. 표시되는 16자 비밀번호를 메모 (창을 닫으면 다시 못 봄)

### 3\. GitHub Secrets 등록

Repo → Settings → Secrets and variables → Actions → **New repository secret** 로 다음 3개 등록:

| Secret 이름 | 값 |
| :---- | :---- |
| `ANTHROPIC_API_KEY` | Anthropic 콘솔에서 발급한 `sk-ant-...` |
| `GMAIL_USER` | 발송용 Gmail 주소 |
| `GMAIL_APP_PASSWORD` | 위에서 발급한 16자 App Password |

선택: `NCBI_API_KEY` 를 추가하면 PubMed API rate limit이 완화됩니다 ([발급 안내](https://www.ncbi.nlm.nih.gov/account/settings/)). 발송 주소와 수신 주소가 다르다면 Variables 탭에서 `EMAIL_TO` 추가.

### 4\. 워크플로우 활성화

Repo의 **Actions** 탭에서 "I understand my workflows, go ahead and enable them" 클릭. 다음 날 cron 시각에 자동 실행됩니다.

즉시 테스트하려면 **Run workflow** 버튼으로 수동 실행:

- `days_back`: 7 (최근 1주일치로 충분한 데이터 확보)  
- `test_email_only`: false

---

## 커스터마이즈

대부분의 설정은 `src/config.py` 한 파일에서 변경할 수 있습니다.

### 검색 쿼리 변경

`src/config.py` 의 `QUERIES` 리스트 수정. 형식:

QUERIES \= \[

    (

        "프로젝트명",         \# 예: "MFDS", "GDM"

        "서브토픽 설명",       \# 예: "Multi-omics × 만성질환"

        '\<PubMed Boolean 쿼리\>',  \# 예: '("multi-omics") AND ("diabetes")'

    ),

    ...

\]

쿼리에는 **저널 필터와 날짜 필터를 넣지 마세요** — 자동으로 결합됩니다.

쿼리 작성 도움말: [PubMed Advanced Search Builder](https://pubmed.ncbi.nlm.nih.gov/advanced/) 에서 테스트한 뒤 그대로 복사.

### 대상 저널 변경

`TARGET_JOURNALS` (표시용 이름) 와 `JOURNAL_NLM_ABBREVIATIONS` (PubMed 검색용 NLM 약어) 를 함께 수정해야 합니다.

JOURNAL\_NLM\_ABBREVIATIONS \= \[

    "Nature", "Science", "Cell",

    "Nat Genet", "Nat Med", ...

\]

NLM 약어는 [NLM Catalog](https://www.ncbi.nlm.nih.gov/nlmcatalog/journals) 에서 확인 가능. PubMed의 `[ta]` 필드와 매칭됩니다.

추가로 `_RAW_TO_CANONICAL` 매핑에 PubMed가 반환하는 다양한 저널명 변형 (`"Lancet (London, England)"`, `"The New England journal of medicine"` 등)을 등록해두면 매칭이 정확해집니다.

### 점수 임계값 조정

SCORE\_THRESHOLD \= 6   \# 이 점수 이상만 메일 발송. 0\~10 정수.

낮추면 메일이 더 많이 옴, 높이면 핵심 논문만.

### 검색 기간 변경

DAYS\_BACK \= 1   \# 1 \= 어제\~오늘, 7 \= 최근 1주일

매일 실행하면 1이 적절. 주간 다이제스트로 만들고 싶으면 7로 늘리고 cron도 weekly로 바꾸세요.

### 실행 시각 변경

`.github/workflows/daily.yml` 의 cron 표현식:

on:

  schedule:

    \- cron: '0 23 \* \* \*'   \# UTC 23:00 \= KST 익일 08:00

GitHub Actions는 UTC 기준입니다. KST \= UTC \+ 9\.

| 한국시간 | cron |
| :---- | :---- |
| 매일 08:00 | `0 23 * * *` |
| 매일 12:00 | `0 3 * * *` |
| 매일 18:00 | `0 9 * * *` |
| 매주 월요일 08:00 | `0 23 * * 0` |

### Claude 모델 변경

CLAUDE\_MODEL \= "claude-haiku-4-5-20251001"

비용보다 평가 품질을 중시한다면 상위 모델 (`claude-sonnet-4-6` 등) 로 변경 가능.

### 프롬프트 (평가 기준) 변경

`src/scorer.py` 의 `PROMPT_TEMPLATE` 수정. 본인 연구 주제 설명과 점수 기준을 포함합니다.

### 수신자 변경 / 다수 수신자

기본적으로 발송자(GMAIL\_USER) 본인이 수신자가 됩니다. 다른 사람에게 보내려면 repository Variables 탭에 `EMAIL_TO` 추가:

EMAIL\_TO \= colleague1@example.com, colleague2@example.com

쉼표로 구분된 여러 주소를 지원합니다.

### 1회 처리 논문 수 상한

Claude API 비용 폭주 방지용:

MAX\_RESULTS\_PER\_QUERY \= 50    \# 서브쿼리당 최대

MAX\_TOTAL\_ARTICLES \= 100      \# 전체 합계 상한

---

## 프로젝트 구조

.

├── .github/workflows/daily.yml   \# GitHub Actions 워크플로우

├── scripts/

│   ├── run\_daily.py              \# 메인 파이프라인 (PubMed → Claude → Email)

│   └── test\_email.py             \# SMTP 인증 단독 테스트

├── src/

│   ├── config.py                 \# 쿼리, 저널, 임계값 등 모든 설정

│   ├── pubmed.py                 \# PubMed E-utilities 클라이언트

│   ├── scorer.py                 \# Claude 점수/요약 생성

│   ├── emailer.py                \# Gmail SMTP 발송 (디버깅 친화)

│   └── renderer.py               \# HTML 메일 본문 렌더링

├── archive/                      \# 일별 결과 누적 저장 (자동 생성)

│   ├── YYYY-MM-DD.json           \# 전체 평가 결과

│   └── YYYY-MM-DD.email.html     \# 발송된 메일 본문 백업

├── requirements.txt

└── README.md

---

## 워크플로우 입력 (수동 실행)

**Run workflow** 버튼으로 수동 실행 시 다음 옵션을 조정할 수 있습니다.

| 입력 | 기본값 | 설명 |
| :---- | :---- | :---- |
| `days_back` | `1` | 며칠 전부터 검색할지 |
| `send_email` | `true` | 메일 발송 여부 |
| `test_email_only` | `false` | true면 PubMed 검색 건너뛰고 테스트 메일 1통만 발송 |

매일 cron 실행 시에는 모두 기본값으로 동작합니다.

---

## 메일 미리보기

발송되는 메일은 다음 정보를 포함합니다:

- 프로젝트별 그룹화 (색상으로 구분)  
- 점수 배지 (0-10점, 점수에 따라 색상 변화)  
- 논문 제목 (PubMed 링크 포함) \+ 저널 \+ 발행일 \+ 저자 (최대 3명)  
- 3-5문장 한국어 요약  
- 3개 핵심 포인트  
- Claude의 점수 부여 근거

발송 실패 시에도 `archive/YYYY-MM-DD.email.html` 에 본문이 저장되므로, 브라우저로 열어 동일한 내용을 확인할 수 있습니다.

---

## 비용

- **Claude Haiku**: 일 50-100편 평가 기준 약 $0.005\~0.02/일 → **월 $0.5 미만**  
- **GitHub Actions**: public repo는 완전 무료, private repo는 월 2000분 무료 (이 워크플로우는 1회 실행에 5분 이내)  
- **PubMed / Gmail SMTP**: 무료

---

## 라이선스

개인 사용 / 학술 연구 목적. fork 및 본인 환경에 맞춘 수정 환영.  
