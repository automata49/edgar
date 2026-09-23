"""Pepper Google Sheets 워크스페이스 읽기 (읽기 전용).

Edgar는 시트 값을 다시 계산하지 않고 보기 좋게 보여주기만 합니다.
읽는 순서
1. Google Sheets API (spreadsheets.readonly) — GOOGLE_APPLICATION_CREDENTIALS 또는 ADC 인증 필요
2. Pepper가 `pepper sync`로 남긴 최신 스냅샷 (pepper/data/history/*/*/snapshot.json)
3. PEPPER_SHEET_SNAPSHOT 로 지정한 JSON (Pepper snapshot 형식)
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
TABS = ["Portfolio", "Research", "Financials", "Valuation", "Prices"]
# Pepper Settings!A5:B19 순서 (pepper-sheets-v1)
SETTINGS_LABELS = ["데이터 모드", "평가 기준일", "USD/KRW", "환율 기준일", "현금 KRW", "현금 USD",
                   "종목 비중 한도", "가격 위험 한도", "가격 허용 경과일", "평가 근거 유효일",
                   "재무 검토 유효일", "예상 거래 수수료율", "주가 스트레스", "외화가치 스트레스", "스키마"]
DATE_COLUMNS = {"평가 기준일", "환율 기준일", "검토일", "평가일", "TTM 종료일", "공시일", "가격일"}
_MAX_ROWS = 200


def serial_to_date(v):
    """시트 날짜 일련번호(1899-12-30 기준) → 'YYYY-MM-DD'. 숫자가 아니면 그대로."""
    if isinstance(v, (int, float)) and not isinstance(v, bool) and 20000 < v < 80000:
        return (date(1899, 12, 30) + timedelta(days=int(v))).isoformat()
    return v


def _clean(row: dict) -> dict:
    return {k: serial_to_date(v) if k in DATE_COLUMNS else v for k, v in row.items()}


def from_snapshot(snap: dict, source: str) -> dict:
    """Pepper snapshot(JSON) → Edgar 표시용 구조."""
    raw = snap.get("settings") or []
    settings = {k: v for k, v in zip(SETTINGS_LABELS, raw)} if isinstance(raw, list) else dict(raw)
    settings = _clean(settings)
    tables = {t: [_clean(r) for r in snap.get("tables", {}).get(t, [])] for t in TABS}
    return {"settings": settings, "tables": tables, "source": source}


def parse_values(ranges: dict[str, list[list]]) -> dict:
    """batchGet 결과 → {settings, tables}. 각 탭은 5행이 헤더, 첫 열이 빈 행은 건너뜁니다."""
    settings = {}
    for row in ranges.get("Settings", []):
        if row and row[0] not in (None, ""):
            settings[str(row[0])] = row[1] if len(row) > 1 else None
    tables = {}
    for tab in TABS:
        values = ranges.get(tab) or []
        if not values:
            tables[tab] = []
            continue
        headers = [str(h) for h in values[0]]
        rows = []
        for r in values[1:_MAX_ROWS + 1]:
            if not r or all(v in (None, "") for v in r[:2]):
                continue
            rows.append(_clean(dict(zip(headers, list(r) + [None] * (len(headers) - len(r))))))
        tables[tab] = rows
    return {"settings": _clean(settings), "tables": tables, "source": "sheets"}


class SheetReader:
    def __init__(self, spreadsheet_id: str | None, history_dir: str | None = None,
                 snapshot_path: str | None = None, ttl: int = 300) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.history_dir = Path(history_dir) if history_dir else None
        self.snapshot_path = Path(snapshot_path) if snapshot_path else None
        self.ttl = ttl
        self._cache: tuple[float, dict] | None = None
        self._lock = threading.Lock()

    @property
    def url(self) -> str | None:
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit" if self.spreadsheet_id else None

    def load(self, refresh: bool = False) -> dict | None:
        """캐시(기본 5분) → 시트 → 스냅샷 순으로 읽습니다. 모두 실패하면 None."""
        with self._lock:
            if not refresh and self._cache and time.time() - self._cache[0] < self.ttl:
                return self._cache[1]
            data = self._fetch_live() or self._latest_history() or self._snapshot_file()
            if data:
                data["loaded_at"] = time.strftime("%Y-%m-%d %H:%M")
                self._cache = (time.time(), data)
            return data

    def _fetch_live(self) -> dict | None:
        if not self.spreadsheet_id:
            return None
        try:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            credentials, _ = google.auth.default(scopes=SCOPES)
            session = AuthorizedSession(credentials)
            ranges = ["Settings!A5:B19"] + [f"{t}!A5:AZ{5 + _MAX_ROWS}" for t in TABS]
            resp = session.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{quote(self.spreadsheet_id, safe='')}/values:batchGet",
                params=[("ranges", r) for r in ranges] + [("valueRenderOption", "UNFORMATTED_VALUE"),
                                                         ("dateTimeRenderOption", "SERIAL_NUMBER")],
                timeout=30)
            resp.raise_for_status()
            values = [r.get("values", []) for r in resp.json().get("valueRanges", [])]
            return parse_values(dict(zip(["Settings", *TABS], values)))
        except Exception as e:  # noqa: BLE001 — 인증 미설정·네트워크 오류 시 스냅샷으로 대체
            logger.info("Google Sheets 직접 읽기 실패, 스냅샷 사용: %s", e)
            return None

    def _latest_history(self) -> dict | None:
        if not self.history_dir or not self.history_dir.exists():
            return None
        files = sorted(self.history_dir.glob("*/*/snapshot.json"), key=lambda p: p.parent.name)
        for f in reversed(files):
            try:
                return from_snapshot(json.loads(f.read_text(encoding="utf-8")), f"pepper sync ({f.parent.name[:10]})")
            except (OSError, json.JSONDecodeError):
                continue
        return None

    def _snapshot_file(self) -> dict | None:
        if not self.snapshot_path or not self.snapshot_path.exists():
            return None
        try:
            return from_snapshot(json.loads(self.snapshot_path.read_text(encoding="utf-8")),
                                 f"스냅샷 ({self.snapshot_path.name})")
        except (OSError, json.JSONDecodeError):
            return None


def spreadsheet_id_from(workspace_json: str | Path) -> str | None:
    try:
        return json.loads(Path(workspace_json).read_text(encoding="utf-8")).get("spreadsheet_id")
    except (OSError, json.JSONDecodeError):
        return None
