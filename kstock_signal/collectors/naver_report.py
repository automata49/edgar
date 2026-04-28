from __future__ import annotations

import io
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pdfplumber
import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://finance.naver.com/",
}
_LIST_URL = "https://finance.naver.com/research/company_list.naver"


@dataclass
class NaverReport:
    stock_name:  str
    firm:        str
    title:       str
    target_price: str
    date:        str
    pdf_url:     str
    report_id:   str = ""
    text:        str = ""
    key_numbers: list[str] = field(default_factory=list)


class NaverReportCollector:
    """네이버 금융 종목분석 리포트 수집 및 PDF 텍스트 추출."""

    def __init__(self, config: dict) -> None:
        cfg = config.get("naver_report", {})
        self.target_symbols: list[str] = cfg.get("target_symbols", [])
        self.max_reports:    int        = cfg.get("max_reports", 3)
        self.session = requests.Session()
        self.session.headers.update(_HEADERS)

    async def collect(self) -> list[dict]:
        print("📑 네이버 리포트 수집 중...")
        reports = self._fetch_list()

        if self.target_symbols:
            filtered = [r for r in reports if any(s in r.stock_name for s in self.target_symbols)]
            reports  = filtered or reports  # 매칭 없으면 전체 사용

        reports = reports[: self.max_reports]
        results: list[dict] = []

        for rpt in reports:
            text = self._extract_pdf_text(rpt.pdf_url)
            if text:
                rpt.text        = text
                rpt.key_numbers = self._extract_key_numbers(text)
            results.append(self._to_dict(rpt))
            time.sleep(0.5)  # 서버 부하 방지

        print(f"✅ 네이버 리포트: {len(results)}건\n")
        return results

    # ── List Scraping ────────────────────────────────────────────────────────

    def _fetch_list(self) -> list[NaverReport]:
        """
        실제 테이블 컬럼 순서:
          [0] 종목명  [1] 리포트 제목(+nid href)  [2] 증권사
          [3] PDF 링크(img cell)  [4] 날짜  [5] 조회수
        """
        reports: list[NaverReport] = []
        try:
            r = self.session.get(_LIST_URL, timeout=10)
            r.encoding = "euc-kr"
            soup = BeautifulSoup(r.text, "html.parser")

            table = soup.find("table", class_="type_1")
            if not table:
                return reports

            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 5:
                    continue

                stock_name = cells[0].get_text(strip=True)
                if not stock_name:
                    continue

                # 리포트 제목 + nid 추출
                title_tag  = cells[1].find("a")
                title      = title_tag.get_text(strip=True) if title_tag else ""
                report_id  = ""
                if title_tag and title_tag.get("href"):
                    m = re.search(r"nid=(\d+)", title_tag["href"])
                    if m:
                        report_id = m.group(1)

                firm = cells[2].get_text(strip=True)
                date = cells[4].get_text(strip=True)

                # PDF URL: cell[3] 앵커 href 직접 사용
                pdf_url = ""
                pdf_tag = cells[3].find("a")
                if pdf_tag and pdf_tag.get("href", ""):
                    href = pdf_tag["href"]
                    pdf_url = href if href.startswith("http") else "https://finance.naver.com" + href

                if not title:
                    continue

                reports.append(NaverReport(
                    stock_name=stock_name,
                    firm=firm,
                    title=title,
                    target_price="",
                    date=date,
                    pdf_url=pdf_url,
                    report_id=report_id,
                ))
        except Exception as e:
            print(f"   ⚠️  네이버 리포트 리스트 오류: {e}")
        return reports

    # ── PDF Extraction ───────────────────────────────────────────────────────

    def _extract_pdf_text(self, pdf_url: str) -> str:
        if not pdf_url:
            return ""
        try:
            r = self.session.get(pdf_url, timeout=15)
            if r.status_code != 200 or len(r.content) < 100:
                return ""
            # Naver는 PDF를 application/octet-stream으로 서빙 — magic bytes로 검증
            if not r.content.startswith(b"%PDF"):
                return ""

            with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                pages = pdf.pages[:8]  # 처음 8페이지만 (리포트 요약부)
                text  = "\n".join(p.extract_text() or "" for p in pages)
            return text.strip()
        except Exception as e:
            print(f"   ⚠️  PDF 추출 실패 ({pdf_url[:60]}): {e}")
            return ""

    # ── Key Number Extraction ────────────────────────────────────────────────

    def _extract_key_numbers(self, text: str) -> list[str]:
        """텍스트에서 투자 핵심 수치 추출 (목표가, 영업이익, 매출 등)."""
        patterns = [
            r"목표[주가가격][\s:：]*[\d,]+원",
            r"영업이익[\s:：]*[\d,]+억?원",
            r"매출[액]?[\s:：]*[\d,]+억?원",
            r"순이익[\s:：]*[\d,]+억?원",
            r"[＋\+][\d.]+%",
            r"[-－][\d.]+%",
            r"PER[\s:：]*[\d.]+배",
            r"ROE[\s:：]*[\d.]+%",
        ]
        numbers: list[str] = []
        for pat in patterns:
            matches = re.findall(pat, text)
            numbers.extend(matches[:2])
        return numbers[:8]

    def _to_dict(self, r: NaverReport) -> dict:
        return {
            "stock_name":   r.stock_name,
            "firm":         r.firm,
            "title":        r.title,
            "target_price": r.target_price,
            "date":         r.date,
            "pdf_url":      r.pdf_url,
            "report_id":    r.report_id,
            "text":         r.text,
            "key_numbers":  r.key_numbers,
            "collected_at": datetime.now().isoformat(),
        }
