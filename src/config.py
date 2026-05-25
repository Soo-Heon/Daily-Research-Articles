"""
설정: PubMed 쿼리, 대상 저널, 점수 임계값
"""

# 점수 임계값 (0-10). 이 점수 이상의 논문만 메일로 발송.
SCORE_THRESHOLD = 6

# 며칠 전부터 검색할지 (1 = 어제 ~ 오늘)
DAYS_BACK = 1

# 각 서브쿼리당 최대 검색 결과 수 (PubMed API 부하 방지)
MAX_RESULTS_PER_QUERY = 50

# 전체 처리할 최대 논문 수 (Claude API 비용 방지)
MAX_TOTAL_ARTICLES = 100

# Claude 모델 (요약/점수용). 비용 효율 위해 Haiku 사용.
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# 우선 저널 (점수에 +1 가산점)
TARGET_JOURNALS = [
    "Nature", "Science", "Cell",
    "Nature Genetics", "Nature Medicine", "Nature Communications",
    "Nature Biotechnology", "Nature Methods", "Nature Metabolism",
    "Cell Metabolism", "Cell Reports Medicine",
    "Lancet", "Lancet Diabetes Endocrinology", "Lancet Digital Health",
    "Diabetes Care", "Diabetologia", "Diabetes",
    "JAMA", "JAMA Internal Medicine", "JAMA Network Open",
    "New England Journal of Medicine", "NEJM",
    "npj Digital Medicine", "npj Genomic Medicine",
    "Science Translational Medicine",
    "BMJ", "Annals of Internal Medicine",
]


# ---------- 쿼리 정의 ----------
# 각 쿼리는 (프로젝트, 서브토픽, 쿼리문자열) 형태
QUERIES = [
    # =================================================================
    # 1. 식약처(MFDS) 과제: 다중오믹스 × 약물반응 × 만성대사질환
    # =================================================================
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

    # =================================================================
    # 2. 데기디바: T2D × Foundation model / LLM / Federated
    # =================================================================
    (
        "DGDB",
        "T2D × Foundation/LLM/Federated",
        '("type 2 diabetes" OR "diabetic complication*") '
        'AND ("foundation model" OR "large language model" OR "self-supervised" OR "federated learning") '
        'AND ("prediction" OR "diagnosis" OR "prognosis")',
    ),

    # =================================================================
    # 3. 질병관리청 GDM 과제 (4개 서브토픽)
    # =================================================================
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
