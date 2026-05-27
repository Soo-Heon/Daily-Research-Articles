"""
PubMed E-utilities 클라이언트.

API 키 없이도 동작하지만, NCBI_API_KEY를 설정하면
초당 3 → 10 requests로 rate limit이 완화됩니다.
"""
from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

import requests

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# NCBI E-utilities는 익명 요청보다 tool/email 식별된 요청을 우대.
# 이 값은 식별용이며 실제로 메일이 가지 않음. 본인 정보로 바꿔도 됨.
TOOL_NAME = "daily-research-articles"
TOOL_EMAIL = os.getenv("NCBI_TOOL_EMAIL", "")  # GitHub Secret에서 주입


def _common_params(api_key: Optional[str] = None) -> dict:
    p = {"tool": TOOL_NAME}
    if TOOL_EMAIL:
        p["email"] = TOOL_EMAIL
    if api_key:
        p["api_key"] = api_key
    return p


def _date_range_filter(days_back: int) -> str:
    """PubMed의 EDAT(Entrez Date) 기반 날짜 필터 생성."""
    end = datetime.utcnow()
    start = end - timedelta(days=days_back)
    return (
        f'("{start.strftime("%Y/%m/%d")}"[EDAT] '
        f': "{end.strftime("%Y/%m/%d")}"[EDAT])'
    )


def search_pmids(
    query: str,
    days_back: int = 1,
    max_results: int = 50,
    api_key: Optional[str] = None,
    journal_filter: Optional[str] = None,
) -> list[str]:
    """
    쿼리에 해당하는 PMID 리스트 반환 (최근 N일).
    
    journal_filter: PubMed Boolean 구문 (예: '("Nature"[ta] OR "Science"[ta])').
                    지정 시 모든 쿼리에 AND로 결합되어 대상 저널만 검색.
    """
    parts = [f"({query})", _date_range_filter(days_back)]
    if journal_filter:
        parts.append(journal_filter)
    full_query = " AND ".join(parts)

    params = {
        **_common_params(api_key),
        "db": "pubmed",
        "term": full_query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "date",
    }

    r = requests.get(f"{NCBI_BASE}/esearch.fcgi", params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])


def fetch_articles(
    pmids: list[str],
    api_key: Optional[str] = None,
    batch_size: int = 100,
) -> list[dict]:
    """PMID 리스트로부터 논문 상세정보(title/abstract/journal 등) 가져오기."""
    if not pmids:
        return []

    articles = []
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i : i + batch_size]
        params = {
            **_common_params(api_key),
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
        }

        r = requests.get(f"{NCBI_BASE}/efetch.fcgi", params=params, timeout=60)
        r.raise_for_status()
        articles.extend(_parse_xml(r.text))

        # rate limit 보호
        time.sleep(0.4 if not api_key else 0.15)

    return articles


def _parse_xml(xml_text: str) -> list[dict]:
    """PubMed EFetch XML 응답을 dict 리스트로 변환."""
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  [WARN] XML 파싱 실패: {e}")
        return out

    for art in root.findall(".//PubmedArticle"):
        try:
            pmid = art.findtext(".//PMID", "") or ""

            # Title (italic 등 inline 요소 처리 위해 itertext)
            title_elem = art.find(".//ArticleTitle")
            title = "".join(title_elem.itertext()).strip() if title_elem is not None else ""

            # Abstract: 라벨이 있는 구조화 초록 처리
            parts = []
            for ab in art.findall(".//Abstract/AbstractText"):
                label = ab.get("Label")
                text = "".join(ab.itertext()).strip()
                parts.append(f"{label}: {text}" if label else text)
            abstract = " ".join(parts).strip()

            journal = art.findtext(".//Journal/Title", "") or ""

            # 저자 (최대 6명만)
            authors = []
            for a in art.findall(".//Author")[:6]:
                last = a.findtext("LastName", "") or ""
                first = a.findtext("ForeName", "") or ""
                if last:
                    authors.append(f"{first} {last}".strip())

            # 발행일
            pd = art.find(".//PubDate")
            if pd is not None:
                y = pd.findtext("Year", "") or ""
                m = pd.findtext("Month", "") or ""
                d = pd.findtext("Day", "") or ""
                pub_date = "-".join(x for x in [y, m, d] if x)
            else:
                pub_date = ""

            # DOI
            doi = ""
            for idel in art.findall(".//ArticleId"):
                if idel.get("IdType") == "doi":
                    doi = idel.text or ""
                    break

            out.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "authors": authors,
                "pub_date": pub_date,
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
        except Exception as e:
            print(f"  [WARN] 논문 파싱 오류: {e}")
            continue

    return out
