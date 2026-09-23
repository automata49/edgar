"""리서치 리포트 행(research_reports) → 텔레그램/프롬프트용 일반 텍스트."""
from __future__ import annotations

CHANGE_MARK = {"상향": "▲", "하향": "▼", "유지": "", "신규": "🆕", "미확인": ""}
SENTIMENT_MARK = {"긍정": "🟢", "중립": "⚪", "부정": "🔴"}


def won(v) -> str:
    return f"{v:,}원" if isinstance(v, int) and not isinstance(v, bool) and v > 0 else "-"


def stock_label(row: dict) -> str:
    code = row.get("stock_code")
    return f"{row.get('stock_name')} ({code})" if code else str(row.get("stock_name"))


def one_line(row: dict) -> str:
    return str((row.get("summary") or {}).get("one_line") or row.get("title") or "")


def opinion_target(row: dict) -> str:
    """'매수 · 목표 516,000원▲' 형식."""
    parts = []
    if row.get("opinion") and row["opinion"] != "미확인":
        parts.append(str(row["opinion"]))
    if row.get("target_value"):
        parts.append(f"목표 {won(row['target_value'])}{CHANGE_MARK.get(row.get('target_change'), '')}")
    return " · ".join(parts) or "의견·목표가 미확인"


def group_by_stock(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(stock_label(r), []).append(r)
    return groups


def daily_section(rows: list[dict], limit: int = 15) -> str:
    """Daily 메시지의 '오늘의 증권사 리포트' 블록."""
    if not rows:
        return ""
    groups = group_by_stock(rows)
    lines = [f"📑 오늘의 증권사 리포트 ({len(rows)}건 · {len(groups)}종목)", "━" * 30]
    for label, items in list(groups.items())[:limit]:
        lines.append(f"{SENTIMENT_MARK.get(items[0].get('sentiment'), '•')} {label}")
        for r in items[:3]:
            lines.append(f"  {r.get('firm')} · {opinion_target(r)}")
            lines.append(f"  └ {one_line(r)}")
    if len(groups) > limit:
        lines.append(f"… 외 {len(groups) - limit}종목 (/research 로 전체 보기)")
    return "\n".join(lines)


def prompt_lines(rows: list[dict], limit: int = 25) -> str:
    """분석 프롬프트에 넣을 요약 (종목 · 증권사 · 의견 · 한 줄)."""
    out = []
    for r in rows[:limit]:
        out.append(f"[{stock_label(r)}] {r.get('firm')} · {opinion_target(r)} · "
                   f"{r.get('sentiment') or '중립'} — {one_line(r)}")
    return "\n".join(out) or "없음"
