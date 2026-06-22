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
# 대상 저널 (이 43개만 검색)
# - 종합 의학/기초 top: Nature, Science, NEJM, Lancet, JAMA, BMJ 등
# - 당뇨/대사: Diabetes, Diabetes Care, Diabetologia, Lancet Diab Endo,
#              Nature Metabolism, Cell Metabolism
# - 심혈관: Circulation, Eur Heart J, JACC, Circulation Research
# - 신장: Kidney International, JASN, CJASN
# - 뇌졸중: Stroke
# - 간/위장관: Hepatology, J Hepatol, Gastroenterology, Gut
# - 오믹스/중개의학: Genome Biology, Genome Medicine, Mol Syst Biol,
#                    Cell Systems, EBioMedicine, Cell Reports Medicine
# - AI/디지털: Lancet Digital Health, npj Digital Medicine
# - 유전체: Nature Genetics, npj Genomic Medicine
# =================================================================
TARGET_JOURNALS = [
    # 종합 의학·기초
    "Nature", "Science", "Cell",
    "New England Journal of Medicine",
    "Lancet", "JAMA", "BMJ",
    "Annals of Internal Medicine",
    "JAMA Internal Medicine", "JAMA Network Open",
    "Science Translational Medicine",
    # 기초 (Nature/Cell 자매지)
    "Nature Medicine", "Nature Genetics", "Nature Communications",
    "Nature Biotechnology", "Nature Methods", "Nature Metabolism",
    "Cell Metabolism", "Cell Reports Medicine",
    # 당뇨/내분비
    "Lancet Diabetes Endocrinology", "Diabetes Care", "Diabetologia", "Diabetes",
    # 심혈관
    "Circulation", "European Heart Journal",
    "Journal of the American College of Cardiology", "Circulation Research",
    # 신장
    "Kidney International",
    "Journal of the American Society of Nephrology",
    "Clinical Journal of the American Society of Nephrology",
    # 뇌졸중
    "Stroke",
    # 간/위장관
    "Hepatology", "Journal of Hepatology", "Gastroenterology", "Gut",
    # 오믹스/중개의학
    "EBioMedicine",
    "Genome Biology", "Genome Medicine",
    "Molecular Systems Biology", "Cell Systems",
    # 디지털 헬스
    "Lancet Digital Health", "npj Digital Medicine", "npj Genomic Medicine",
]

# PubMed [ta] (NLM Title Abbreviation) 필터용.
# 약어가 가장 정확하게 매칭됩니다.
JOURNAL_NLM_ABBREVIATIONS = [
    # 종합 의학·기초
    "Nature", "Science", "Cell",
    "N Engl J Med",
    "Lancet", "JAMA", "BMJ",
    "Ann Intern Med",
    "JAMA Intern Med", "JAMA Netw Open",
    "Sci Transl Med",
    # 기초 자매지
    "Nat Med", "Nat Genet", "Nat Commun",
    "Nat Biotechnol", "Nat Methods", "Nat Metab",
    "Cell Metab", "Cell Rep Med",
    # 당뇨/내분비
    "Lancet Diabetes Endocrinol", "Diabetes Care", "Diabetologia", "Diabetes",
    # 심혈관
    "Circulation", "Eur Heart J",
    "J Am Coll Cardiol", "Circ Res",
    # 신장
    "Kidney Int",
    "J Am Soc Nephrol",
    "Clin J Am Soc Nephrol",
    # 뇌졸중
    "Stroke",
    # 간/위장관
    "Hepatology", "J Hepatol", "Gastroenterology", "Gut",
    # 오믹스/중개의학
    "EBioMedicine",
    "Genome Biol", "Genome Med",
    "Mol Syst Biol", "Cell Syst",
    # 디지털
    "Lancet Digit Health", "NPJ Digit Med", "NPJ Genom Med",
]

# PubMed AND 절에 끼워넣을 저널 필터
JOURNAL_FILTER_QUERY = "(" + " OR ".join(
    f'"{a}"[ta]' for a in JOURNAL_NLM_ABBREVIATIONS
) + ")"


# =================================================================
# 저널 이름 정규화 + 매칭 (PubMed 표기 흔들림 대응)
# =================================================================
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


_RAW_TO_CANONICAL = {
    # ---- 종합 의학·기초 ----
    "Nature": "Nature",
    "Science": "Science",
    "Cell": "Cell",
    "New England Journal of Medicine": "New England Journal of Medicine",
    "The New England Journal of Medicine": "New England Journal of Medicine",
    "N Engl J Med": "New England Journal of Medicine",
    "Lancet": "Lancet",
    "The Lancet": "Lancet",
    "JAMA": "JAMA",
    "BMJ": "BMJ",
    "BMJ (Clinical research ed.)": "BMJ",
    "Annals of Internal Medicine": "Annals of Internal Medicine",
    "Ann Intern Med": "Annals of Internal Medicine",
    "JAMA Internal Medicine": "JAMA Internal Medicine",
    "JAMA Intern Med": "JAMA Internal Medicine",
    "JAMA Network Open": "JAMA Network Open",
    "JAMA Netw Open": "JAMA Network Open",
    "Science Translational Medicine": "Science Translational Medicine",
    "Sci Transl Med": "Science Translational Medicine",
    # ---- Nature/Cell 자매지 ----
    "Nature Medicine": "Nature Medicine",
    "Nat Med": "Nature Medicine",
    "Nature Genetics": "Nature Genetics",
    "Nat Genet": "Nature Genetics",
    "Nature Communications": "Nature Communications",
    "Nat Commun": "Nature Communications",
    "Nature Biotechnology": "Nature Biotechnology",
    "Nat Biotechnol": "Nature Biotechnology",
    "Nature Methods": "Nature Methods",
    "Nat Methods": "Nature Methods",
    "Nature Metabolism": "Nature Metabolism",
    "Nat Metab": "Nature Metabolism",
    "Cell Metabolism": "Cell Metabolism",
    "Cell Metab": "Cell Metabolism",
    "Cell Reports Medicine": "Cell Reports Medicine",
    "Cell Reports. Medicine": "Cell Reports Medicine",
    "Cell Rep Med": "Cell Reports Medicine",
    # ---- 당뇨/내분비 ----
    "Lancet Diabetes Endocrinology": "Lancet Diabetes Endocrinology",
    "The Lancet Diabetes & Endocrinology": "Lancet Diabetes Endocrinology",
    "The Lancet. Diabetes & Endocrinology": "Lancet Diabetes Endocrinology",
    "Lancet Diabetes Endocrinol": "Lancet Diabetes Endocrinology",
    "Diabetes Care": "Diabetes Care",
    "Diabetologia": "Diabetologia",
    "Diabetes": "Diabetes",
    # ---- 심혈관 ----
    "Circulation": "Circulation",
    "European Heart Journal": "European Heart Journal",
    "Eur Heart J": "European Heart Journal",
    "Journal of the American College of Cardiology": "Journal of the American College of Cardiology",
    "J Am Coll Cardiol": "Journal of the American College of Cardiology",
    "Circulation Research": "Circulation Research",
    "Circ Res": "Circulation Research",
    # ---- 신장 ----
    "Kidney International": "Kidney International",
    "Kidney Int": "Kidney International",
    "Journal of the American Society of Nephrology": "Journal of the American Society of Nephrology",
    "Journal of the American Society of Nephrology : JASN": "Journal of the American Society of Nephrology",
    "J Am Soc Nephrol": "Journal of the American Society of Nephrology",
    "Clinical Journal of the American Society of Nephrology": "Clinical Journal of the American Society of Nephrology",
    "Clinical Journal of the American Society of Nephrology : CJASN": "Clinical Journal of the American Society of Nephrology",
    "Clin J Am Soc Nephrol": "Clinical Journal of the American Society of Nephrology",
    # ---- 뇌졸중 ----
    "Stroke": "Stroke",
    "Stroke; a journal of cerebral circulation": "Stroke",
    # ---- 간/위장관 ----
    "Hepatology": "Hepatology",
    "Hepatology (Baltimore, Md.)": "Hepatology",
    "Journal of Hepatology": "Journal of Hepatology",
    "J Hepatol": "Journal of Hepatology",
    "Gastroenterology": "Gastroenterology",
    "Gut": "Gut",
    # ---- 오믹스/중개의학 ----
    "EBioMedicine": "EBioMedicine",
    "Genome Biology": "Genome Biology",
    "Genome Biol": "Genome Biology",
    "Genome Medicine": "Genome Medicine",
    "Genome Med": "Genome Medicine",
    "Molecular Systems Biology": "Molecular Systems Biology",
    "Mol Syst Biol": "Molecular Systems Biology",
    "Cell Systems": "Cell Systems",
    "Cell Syst": "Cell Systems",
    # ---- 디지털 헬스 ----
    "Lancet Digital Health": "Lancet Digital Health",
    "The Lancet Digital Health": "Lancet Digital Health",
    "The Lancet. Digital Health": "Lancet Digital Health",
    "Lancet Digit Health": "Lancet Digital Health",
    "npj Digital Medicine": "npj Digital Medicine",
    "NPJ Digit Med": "npj Digital Medicine",
    "npj Genomic Medicine": "npj Genomic Medicine",
    "NPJ Genom Med": "npj Genomic Medicine",
}

# 정규화 후 키 → canonical
_NORMALIZED_TARGETS: dict[str, str] = {
    normalize_journal(k): v for k, v in _RAW_TO_CANONICAL.items()
}


def match_target_journal(journal_name: str) -> str | None:
    """PubMed가 반환한 저널명이 대상 목록에 있는지 확인."""
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
