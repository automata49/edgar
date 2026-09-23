from __future__ import annotations

import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from invest import sheets, views

SNAPSHOT = {
    "schema": "pepper-sheets-v1",
    "settings": ["Demo", 46283, 1300, 46283, 3000000, 2000, 0.25, 0.02, 4, 120, 180, 0.001, -0.2, -0.1,
                 "pepper-sheets-v1"],
    "tables": {
        "Portfolio": [{"ID": "P1", "Ticker": "DEMO_US", "전략": "Swing", "현재 수량": 10, "평균단가": 80,
                       "손절 기준": 90, "계획 수량": 15, "보유 논리": "돌파 <테스트>", "무효화 조건": "이탈",
                       "검토일": 46283, "현재가": 100, "통화": "USD", "평가액 KRW": 1300000,
                       "적용 계획수량": 15, "증감 수량": 5, "현재 비중": 0.16455, "계획 비중": 0.24685,
                       "가격손익 KRW": 260000, "점검": "조건 확인", "입력 상태": "OK", "섹터": "Technology"}],
        "Research": [{"ID": "R1", "Ticker": "DEMO_US", "전략": "Swing", "평가 항목": "Trend", "판정": "PASS",
                      "관측값": 72, "단위": "RS", "평가 근거": "RS 상위", "근거 상태": "확인"},
                     {"ID": "R2", "Ticker": "DEMO_US", "전략": "Swing", "평가 항목": "Volume", "판정": "UNKNOWN",
                      "관측값": "", "단위": "", "근거 상태": "미평가"}],
        "Financials": [{"Ticker": "DEMO_US", "기간 역할": "Current", "TTM 종료일": 46203, "통화": "USD",
                        "매출": 1500, "순이익": 240, "순이익률": 0.16, "자산회전율": 1.25, "재무레버리지": 1.846,
                        "ROE": 0.369, "FCF": 180, "현금 전환율": 1.1667, "TTM EPS": 4, "입력 상태": "OK"}],
        "Valuation": [], "Prices": [{"Ticker": "DEMO_US", "종목명": "가상", "시장": "US", "통화": "USD",
                                     "현재가": 100, "가격일": 46283, "입력 상태": "OK"}],
    },
}

ALLOWED_TAGS = {"b", "i", "code", "a"}


class TagChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.bad = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self.bad.append(tag)
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.bad.append("/" + tag)


def assert_telegram_html(tc: unittest.TestCase, page: views.Page) -> None:
    p = TagChecker()
    p.feed(page.text)
    tc.assertEqual(p.bad, [], page.text)
    tc.assertEqual(p.stack, [], page.text)
    tc.assertLessEqual(len(page.text), 4096)
    for row in page.buttons:
        for _, data in row:
            tc.assertLessEqual(len(data.encode()), 64)


class SheetParseTest(unittest.TestCase):
    def test_snapshot_dates_and_settings(self):
        sheet = sheets.from_snapshot(SNAPSHOT, "test")
        self.assertEqual(sheet["settings"]["평가 기준일"], "2026-09-18")
        self.assertEqual(sheet["settings"]["현금 KRW"], 3000000)
        self.assertEqual(sheet["tables"]["Portfolio"][0]["검토일"], "2026-09-18")

    def test_parse_values_uses_header_row_and_skips_blank_rows(self):
        ranges = {"Settings": [["데이터 모드", "Live"], ["평가 기준일", 46283]],
                  "Prices": [["Ticker", "현재가", "가격일"], ["AAA", 10, 46283], [], ["", ""], ["BBB", 20]]}
        sheet = sheets.parse_values(ranges)
        self.assertEqual(sheet["settings"]["평가 기준일"], "2026-09-18")
        self.assertEqual([r["Ticker"] for r in sheet["tables"]["Prices"]], ["AAA", "BBB"])
        self.assertIsNone(sheet["tables"]["Prices"][1]["가격일"])
        self.assertEqual(sheet["tables"]["Portfolio"], [])

    def test_reader_falls_back_to_latest_pepper_history(self):
        with tempfile.TemporaryDirectory() as d:
            for stamp in ("2026-09-17_20260917T000000Z", "2026-09-18_20260918T000000Z"):
                p = Path(d) / "demo" / stamp
                p.mkdir(parents=True)
                snap = dict(SNAPSHOT, settings=["Demo", 46282 if "17" in stamp else 46283] + SNAPSHOT["settings"][2:])
                (p / "snapshot.json").write_text(json.dumps(snap), encoding="utf-8")
            data = sheets.SheetReader(None, history_dir=d).load()
            self.assertEqual(data["settings"]["평가 기준일"], "2026-09-18")
            self.assertIn("pepper sync", data["source"])

    def test_reader_returns_none_without_any_source(self):
        self.assertIsNone(sheets.SheetReader(None, history_dir="/nonexistent").load())


class ViewsTest(unittest.TestCase):
    def setUp(self):
        self.sheet = sheets.from_snapshot(SNAPSHOT, "test")

    def test_portfolio_overview(self):
        page = views.portfolio(self.sheet)
        assert_telegram_html(self, page)
        self.assertIn("Demo 모드", page.text)
        self.assertIn("1,300,000원", page.text)
        self.assertIn("16.5% → 24.7%", page.text)
        self.assertIn("+260,000원", page.text)
        self.assertIn(("🔍 DEMO_US", "v:pf:DEMO_US"), page.buttons[0])

    def test_portfolio_detail_escapes_user_text(self):
        page = views.portfolio_detail(self.sheet, "demo_us")
        assert_telegram_html(self, page)
        self.assertIn("돌파 &lt;테스트&gt;", page.text)

    def test_research_counts_and_detail(self):
        page = views.research(self.sheet)
        assert_telegram_html(self, page)
        self.assertIn("✅1 ⚪1", page.text)
        detail = views.research_detail(self.sheet, "DEMO_US")
        assert_telegram_html(self, detail)
        self.assertIn("✅ Trend: 72 RS", detail.text)
        self.assertIn("(미평가)", detail.text)

    def test_financials_prices_valuation(self):
        for page in (views.financials(self.sheet), views.financials(self.sheet, "DEMO_US"),
                     views.prices(self.sheet), views.valuation(self.sheet)):
            assert_telegram_html(self, page)
        self.assertIn("ROE 36.9%", views.financials(self.sheet).text)

    def test_market_groups_and_arrows(self):
        snap = {"SPX": {"price": 5000.5, "change_percent": 1.2}, "BTC": {"price": 60000, "change_percent": -2.5}}
        page = views.market(snap, {"SPX": "indices", "BTC": "crypto"}, "2026-09-22T08:00:00")
        assert_telegram_html(self, page)
        self.assertIn("🔺", page.text)
        self.assertIn("-2.50%", page.text)
        self.assertIn("2026-09-22 08:00", page.text)

    def test_news_pagination_and_link_escaping(self):
        items = [{"title": f"기사 {i} & <b>", "url": f"https://x.com/?a={i}&b=\"1\"", "source": "S",
                  "published_at": "2026-09-22T01:00:00"} for i in range(20)]
        p1, p3 = views.news(items, 1), views.news(items, 3)
        for p in (p1, p3):
            assert_telegram_html(self, p)
        self.assertIn(("다음 ▶", "v:news:2"), p1.buttons[0])
        self.assertIn("17. ", p3.text)
        self.assertNotIn(("다음 ▶", "v:news:4"), p3.buttons[0])

    def test_long_report_is_cut_on_line_boundary(self):
        rep = {"id": 1, "analysis": "\n".join(f"<줄 {i}>" * 5 for i in range(500)), "action_plan": None}
        page = views.report(rep)
        assert_telegram_html(self, page)
        self.assertTrue(page.text.endswith("…(생략)"))

    def test_home_menu(self):
        page = views.home("https://docs.google.com/x")
        assert_telegram_html(self, page)
        self.assertEqual(page.buttons[-1][0][1], "url:https://docs.google.com/x")


class MatchViewTest(unittest.TestCase):
    def test_show_requests_map_to_views(self):
        cases = {"포트폴리오 보여줘": "pf", "뉴스 확인": "news:1", "유튜브 영상 목록": "yt:1",
                 "오늘 시장 시세 알려줘": "mkt", "리서치 판정 보여줘": "rs", "메뉴": "home",
                 "DEMO_US 재무 보여줘": "fin", "페퍼 점수 조회": "pep"}
        for text, key in cases.items():
            self.assertEqual(views.match_view(text), key, text)

    def test_questions_go_to_chat(self):
        for text in ("NVDA 적정가가 얼마야?", "금리가 오르면 성장주는 왜 떨어져?", "안녕",
                     "포트폴리오를 어떻게 분산하면 좋을지 자세하게 설명해 주세요 부탁드립니다 정말로요 감사합니다"):
            self.assertIsNone(views.match_view(text), text)


if __name__ == "__main__":
    unittest.main()
