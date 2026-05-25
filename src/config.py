"""
설정: PubMed 쿼리, 대상 저널 (하드 필터), 점수 임계값.

대상 저널 외 논문은 PubMed 검색 단계에서 제외됩니다.
"""
from __future__ import annotations

import re

# 점수 임계값 (0-10). 이 점수 이상의 논문만 메일로 발송.
SCORE_THRESHOLD = 6

# 며칠 전부터 검색할지 (1 = 어제 ~ 오늘)
DAYS_BACK = 1

# 각 서브쿼리당 최대 검색 결과 수
MAX_RESULTS_PER_QUERY = 50

# 전체 처리할 최대 논문 수 (Claude API 비용 방지)
MAX_TOTAL_ARTICLES = 100

# Claude 모델
CLAUDE_MODEL = "claude-haiku-4-5-20251001"


# =================================================================
# 대상 저널 (이 27개만 검색)
# =================================================================
TARGET_JOURNALS = [
    "Nature", "Science", "Cell",
    "Nature Genetics", "Nature Medicine", "Nature Communications",
    "Nature Biotechnology", "Nature Methods", "Nature Metabolism",
    "Nature Reviews Genetics", "Nature Reviews Endocrinology",
    "Nature Reviews Drug Discovery",
    "Cell Metabolism", "Cell Reports Medicine",
    "Lancet", "Lancet Diabetes Endocrinology", "Lancet Digital Health",
    "Diabetes Care", "Diabetologia", "Diabetes",
    "JAMA", "JAMA Internal Medicine", "JAMA Network Open",
    "New England Journal of Medicine", "NEJM",
    "npj Digital Medicine", "npj Genomic Medicine",
    "Science Translational Medicine",
    "BMJ", "Annals of Internal Medicine",
]

# PubMed [ta] (NLM Title Abbreviation) 필터용.
# PubMed의 [Journal] 필드는 풀네임/약어/ISO 약어를 모두 인덱싱하므로
# 약어를 쓰면 가장 정확하게 매칭됩니다.
JOURNAL_NLM_ABBREVIATIONS = [
    "Nature",
    "Science",
    "Cell",
    "Nat Genet",
    "Nat Med",
    "Nat Commun",
    "Nat Biotechnol",
    "Nat Methods",
    "Nat Metab",
    "Nat Rev Genet",
    "Nat Rev Endocrinol",
    "Nat Rev Drug Discov",
    "Cell Metab",
    "Cell Rep Med",
    "Lancet",
    "Lancet Diabetes Endocrinol",
    "Lancet Digit Health",
    "Diabetes Care",
    "Diabetologia",
    "Diabetes",
    "JAMA",
    "JAMA Intern Med",
    "JAMA Netw Open",
    "N Engl J Med",
    "NPJ Digit Med",
    "NPJ Genom Med",
    "Sci Transl Med",
    "BMJ",
    "Ann Intern Med",
]

# PubMed AND 절에 끼워넣을 저널 필터
JOURNAL_FILTER_QUERY = "(" + " OR ".join(
    f'"{a}"[ta]' for a in JOURNAL_NLM_ABBREVIATIONS
) + ")"


# =================================================================
# 저널 이름 정규화 + 매칭 (PubMed 표기 흔들림 대응)
# =================================================================
# PubMed가 반환하는 저널명에 들어있는 noise를 제거:
#   "Lancet (London, England)"           → "lancet"
#   "The New England journal of medicine" → "new england journal of medicine"
#   "Science (New York, N.Y.)"           → "science"
#   "BMJ (Clinical research ed.)"        → "bmj"
def normalize_journal(name: str) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"\s*\([^)]*\)", "", s)   # 괄호 제거
    s = re.sub(r"^the\s+", "", s)         # 앞쪽 "the "
    s = s.replace("&", "and")             # "&" → "and"
    s = re.sub(r"[.,:;]", " ", s)         # 구두점 → 공백
    s = re.sub(r"\s+", " ", s).strip()    # 다중 공백
    return s


# (raw 이름) → (canonical 표시 이름) 매핑.
# 풀네임/NLM약어 모두 등록해 양방향 매칭.
_RAW_TO_CANONICAL = {
    # 풀네임
    "Nature": "Nature",
    "Science": "Science",
    "Cell": "Cell",
    "Nature Genetics": "Nature Genetics",
    "Nature Medicine": "Nature Medicine",
    "Nature Communications": "Nature Communications",
    "Nature Biotechnology": "Nature Biotechnology",
    "Nature Methods": "Nature Methods",
    "Nature Metabolism": "Nature Metabolism",
    "Cell Metabolism": "Cell Metabolism",
    "Cell Reports Medicine": "Cell Reports Medicine",
    "Cell Reports. Medicine": "Cell Reports Medicine",
    "Lancet": "Lancet",
    "The Lancet": "Lancet",
    "Lancet Diabetes Endocrinology": "Lancet Diabetes Endocrinology",
    "The Lancet Diabetes & Endocrinology": "Lancet Diabetes Endocrinology",
    "The Lancet. Diabetes & Endocrinology": "Lancet Diabetes Endocrinology",
    "Lancet Digital Health": "Lancet Digital Health",
    "The Lancet Digital Health": "Lancet Digital Health",
    "The Lancet. Digital Health": "Lancet Digital Health",
    "Diabetes Care": "Diabetes Care",
    "Diabetologia": "Diabetologia",
    "Diabetes": "Diabetes",
    "JAMA": "JAMA",
    "JAMA Internal Medicine": "JAMA Internal Medicine",
    "JAMA Network Open": "JAMA Network Open",
    "New England Journal of Medicine": "New England Journal of Medicine",
    "The New England Journal of Medicine": "New England Journal of Medicine",
    "npj Digital Medicine": "npj Digital Medicine",
    "npj Genomic Medicine": "npj Genomic Medicine",
    "Science Translational Medicine": "Science Translational Medicine",
    "BMJ": "BMJ",
    "BMJ (Clinical research ed.)": "BMJ",
    "Annals of Internal Medicine": "Annals of Internal Medicine",
    # NLM 약어
    "Nat Genet": "Nature Genetics",
    "Nat Med": "Nature Medicine",
    "Nat Commun": "Nature Communications",
    "Nat Biotechnol": "Nature Biotechnology",
    "Nat Methods": "Nature Methods",
    "Nat Metab": "Nature Metabolism",
    "Cell Metab": "Cell Metabolism",
    "Cell Rep Med": "Cell Reports Medicine",
    "Lancet Diabetes Endocrinol": "Lancet Diabetes Endocrinology",
    "Lancet Digit Health": "Lancet Digital Health",
    "JAMA Intern Med": "JAMA Internal Medicine",
    "JAMA Netw Open": "JAMA Network Open",
    "N Engl J Med": "New England Journal of Medicine",
    "NPJ Digit Med": "npj Digital Medicine",
    "NPJ Genom Med": "npj Genomic Medicine",
    "Sci Transl Med": "Science Translational Medicine",
    "Ann Intern Med": "Annals of Internal Medicine",
}

# 정규화 후 키 → canonical (모듈 로드시 1회)
_NORMALIZED_TARGETS: dict[str, str] = {
    normalize_journal(k): v for k, v in _RAW_TO_CANONICAL.items()
}


def match_target_journal(journal_name: str) -> str | None:
    """
    PubMed가 반환한 저널명이 대상 목록에 있는지 확인.
    있으면 표시용 canonical 이름, 없으면 None.
    """
    norm = normalize_journal(journal_name)
    return _NORMALIZED_TARGETS.get(norm)


# =================================================================
# 검색 쿼리
# =================================================================
QUERIES = [
    # ----- 1. 식약처(MFDS) 과제 -----
    (
        "MFDS",
        "Multi-omics × 만성질환",
        '("multi-omics" OR "multiomics" OR "omics integration") '
        'AND ("diabetes" OR "cardiovascular" OR "NAFLD" OR "MASLD" OR "stroke" OR "chronic kidney disease")',
    ),
    (
        "MFDS",
        "AI × 약물반응 × 대사질환",
        '("machine learning" OR "deep learning" OR "artificial intelligence") '
        'AND ("adverse drug reaction" OR "drug response" OR "pharmacogenomics" OR "drug efficacy") '
        'AND ("metabolic" OR "diabetes" OR "cardiovascular")',
    ),
    (
        "MFDS",
        "오믹스 × 약물반응",
        '("proteomics" OR "metabolomics" OR "genomics" OR "transcriptomics") '
        'AND ("pharmacogenomics" OR "drug-induced" OR "treatment response" OR "adverse drug")',
    ),
    (
        "MFDS",
        "코호트/바이오뱅크 × 다중오믹스 × AI",
        '("cohort" OR "biobank") '
        'AND ("multi-omics" OR "multiomics") '
        'AND ("machine learning" OR "deep learning" OR "artificial intelligence")',
    ),
    (
        "MFDS",
        "EHR/RWD × 오믹스 × 정밀의료",
        '("electronic health record" OR "real-world data" OR "multimodal") '
        'AND ("omics" OR "genomics" OR "proteomics" OR "metabolomics") '
        'AND ("prediction" OR "biomarker" OR "precision medicine")',
    ),

    # ----- 2. 데기디바 과제 -----
    (
        "DGDB",
        "T2D × Foundation/LLM/Federated",
        '("type 2 diabetes" OR "diabetic complication*") '
        'AND ("foundation model" OR "large language model" OR "self-supervised" OR "federated learning") '
        'AND ("prediction" OR "diagnosis" OR "prognosis")',
    ),

    # ----- 3. 질병관리청 GDM 과제 -----
    (
        "GDM",
        "GDM → T2D 전환",
        '("gestational diabetes" OR "GDM") '
        'AND ("type 2 diabetes" OR "T2DM" OR "progression" OR "postpartum") '
        'AND ("risk" OR "prediction" OR "cohort" OR "longitudinal")',
    ),
    (
        "GDM",
        "GDM × CGM",
        '("gestational diabetes" OR "GDM") '
        'AND ("continuous glucose monitoring" OR "CGM" OR "time in range" OR "glycemic variability")',
    ),
    (
        "GDM",
        "GDM × Genetics/GWAS",
        '("gestational diabetes" OR "GDM") '
        'AND ("GWAS" OR "genome-wide" OR "polygenic" OR "genetic variant" OR "SNP" OR "heritability")',
    ),
    (
        "GDM",
        "GDM × Microbiome",
        '("gestational diabetes" OR "GDM") '
        'AND ("microbiome" OR "microbiota" OR "gut bacteria" OR "16S")',
    ),
]
