"""네이버 종목분석 리포트 1건 → 구조화된 한국어 요약.

ModelRouter의 `report_summary` 작업(무료 Gemini 티어, 기본 gemini-3.8-flash)을 사용합니다.
숫자(목표주가·실적)는 리포트 본문에 적힌 값만 옮기고 새로 계산하지 않습니다.
"""
from __future__ import annotations

import json
import re

SYSTEM = """너는 증권사 리서치 리포트를 정리하는 조사원이다. 한국어로 답한다.
- 제공된 본문에 적힌 내용과 숫자만 사용한다. 계산·추정·외부 지식은 쓰지 않는다.
- 본문에서 확인할 수 없는 값은 0 또는 '미확인'으로 둔다.
- 목표주가·현재주가는 원 단위 정수로 적는다 (예: '9만 원' → 90000).
- 쉬운 말로 쓰되 핵심 숫자(매출·영업이익·성장률 등)는 본문 표기 그대로 포함한다."""

SCHEMA = {
    "type": "object",
    "properties": {
        "one_line":       {"type": "string", "description": "핵심 한 줄 (60자 이내)"},
        "sentiment":      {"type": "string", "enum": ["긍정", "중립", "부정"]},
        "opinion":        {"type": "string", "description": "투자의견 (예: 매수, Buy, 중립). 없으면 '미확인'"},
        "opinion_change": {"type": "string", "enum": ["상향", "하향", "유지", "신규", "미확인"]},
        "target_price":   {"type": "integer", "description": "목표주가(원). 없으면 0"},
        "target_change":  {"type": "string", "enum": ["상향", "하향", "유지", "신규", "미확인"]},
        "current_price":  {"type": "integer", "description": "리포트에 적힌 현재주가(원). 없으면 0"},
        "key_points":     {"type": "array", "items": {"type": "string"}, "description": "핵심 포인트 3개 (각 80자 이내)"},
        "risks":          {"type": "array", "items": {"type": "string"}, "description": "리스크 0~2개"},
        "numbers":        {"type": "array", "items": {
            "type": "object",
            "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
            "required": ["label", "value"]}, "description": "핵심 수치 최대 5개 (본문 표기 그대로)"},
    },
    "required": ["one_line", "sentiment", "opinion", "opinion_change", "target_price", "target_change",
                 "current_price", "key_points", "risks", "numbers"],
}

_CHANGES = {"상향", "하향", "유지", "신규", "미확인"}


class ReportSummarizer:
    def __init__(self, router, config: dict | None = None) -> None:
        self.router = router
        self.max_chars = (config or {}).get("naver_report", {}).get("max_text_chars", 6000)

    def summarize(self, report: dict) -> dict:
        """리포트 dict(수집기 결과) → 요약 dict. 모델 실패 시 제목·정규식 기반 최소 요약."""
        text = (report.get("text") or "").strip()
        if not text:
            return fallback_summary(report, "PDF 본문 없음")
        prompt = (f"종목: {report.get('stock_name')} ({report.get('stock_code') or '코드 미확인'})\n"
                  f"증권사: {report.get('firm')} · 날짜: {report.get('date')}\n"
                  f"제목: {report.get('title')}\n\n본문:\n{text[: self.max_chars]}")
        result = self.router.run("report_summary", prompt, system=SYSTEM, json_schema=SCHEMA)
        if not result.ok:
            return fallback_summary(report, "; ".join(result.notes) or "모델 호출 실패")
        try:
            data = parse_json(result.text)
        except ValueError:
            return fallback_summary(report, "요약 형식 오류")
        return normalize(data, model=result.model)


def parse_json(raw: str) -> dict:
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if not m:
            raise ValueError("JSON 없음") from None
        try:
            data = json.loads(m.group())
        except json.JSONDecodeError as e:
            raise ValueError(str(e)) from e
    if not isinstance(data, dict):
        raise ValueError("JSON 객체 아님")  # noqa: TRY004 — 호출부가 ValueError로 형식 오류를 처리
    return data


def _price(v) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v) if v > 0 else None
    digits = re.sub(r"[^\d]", "", str(v or ""))
    return int(digits) if digits and int(digits) > 0 else None


def normalize(data: dict, model: str | None) -> dict:
    """모델 출력의 형식을 정리합니다 (값을 새로 계산하지 않음)."""
    def text_list(v, n):
        return [str(x).strip() for x in v if str(x).strip()][:n] if isinstance(v, list) else []

    numbers = []
    for x in data.get("numbers") or []:
        if isinstance(x, dict) and x.get("label") and x.get("value"):
            numbers.append({"label": str(x["label"]), "value": str(x["value"])})
    return {
        "one_line":       str(data.get("one_line") or "").strip()[:120],
        "sentiment":      data.get("sentiment") if data.get("sentiment") in ("긍정", "중립", "부정") else "중립",
        "opinion":        str(data.get("opinion") or "미확인").strip()[:20],
        "opinion_change": data.get("opinion_change") if data.get("opinion_change") in _CHANGES else "미확인",
        "target_price":   _price(data.get("target_price")),
        "target_change":  data.get("target_change") if data.get("target_change") in _CHANGES else "미확인",
        "current_price":  _price(data.get("current_price")),
        "key_points":     text_list(data.get("key_points"), 3),
        "risks":          text_list(data.get("risks"), 2),
        "numbers":        numbers[:5],
        "model":          model,
        "status":         "ok",
    }


_TARGET_RE = re.compile(r"목표\s*주?가[^\d]{0,15}([\d,]{4,})\s*원")


def fallback_summary(report: dict, reason: str) -> dict:
    """모델 없이 만들 수 있는 최소 요약: 제목 + 본문의 '목표주가 NN원' 표기."""
    m = _TARGET_RE.search(report.get("text") or "")
    return {
        "one_line": str(report.get("title") or "")[:120], "sentiment": "중립",
        "opinion": "미확인", "opinion_change": "미확인",
        "target_price": _price(m.group(1)) if m else None, "target_change": "미확인",
        "current_price": None, "key_points": [], "risks": [],
        "numbers": [{"label": "추출 수치", "value": v} for v in (report.get("key_numbers") or [])[:5]],
        "model": None, "status": f"요약 실패: {reason}"[:200],
    }
