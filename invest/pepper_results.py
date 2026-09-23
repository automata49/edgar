"""Pepper가 만든 results JSON을 읽어 챗봇·리포트용으로 요약합니다.

Edgar는 숫자를 새로 계산하지 않습니다. 여기서는 Pepper 결과를 골라 담기만 합니다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROFILE_KO = {"minervini": "Minervini(추세)", "buffett": "Buffett(질·가치)",
              "fisher": "Fisher(성장 지속성)", "lynch": "Lynch(가격)"}


def load(path: str | Path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def find_tickers(text: str, results: dict | None) -> list[str]:
    if not results:
        return []
    known = results.get("tickers", {})
    words = set(re.findall(r"[A-Za-z0-9_]{2,12}", text.upper()))
    return [t for t in known if t.upper() in words]


def compact(ticker: str, r: dict) -> dict:
    """LLM 프롬프트에 넣을 핵심 값만 추립니다 (토큰 절약)."""
    profiles = {}
    for name, p in r.get("profiles", {}).items():
        profiles[name] = {
            "score": p.get("score"), "coverage": p.get("coverage"), "verdict": p.get("verdict"),
            "status": p.get("status"),
            "criteria": [{k: c.get(k) for k in ("label", "status", "value", "label_result", "reason") if c.get(k) is not None}
                         for c in p.get("criteria", [])],
        }
    return {"ticker": ticker, "tags": r.get("tags"), "lynch_category": r.get("lynch_category"),
            "swing_status": r.get("swing_status"), "stop_price": r.get("stop_price"),
            "composites": r.get("composites"), "valuation": r.get("valuation"),
            "flags": r.get("flags"), "profiles": profiles}


def summary_lines(results: dict, limit: int = 20) -> list[str]:
    lines = [f"📊 Pepper 결과 기준일 {results.get('asof')} (규칙 {results.get('rules_version', {}).get('minervini')})"]
    for t, r in list(results.get("tickers", {}).items())[:limit]:
        pos = (r.get("composites", {}).get("position") or {}).get("score")
        val = r.get("valuation", {})
        label = val.get("label") or val.get("model")
        if val.get("label_status") == "UNVERIFIED":
            label = f"{label}*"
        flags = " ⚠️" if r.get("flags") else ""
        lines.append(f"• {t}: 스윙 {r.get('swing_status')} · 장기 {pos if pos is not None else '-'}점 · 가치 {label}{flags}")
    lines.append("* 미검증 입력 사용, ⚠️ 데이터 갱신 필요")
    return lines


def ticker_card(ticker: str, r: dict) -> str:
    lines = [f"🔎 {ticker} ({', '.join(r.get('tags') or []) or '태그 없음'})"]
    for name, p in r.get("profiles", {}).items():
        score = p.get("score")
        extra = f" · {p['status']}" if p.get("status") else ""
        lines.append(f"• {PROFILE_KO.get(name, name)}: {score if score is not None else '-'}점 "
                     f"({p.get('verdict')}, 데이터 {int((p.get('coverage') or 0) * 100)}%){extra}")
    v = r.get("valuation", {})
    if v.get("fair_value"):
        lines.append(f"• 적정가 {v['fair_value']:,.2f} ({v.get('fair_value_method')}) → {v.get('label')}"
                     f"{' [미검증 입력]' if v.get('label_status') == 'UNVERIFIED' else ''}")
    elif v.get("note"):
        lines.append(f"• {v['note']}")
    if r.get("stop_price"):
        lines.append(f"• 권장 손절가 {r['stop_price']:,.2f}")
    for f in r.get("flags") or []:
        lines.append(f"⚠️ {f}")
    return "\n".join(lines)
