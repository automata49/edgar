from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime


class ReportSummarizer:
    """
    [1단계] 네이버 리포트 목록 → 종목별 한국어 요약 생성.

    - 동일 종목 리포트를 묶어 하나의 요약 생성
    - 2~3개 핵심 주제 중심으로 요약
    - 고등학생도 이해할 수 있는 언어 사용
    """

    def __init__(self, config: dict) -> None:
        self.provider    = config.get("llm_provider", "deepseek")
        cfg              = config.get("report_summary", {})
        self.output_dir: str = cfg.get("output_dir", "data/summaries")
        self.max_chars:  int = cfg.get("max_text_chars", 3000)
        self._client     = self._init_client(config)

    # ── Public API ───────────────────────────────────────────────────────────

    def summarize_by_stock(self, reports: list[dict]) -> list[dict]:
        """종목별로 리포트를 묶어 요약 생성. 저장 후 목록 반환."""
        grouped  = self._group_by_stock(reports)
        results: list[dict] = []
        for stock_name, stock_reports in grouped.items():
            print(f"   📝 {stock_name} 요약 생성 중... ({len(stock_reports)}건)")
            summary = self._summarize_stock(stock_name, stock_reports)
            self._save(summary)
            results.append(summary)
        return results

    # ── Grouping ─────────────────────────────────────────────────────────────

    def _group_by_stock(self, reports: list[dict]) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = defaultdict(list)
        for report in reports:
            name = report.get("stock_name", "Unknown")
            groups[name].append(report)
        return dict(groups)

    # ── Summarization ────────────────────────────────────────────────────────

    def _summarize_stock(self, stock_name: str, reports: list[dict]) -> dict:
        combined = self._combine_texts(reports)
        prompt   = self._build_prompt(stock_name, reports, combined)
        raw      = self._call_llm(prompt)
        return self._parse(raw, stock_name, reports)

    def _combine_texts(self, reports: list[dict]) -> str:
        parts: list[str] = []
        budget = self.max_chars
        for r in reports:
            text = r.get("text", "").strip()
            if not text:
                continue
            chunk = text[: min(budget, 1200)]
            parts.append(f"[{r.get('firm', '')} / {r.get('date', '')}]\n{chunk}")
            budget -= len(chunk)
            if budget <= 0:
                break
        return "\n\n---\n\n".join(parts)

    def _build_prompt(self, stock_name: str, reports: list[dict], combined: str) -> str:
        report_list = "\n".join(
            f"  - [{r.get('date', '')}] {r.get('firm', '')}: {r.get('title', '')}"
            for r in reports
        )
        key_numbers = []
        for r in reports:
            key_numbers.extend(r.get("key_numbers", []))
        nums_str = ", ".join(list(dict.fromkeys(key_numbers))[:6]) or "없음"

        return f"""당신은 금융 리포트를 누구나 쉽게 이해할 수 있게 요약하는 전문가입니다.

## 종목명: {stock_name}
## 분석 리포트 목록:
{report_list}
## 핵심 수치: {nums_str}

## 리포트 원문:
{combined}

---
**요약 지침:**
1. 2~3개의 핵심 주제를 중심으로 정리하세요
2. 고등학생이 이해할 수 있는 쉬운 언어로 작성하세요
3. 어려운 금융 용어는 괄호 안에 짧게 설명하세요 (예: PER(주가수익비율))
4. 핵심 숫자·수치는 반드시 포함하세요
5. 각 주제별로 "왜 중요한지"를 한 문장으로 덧붙이세요

아래 JSON 형식으로만 응답하세요 (마크다운 코드 블록 없이):

{{
  "stock_name": "{stock_name}",
  "one_line": "한 줄 핵심 요약 (40자 이내)",
  "sentiment": "긍정 | 중립 | 부정",
  "key_themes": ["주제1 제목", "주제2 제목"],
  "theme_details": [
    {{
      "theme": "주제 제목",
      "content": "쉬운 설명 (80~120자)",
      "key_stat": "핵심 수치 또는 '없음'",
      "why_matters": "왜 중요한지 한 문장"
    }}
  ],
  "summary": "전체 흐름 요약 (200~300자, 고등학생 눈높이)"
}}"""

    # ── LLM Call ─────────────────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> str:
        try:
            if self.provider == "claude":
                msg = self._client.messages.create(
                    model=self._model, max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text
            if self.provider == "gemini":
                return self._client.generate_content(prompt).text
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f'{{"error": "{e}"}}'

    # ── Parse ────────────────────────────────────────────────────────────────

    def _parse(self, raw: str, stock_name: str, reports: list[dict]) -> dict:
        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        clean = re.sub(r"\s*```\s*$", "", clean.strip(), flags=re.MULTILINE).strip()

        data: dict = {}
        try:
            data = json.loads(clean)
        except Exception:
            pass
        if not data:
            try:
                m = re.search(r"\{.*\}", clean, re.DOTALL)
                if m:
                    data = json.loads(m.group())
            except Exception:
                pass

        if not data or "error" in data:
            print(f"   ⚠️  {stock_name} 요약 파싱 실패 → fallback 사용")
            return self._fallback(stock_name, reports)

        data.setdefault("stock_name",   stock_name)
        data.setdefault("report_count", len(reports))
        data.setdefault("generated_at", datetime.now().isoformat())
        return data

    def _fallback(self, stock_name: str, reports: list[dict]) -> dict:
        nums = []
        for r in reports:
            nums.extend(r.get("key_numbers", []))
        return {
            "stock_name":    stock_name,
            "one_line":      f"{stock_name} 분석 리포트 {len(reports)}건",
            "sentiment":     "중립",
            "key_themes":    ["투자의견", "목표주가"],
            "theme_details": [
                {
                    "theme":       "투자의견",
                    "content":     "증권사 분석사들의 투자의견을 정리한 내용입니다.",
                    "key_stat":    nums[0] if nums else "없음",
                    "why_matters": "투자 결정에 직접적인 영향을 미칩니다.",
                }
            ],
            "summary":      f"{stock_name}에 대한 {len(reports)}건의 리포트를 수집했습니다. "
                            f"핵심 수치: {', '.join(nums[:3]) or '없음'}",
            "report_count": len(reports),
            "generated_at": datetime.now().isoformat(),
        }

    # ── Save ─────────────────────────────────────────────────────────────────

    def _save(self, summary: dict) -> None:
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            stock = re.sub(r"[^\w가-힣\-]", "_", summary.get("stock_name", "unknown"))
            path  = os.path.join(self.output_dir, f"{stock}_summary.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   ⚠️  요약 저장 실패: {e}")

    # ── LLM Init ─────────────────────────────────────────────────────────────

    def _init_client(self, config: dict):
        p = self.provider
        if p == "deepseek":
            from openai import OpenAI
            self._model = "deepseek-chat"
            return OpenAI(api_key=config.get("deepseek_api_key"), base_url="https://api.deepseek.com")
        if p == "groq":
            from groq import Groq
            self._model = "llama-3.3-70b-versatile"
            return Groq(api_key=config.get("groq_api_key"))
        if p == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=config.get("gemini_api_key"))
            self._model = "gemini-pro"
            return genai.GenerativeModel(self._model)
        if p == "claude":
            from anthropic import Anthropic
            self._model = "claude-sonnet-4-6"
            return Anthropic(api_key=config.get("anthropic_api_key"))
        raise ValueError(f"Unknown provider: {p}")
