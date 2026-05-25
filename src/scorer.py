"""
Claude API를 사용한 관련성 점수 + 한국어 요약 생성.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from anthropic import Anthropic

PROMPT_TEMPLATE = """다음은 PubMed에서 검색된 최신 논문입니다.
아래 우리 연구실 과제와의 **관련성**을 0-10점으로 평가하고 한국어 요약을 작성해주세요.

# 우리 연구실 과제
1. **MFDS (식약처)**: 다중오믹스 통합, 약물반응/약물유해반응 예측, 정밀의료, 만성대사질환(당뇨/심혈관/MASLD/CKD/뇌졸중), 코호트/바이오뱅크, EHR/RWD
2. **DGDB (데기디바)**: 제2형 당뇨 + Foundation model / LLM / Self-supervised / Federated learning
3. **GDM (질병관리청)**: 임신성당뇨 (GDM→T2D 전환 / CGM / GWAS·Genetics / Microbiome)

# 점수 가이드
- 10: 위 과제와 직접 관련 (예: GDM cohort에서 microbiome으로 T2D 전환 예측)
- 7-9: 핵심 키워드 다수 일치, 방법론도 부합
- 4-6: 부분 관련 (예: 당뇨 일반론, 무관한 질환의 multi-omics)
- 0-3: 거의 무관 (예: 식물 유전학, 동물 모델 only)

# 검색 컨텍스트 (이 쿼리로 잡힌 논문)
- 프로젝트: {project}
- 서브토픽: {subtopic}

# 논문 정보
제목: {title}
저널: {journal}
초록:
{abstract}

# 출력 (반드시 아래 JSON 형식, 다른 텍스트 금지)
{{
  "relevance_score": <0~10 정수>,
  "topic_match": "<MFDS | DGDB | GDM | 없음>",
  "summary_kr": "<3~5문장 한국어 요약. 무엇을 했고, 어떤 데이터/방법, 핵심 결과까지>",
  "key_points": ["<핵심 포인트 1>", "<핵심 포인트 2>", "<핵심 포인트 3>"],
  "reason": "<점수 부여 근거 한 문장>"
}}"""


class Scorer:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 가 비어 있습니다.")
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def score(self, article: dict, project: str, subtopic: str) -> Optional[dict]:
        """단일 논문 점수 매기기. 실패 시 None 반환."""
        if not article.get("abstract"):
            # 초록 없는 논문은 점수 0으로 처리
            return {
                "relevance_score": 0,
                "topic_match": "없음",
                "summary_kr": "초록 없음 — 평가 불가",
                "key_points": [],
                "reason": "abstract 비어있음",
            }

        prompt = PROMPT_TEMPLATE.format(
            project=project,
            subtopic=subtopic,
            title=article["title"][:500],
            journal=article["journal"],
            abstract=article["abstract"][:4000],
        )

        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip()
            return _parse_json(text)
        except Exception as e:
            print(f"  [WARN] PMID {article.get('pmid')} 점수 매기기 실패: {e}")
            return None


def _parse_json(text: str) -> Optional[dict]:
    """Claude 응답에서 JSON 추출 (코드펜스 등 제거)."""
    # ```json ... ``` 제거
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # 첫 { 부터 마지막 } 까지
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON 파싱 실패: {e}\n원문: {text[:300]}")
        return None
