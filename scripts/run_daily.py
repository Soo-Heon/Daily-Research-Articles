#!/usr/bin/env python3
"""
메인 워크플로우: PubMed 검색 → Claude 점수 → archive 저장 → Gmail 발송.

환경변수:
  ANTHROPIC_API_KEY    (필수)
  GMAIL_USER           (필수, 이메일 발송 시)
  GMAIL_APP_PASSWORD   (필수, 이메일 발송 시)
  EMAIL_TO             (선택, 기본은 GMAIL_USER)
  NCBI_API_KEY         (선택, PubMed rate limit 완화)
  DAYS_BACK            (선택, 기본 1)
  SEND_EMAIL           (선택, 'true'/'false', 기본 true)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 부모 디렉터리 import 경로
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config, pubmed
from src.scorer import Scorer
from src.emailer import EmailSender
from src.renderer import render_html, render_text_fallback


# -------------------------- 환경변수 -------------------------- #
def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def env_bool(name: str, default: bool) -> bool:
    v = env(name, "").lower()
    if v in ("1", "true", "yes", "y"):
        return True
    if v in ("0", "false", "no", "n"):
        return False
    return default


def env_int(name: str, default: int) -> int:
    try:
        return int(env(name, str(default)))
    except ValueError:
        return default


# -------------------------- 메인 -------------------------- #
def main() -> int:
    print("=" * 70)
    print(f"Daily Research Articles — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    anthropic_key = env("ANTHROPIC_API_KEY")
    gmail_user = env("GMAIL_USER")
    gmail_password = env("GMAIL_APP_PASSWORD")
    email_to = env("EMAIL_TO", gmail_user)
    ncbi_key = env("NCBI_API_KEY") or None
    days_back = env_int("DAYS_BACK", config.DAYS_BACK)
    send_email = env_bool("SEND_EMAIL", True)

    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY 가 설정되지 않았습니다.")
        return 1

    # -------------------- 1) PubMed 검색 -------------------- #
    print(f"\n[1/4] PubMed 검색 (최근 {days_back}일, 대상 저널 {len(config.TARGET_JOURNALS)}개로 제한)")
    seen_pmids: set[str] = set()
    pmid_to_context: dict[str, tuple[str, str]] = {}  # pmid -> (project, subtopic)

    for project, subtopic, query in config.QUERIES:
        print(f"  • [{project}] {subtopic} ...", end=" ", flush=True)
        try:
            pmids = pubmed.search_pmids(
                query=query,
                days_back=days_back,
                max_results=config.MAX_RESULTS_PER_QUERY,
                api_key=ncbi_key,
                journal_filter=config.JOURNAL_FILTER_QUERY,
            )
        except Exception as e:
            print(f"❌ {e}")
            continue

        new_pmids = [p for p in pmids if p not in seen_pmids]
        for p in new_pmids:
            seen_pmids.add(p)
            # 같은 논문이 여러 쿼리에 잡혀도 첫 번째 쿼리의 컨텍스트만 기록
            pmid_to_context.setdefault(p, (project, subtopic))
        print(f"hit={len(pmids)} new={len(new_pmids)}")

    print(f"  → 고유 PMID 합계: {len(seen_pmids)}편")

    if len(seen_pmids) > config.MAX_TOTAL_ARTICLES:
        print(f"  ⚠️ 총 {len(seen_pmids)}편이지만 비용 절감 위해 {config.MAX_TOTAL_ARTICLES}편으로 제한")
        seen_pmids = set(list(seen_pmids)[: config.MAX_TOTAL_ARTICLES])

    # -------------------- 2) 상세정보 fetch -------------------- #
    print(f"\n[2/4] 논문 상세정보 가져오기 ({len(seen_pmids)}편)")
    articles_raw = pubmed.fetch_articles(list(seen_pmids), api_key=ncbi_key)
    print(f"  → 가져옴: {len(articles_raw)}편")

    # 안전장치: PubMed 검색 필터가 통과시켰어도 다시 한 번 저널명 매칭 확인.
    # canonical 이름을 부여하여 표시도 깔끔하게.
    articles = []
    rejected_journals = []
    for art in articles_raw:
        canonical = config.match_target_journal(art["journal"])
        if canonical is None:
            rejected_journals.append(art["journal"])
            continue
        art["journal_canonical"] = canonical
        articles.append(art)

    if rejected_journals:
        print(f"  ⚠️ 대상 저널 외 {len(rejected_journals)}편 제외:")
        for j in set(rejected_journals):
            print(f"     - {j!r}")
    print(f"  → 최종 대상 저널 논문: {len(articles)}편")

    # -------------------- 3) Claude 점수 + 요약 -------------------- #
    print(f"\n[3/4] Claude {config.CLAUDE_MODEL}로 점수/요약 ({len(articles)}편)")
    scorer = Scorer(api_key=anthropic_key, model=config.CLAUDE_MODEL)

    scored: list[dict] = []
    for i, art in enumerate(articles, 1):
        project, subtopic = pmid_to_context.get(art["pmid"], ("?", "?"))
        print(f"  [{i}/{len(articles)}] [{art['journal_canonical']}] PMID {art['pmid']} - {art['title'][:50]}...")
        score = scorer.score(art, project=project, subtopic=subtopic)
        if not score:
            continue

        scored.append({
            "article": art,
            "score": score,
            "project": project,
            "subtopic": subtopic,
        })

    above = [s for s in scored if s["score"].get("relevance_score", 0) >= config.SCORE_THRESHOLD]
    print(f"  → 평가 완료: {len(scored)}편, 임계값({config.SCORE_THRESHOLD}) 이상: {len(above)}편")

    # -------------------- 4) Archive 저장 -------------------- #
    today = datetime.now().strftime("%Y-%m-%d")
    archive_dir = ROOT / "archive"
    archive_dir.mkdir(exist_ok=True)
    archive_path = archive_dir / f"{today}.json"

    payload = {
        "date": today,
        "days_back": days_back,
        "threshold": config.SCORE_THRESHOLD,
        "queries_run": len(config.QUERIES),
        "articles_found": len(articles),
        "articles_scored": len(scored),
        "articles_above_threshold": len(above),
        "results": scored,
    }
    archive_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[4/4] Archive 저장: {archive_path}")

    # -------------------- 5) 이메일 발송 -------------------- #
    if not send_email:
        print("\nSEND_EMAIL=false → 메일 발송 건너뜀")
        return 0

    if not gmail_user or not gmail_password:
        print("\n❌ GMAIL_USER 또는 GMAIL_APP_PASSWORD 미설정 → 메일 발송 불가")
        return 1

    print(f"\n[5/5] Gmail 발송 → {email_to}")

    # HTML 본문 백업 저장 (메일 실패해도 결과는 남김)
    html_body = render_html(scored, threshold=config.SCORE_THRESHOLD)
    text_body = render_text_fallback(scored, threshold=config.SCORE_THRESHOLD)
    backup_html = archive_dir / f"{today}.email.html"
    backup_html.write_text(html_body, encoding="utf-8")
    print(f"  HTML 백업: {backup_html}")

    sender = EmailSender(user=gmail_user, password=gmail_password)

    subject = f"📚 Daily Research — {today} ({len(above)}편 / {len(scored)}편 평가)"
    ok = sender.send(
        to=email_to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    if not ok:
        print("\n❌ 메일 발송 실패. 위의 진단 메시지를 확인하세요.")
        return 1

    print("\n✅ 모든 작업 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
