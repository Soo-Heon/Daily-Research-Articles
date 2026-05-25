"""
HTML 메일 본문 렌더러.
"""
from __future__ import annotations

from datetime import datetime
from html import escape


def _badge_color(score: int) -> str:
    if score >= 9:
        return "#d32f2f"   # red
    if score >= 7:
        return "#f57c00"   # orange
    if score >= 6:
        return "#fbc02d"   # yellow
    return "#9e9e9e"


def _project_color(project: str) -> str:
    return {
        "MFDS": "#1565c0",
        "DGDB": "#2e7d32",
        "GDM": "#6a1b9a",
    }.get(project, "#616161")


def render_html(scored_articles: list[dict], threshold: int) -> str:
    """
    scored_articles: 각 항목은
      {
        "article": {...PubMed dict...},
        "score": {...Claude score dict...},
        "project": str,
        "subtopic": str,
      }
    """
    above = [s for s in scored_articles if s["score"].get("relevance_score", 0) >= threshold]
    # 점수 내림차순, 같은 점수면 저널명
    above.sort(key=lambda s: (-s["score"]["relevance_score"], s["article"]["journal"]))

    date_str = datetime.now().strftime("%Y-%m-%d")

    # 프로젝트별 그룹화
    by_project: dict[str, list[dict]] = {}
    for s in above:
        by_project.setdefault(s["project"], []).append(s)

    # ----- HTML 시작 -----
    style = """
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
             color:#222; line-height:1.55; max-width:760px; margin:0 auto; padding:20px; }
      h1 { font-size: 22px; border-bottom: 2px solid #333; padding-bottom: 8px; }
      h2 { font-size: 17px; margin-top: 28px; padding: 6px 10px; color: #fff; border-radius: 4px; }
      .meta { color:#666; font-size: 13px; margin-bottom: 16px; }
      .article { border-left: 4px solid #ddd; padding: 10px 14px; margin: 14px 0;
                 background: #fafafa; border-radius: 0 4px 4px 0; }
      .title { font-weight: 600; font-size: 15px; margin-bottom: 6px; }
      .title a { color: #0d47a1; text-decoration: none; }
      .title a:hover { text-decoration: underline; }
      .journal { color: #555; font-size: 13px; font-style: italic; }
      .badge { display:inline-block; color:#fff; padding: 2px 8px; border-radius: 10px;
               font-size: 12px; font-weight: 600; margin-right: 6px; }
      .summary { margin-top: 8px; font-size: 14px; }
      .keypoints { margin: 6px 0 0 0; padding-left: 20px; font-size: 13px; color:#444; }
      .reason { color:#777; font-size: 12px; margin-top: 6px; }
      .footer { color:#999; font-size: 12px; margin-top: 32px; border-top: 1px solid #eee; padding-top: 12px; }
    </style>
    """

    html = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        style,
        f"<title>Daily Research — {date_str}</title>",
        "</head><body>",
        f"<h1>📚 Daily Research Articles — {date_str}</h1>",
        f"<div class='meta'>임계값 {threshold}점 이상: <b>{len(above)}편</b> "
        f"(전체 평가: {len(scored_articles)}편)</div>",
    ]

    if not above:
        html.append(
            "<p style='color:#666;'>오늘은 임계값 이상의 관련 논문이 없습니다. "
            "전체 검색/평가 결과는 archive 폴더를 확인하세요.</p>"
        )
    else:
        for project, items in by_project.items():
            color = _project_color(project)
            html.append(
                f"<h2 style='background:{color};'>"
                f"{escape(project)} — {len(items)}편</h2>"
            )
            for s in items:
                html.append(_render_article(s))

    html.append(
        "<div class='footer'>이 메일은 GitHub Actions에서 자동 발송되었습니다. "
        "전체 결과 및 로그: archive/ 폴더 참조.</div>"
    )
    html.append("</body></html>")
    return "\n".join(html)


def _render_article(s: dict) -> str:
    art = s["article"]
    sc = s["score"]
    score = sc.get("relevance_score", 0)

    title = escape(art.get("title", "(제목 없음)"))
    journal = escape(art.get("journal_canonical") or art.get("journal", ""))
    url = escape(art.get("url", "#"))
    pub_date = escape(art.get("pub_date", ""))
    subtopic = escape(s.get("subtopic", ""))

    authors = art.get("authors", [])
    author_str = ", ".join(escape(a) for a in authors[:3])
    if len(authors) > 3:
        author_str += " 외"

    summary = escape(sc.get("summary_kr", ""))
    reason = escape(sc.get("reason", ""))
    key_points = sc.get("key_points", []) or []

    badge = f"<span class='badge' style='background:{_badge_color(score)};'>{score}/10</span>"
    sub_badge = f"<span class='badge' style='background:#455a64;'>{subtopic}</span>"

    kp_html = ""
    if key_points:
        kp_html = "<ul class='keypoints'>" + "".join(
            f"<li>{escape(str(p))}</li>" for p in key_points
        ) + "</ul>"

    return f"""
    <div class='article'>
      <div>{badge}{sub_badge}</div>
      <div class='title'><a href='{url}'>{title}</a></div>
      <div class='journal'>{journal} · {pub_date} · {author_str}</div>
      <div class='summary'>{summary}</div>
      {kp_html}
      <div class='reason'>판단 근거: {reason}</div>
    </div>
    """


def render_text_fallback(scored_articles: list[dict], threshold: int) -> str:
    """HTML 미지원 클라이언트용 plain text 본문."""
    above = [s for s in scored_articles if s["score"].get("relevance_score", 0) >= threshold]
    above.sort(key=lambda s: -s["score"]["relevance_score"])

    lines = [
        f"Daily Research Articles — {datetime.now().strftime('%Y-%m-%d')}",
        f"임계값 {threshold}점 이상: {len(above)}편 / 전체 평가 {len(scored_articles)}편",
        "=" * 60,
    ]
    if not above:
        lines.append("오늘은 임계값 이상의 관련 논문이 없습니다.")
    for i, s in enumerate(above, 1):
        art = s["article"]
        sc = s["score"]
        lines.extend([
            "",
            f"[{i}] [{sc['relevance_score']}/10] {art.get('title','')}",
            f"    저널: {art.get('journal','')} ({art.get('pub_date','')})",
            f"    URL : {art.get('url','')}",
            f"    요약: {sc.get('summary_kr','')}",
        ])
    return "\n".join(lines)
