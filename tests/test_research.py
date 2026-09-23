from __future__ import annotations

import json
import sys
import unittest
import unittest.mock
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.client import research_row
from invest import views
from kstock_signal.analyzers.report_summarizer import (
    ReportSummarizer,
    fallback_summary,
    normalize,
    parse_json,
)
from kstock_signal.collectors.naver_report import (
    NaverReportCollector,
    parse_list_html,
    report_day,
)
from kstock_signal.reporters.research_text import daily_section, prompt_lines
from kstock_signal.weekly import WeeklyReport, market_changes, research_stats
from llm.router import LLMResult
from tests.test_views import assert_telegram_html

LIST_HTML = """
<table class="type_1"><tr><th>종목명</th></tr>
<tr>
 <td><a href="/item/main.naver?code=039490" class="stock_item">키움증권</a></td>
 <td><a href="company_read.naver?nid=90001&page=1">증시 호조로 서프라이즈 달성</a></td>
 <td>미래에셋증권</td>
 <td class="file"><a href="https://stock.pstatic.net/stock-research/company/1.pdf"><img></a></td>
 <td class="date">26.04.30</td><td>1234</td>
</tr>
<tr>
 <td><a href="/item/main.naver?code=005930">삼성전자</a></td>
 <td><a href="company_read.naver?nid=90002&page=1">1Q26 Conference call</a></td>
 <td>SK증권</td><td class="file"></td><td class="date">26.04.30</td><td>99</td>
</tr>
<tr><td colspan="6"></td></tr>
</table>
"""

REPORT_TEXT = "키움증권\n투자의견 매수로 상향, 목표주가 516,000원으로 상향\n현재주가(26/4/29) 423,500원"


class FakeRouter:
    def __init__(self, text: str | None = None, ok: bool = True):
        self.text, self.ok_, self.calls = text, ok, []

    def run(self, task, prompt, system=None, json_schema=None):
        self.calls.append({"task": task, "prompt": prompt, "schema": json_schema})
        if not self.ok_:
            return LLMResult(text="실패", task=task, tier="free", notes=["gemini-3.8-flash: 일시적 과부하"])
        return LLMResult(text=self.text, task=task, tier="free", provider="gemini", model="gemini-3.8-flash")


MODEL_JSON = json.dumps({
    "one_line": "실적 서프라이즈로 의견·목표가 상향", "sentiment": "긍정", "opinion": "매수",
    "opinion_change": "상향", "target_price": 516000, "target_change": "상향", "current_price": 423500,
    "key_points": ["1분기 지배주주순이익 4,764억원", "DPS 15,500원으로 상향", "주주환원 정책 발표 예정", "넘침"],
    "risks": ["개인 거래대금 점유율 하락"], "numbers": [{"label": "1Q 순이익", "value": "4,764억원"}, {"x": 1}],
}, ensure_ascii=False)


def row(stock="키움증권", code="039490", firm="미래에셋증권", target=516000, change="상향", sentiment="긍정",
        day="2026-04-30", one="의견 상향"):
    return {"stock_name": stock, "stock_code": code, "firm": firm, "title": "제목", "report_day": day,
            "opinion": "매수", "target_value": target, "target_change": change, "sentiment": sentiment,
            "summary": {"one_line": one, "key_points": ["포인트 <1>"], "risks": ["리스크"],
                        "numbers": [{"label": "순이익", "value": "4,764억원"}], "opinion_change": "상향"},
            "pdf_url": "https://x/1.pdf?a=1&b=2"}


class CollectorTest(unittest.TestCase):
    def test_parse_list_extracts_code_id_pdf(self):
        rows = parse_list_html(LIST_HTML)
        self.assertEqual([(r.stock_name, r.stock_code, r.report_id) for r in rows],
                         [("키움증권", "039490", "90001"), ("삼성전자", "005930", "90002")])
        self.assertTrue(rows[0].pdf_url.endswith("1.pdf"))
        self.assertEqual(rows[1].pdf_url, "")

    def test_report_day(self):
        self.assertEqual(report_day("26.04.30"), "2026-04-30")
        self.assertIsNone(report_day("2026-04-30"))

    def _collector(self, **cfg):
        c = NaverReportCollector({"naver_report": {"pages": 2, "max_reports": 10, "save_dir": None, **cfg}})
        c._fetch_list = lambda page: parse_list_html(LIST_HTML)          # 두 페이지가 같아도 중복 제거
        c._fetch_pdf_bytes = lambda url: b"%PDF-fake" if url else None
        c._parse_pdf_text = lambda b: REPORT_TEXT
        return c

    def test_fetch_new_skips_known_and_dedupes(self):
        c = self._collector()
        seen_ids = []

        def known(ids):
            seen_ids.extend(ids)
            return {"90002"}
        with unittest.mock.patch("time.sleep"):
            out = c.fetch_new(known)
        self.assertEqual(sorted(seen_ids), ["90001", "90002"])
        self.assertEqual([r["report_id"] for r in out], ["90001"])
        self.assertEqual(out[0]["text"], REPORT_TEXT)
        self.assertEqual(out[0]["report_day"], "2026-04-30")

    def test_target_filter_by_name_or_code(self):
        self.assertEqual([r.stock_name for r in self._collector(target_symbols=["005930"]).list_reports()], ["삼성전자"])
        self.assertEqual([r.stock_name for r in self._collector(target_symbols=["키움"]).list_reports()], ["키움증권"])

    def test_known_ids_failure_does_not_stop_collection(self):
        def broken(ids):
            raise RuntimeError("db down")
        with unittest.mock.patch("time.sleep"):
            self.assertEqual(len(self._collector().fetch_new(broken)), 2)


REPORT = {"stock_name": "키움증권", "stock_code": "039490", "firm": "미래에셋증권", "date": "26.04.30",
          "title": "증시 호조로 서프라이즈 달성", "text": REPORT_TEXT, "key_numbers": ["+15%"]}


class SummarizerTest(unittest.TestCase):
    report = REPORT

    def test_summary_uses_report_summary_task_with_schema(self):
        router = FakeRouter(MODEL_JSON)
        s = ReportSummarizer(router).summarize(self.report)
        self.assertEqual(router.calls[0]["task"], "report_summary")
        self.assertIsNotNone(router.calls[0]["schema"])
        self.assertIn(REPORT_TEXT, router.calls[0]["prompt"])
        self.assertEqual((s["target_price"], s["current_price"], s["target_change"]), (516000, 423500, "상향"))
        self.assertEqual(len(s["key_points"]), 3)
        self.assertEqual(s["numbers"], [{"label": "1Q 순이익", "value": "4,764억원"}])
        self.assertEqual((s["model"], s["status"]), ("gemini-3.8-flash", "ok"))

    def test_model_failure_falls_back_to_title_and_regex_target(self):
        s = ReportSummarizer(FakeRouter(ok=False)).summarize(self.report)
        self.assertEqual(s["one_line"], "증시 호조로 서프라이즈 달성")
        self.assertEqual(s["target_price"], 516000)
        self.assertIn("요약 실패", s["status"])

    def test_empty_text_skips_model(self):
        router = FakeRouter(MODEL_JSON)
        s = ReportSummarizer(router).summarize(dict(self.report, text=""))
        self.assertEqual(router.calls, [])
        self.assertIn("PDF 본문 없음", s["status"])

    def test_parse_and_normalize_edge_cases(self):
        self.assertEqual(parse_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(parse_json('앞말 {"a": 2} 뒷말'), {"a": 2})
        with self.assertRaises(ValueError):
            parse_json("없음")
        n = normalize({"target_price": "9만", "sentiment": "좋음", "target_change": "?", "current_price": 0}, None)
        self.assertEqual((n["sentiment"], n["target_change"], n["current_price"]), ("중립", "미확인", None))
        self.assertIsNone(fallback_summary({"title": "t", "text": "목표가 없음"}, "x")["target_price"])


class RetryTest(unittest.TestCase):
    def test_failed_summary_retried_in_run_and_not_counted_as_known(self):
        from database.client import summary_failed
        from kstock_signal.research import ResearchPipeline

        class FlakyRouter(FakeRouter):
            def run(self, task, prompt, system=None, json_schema=None):
                self.ok_ = len(self.calls) >= 1          # 첫 호출만 실패
                return super().run(task, prompt, system, json_schema)

        pipe = ResearchPipeline({"naver_report": {}}, FlakyRouter(MODEL_JSON), None)
        pipe.retry_wait = 0
        rows = pipe.process([dict(REPORT, report_id="1")])
        self.assertEqual(rows[0]["summary_model"], "gemini-3.8-flash")
        failed = research_row(REPORT, fallback_summary(REPORT, "과부하"))
        self.assertTrue(summary_failed(failed))
        no_pdf = research_row(REPORT, fallback_summary(REPORT, "PDF 본문 없음"))
        self.assertFalse(summary_failed(no_pdf))
        self.assertFalse(summary_failed(rows[0]))


class RowAndTextTest(unittest.TestCase):
    def test_research_row_maps_summary(self):
        report = dict(REPORT, report_id="90001", report_day="2026-04-30", pdf_url="u")
        r = research_row(report, normalize(json.loads(MODEL_JSON), "gemini-3.8-flash"))
        self.assertEqual((r["report_id"], r["stock_code"], r["target_value"], r["target_price"]),
                         ("90001", "039490", 516000, "516,000원"))
        self.assertEqual(r["summary"]["one_line"], "실적 서프라이즈로 의견·목표가 상향")
        self.assertEqual(r["summary_model"], "gemini-3.8-flash")

    def test_daily_section_groups_by_stock(self):
        text = daily_section([row(), row(firm="KB증권", target=520000), row("삼성전자", "005930", "SK증권", None,
                                                                               "미확인", "중립")])
        self.assertIn("오늘의 증권사 리포트 (3건 · 2종목)", text)
        self.assertIn("🟢 키움증권 (039490)", text)
        self.assertIn("KB증권 · 매수 · 목표 520,000원▲", text)
        self.assertIn("SK증권 · 매수", text)
        self.assertEqual(daily_section([]), "")
        self.assertIn("[키움증권 (039490)] 미래에셋증권", prompt_lines([row()]))


class WeeklyTest(unittest.TestCase):
    def test_market_changes_first_to_last(self):
        rows = [{"symbol": "SPX", "price": 100, "category": "indices"},
                {"symbol": "SPX", "price": 0, "category": "indices"},       # 0 가격은 무시
                {"symbol": "SPX", "price": 110, "category": "indices"},
                {"symbol": "XLK", "price": 50, "category": "sector_etf"}]
        m = market_changes(rows)
        self.assertEqual(m["SPX"]["change_pct"], 10.0)
        self.assertEqual(m["XLK"]["change_pct"], 0.0)

    def test_research_stats_counts(self):
        st = research_stats([row(), row(firm="KB", target=520000), row("삼성전자", "005930", change="하향",
                                                                         sentiment="부정")])
        self.assertEqual((st["total"], st["stocks"], st["target_up"], st["target_down"]), (3, 2, 2, 1))
        self.assertEqual(st["top"][0]["stock"], "키움증권 (039490)")
        self.assertEqual((st["top"][0]["target_min"], st["top"][0]["target_max"]), (516000, 520000))

    def test_build_with_fake_db(self):
        class DB:
            def market_since(self, since):
                return [{"symbol": "SPX", "price": 100, "category": "indices"},
                        {"symbol": "SPX", "price": 102, "category": "indices"}]

            def research_since(self, since):
                return [row(), row("삼성전자", "005930", change="하향")]

            def news_since(self, since):
                return [{"title": "기사", "source": "한국경제"}] * 3

            def reports_since(self, since, kind):
                return [{"action_plan": "현금 20% 유지"}]

        router = FakeRouter("🧭 이번 주 한눈에\n요약")
        out = WeeklyReport({}, router, DB()).build(datetime(2026, 9, 26, tzinfo=timezone.utc))
        self.assertEqual(router.calls[0]["task"], "weekly_review")
        data = json.loads(router.calls[0]["prompt"])
        self.assertEqual(data["시장_주간등락률"], {"SPX": 2.0})
        self.assertEqual(data["Daily_액션플랜"], ["현금 20% 유지"])
        self.assertIn("🗓 Weekly 리포트 (09/19 ~ 09/26)", out["text"])
        self.assertIn("🟢 SPX: 102.00 (+2.00%)", out["text"])
        self.assertNotIn("섹터", out["text"])
        self.assertIn("증권사 리포트 2건 · 2종목 · 목표가 상향 1 · 하향 1", out["text"])
        self.assertIn("한국경제: 3건", out["text"])
        self.assertIn("AI 주간 해설 (gemini-3.8-flash)", out["text"])

    def test_build_without_db_returns_none(self):
        self.assertIsNone(WeeklyReport({}, FakeRouter("x"), None).build())


class ResearchViewsTest(unittest.TestCase):
    def test_stock_list_and_detail_pages(self):
        stocks = [{"stock_name": "키움증권", "stock_code": "039490", "report_count": 3, "reports_30d": 2,
                   "last_report_day": "2026-04-30", "last_firm": "미래에셋증권", "last_opinion": "매수",
                   "last_target": 516000, "last_target_change": "상향", "last_sentiment": "긍정",
                   "last_one_line": "의견 <상향>"},
                  {"stock_name": "아주아주긴이름의한국종목주식회사입니다", "stock_code": None, "report_count": 1}]
        page = views.research_stocks(stocks)
        assert_telegram_html(self, page)
        self.assertIn("목표 516,000원▲", page.text)
        self.assertIn("의견 &lt;상향&gt;", page.text)
        self.assertEqual(page.buttons[0][0][1], "v:rr:039490")
        detail = views.research_reports([row(), row(firm="KB증권")], "039490")
        assert_telegram_html(self, detail)
        self.assertIn("매수(상향)", detail.text)
        self.assertIn("• 포인트 &lt;1&gt;", detail.text)
        self.assertIn("📊 순이익 4,764억원", detail.text)
        self.assertIn('href="https://x/1.pdf?a=1&amp;b=2"', detail.text)
        assert_telegram_html(self, views.research_reports([], "없는종목"))
        assert_telegram_html(self, views.weekly({"created_at": "2026-09-26T00:00", "analysis": "주간 <요약>"}))

    def test_match_view_research_and_weekly(self):
        self.assertEqual(views.match_view("증권사 리포트 보여줘"), "rr")
        self.assertEqual(views.match_view("삼성전자 리서치 리포트 알려줘"), "rr")
        self.assertEqual(views.match_view("주간 리포트 보여줘"), "wk")
        self.assertEqual(views.match_view("최근 리포트 보여줘"), "rpt")

    def test_stock_from_text(self):
        from telegram_bot.handlers.browse import _stock_from_text
        self.assertEqual(_stock_from_text("삼성전자 증권사 리포트 보여줘"), "삼성전자")
        self.assertEqual(_stock_from_text("키움증권의 리서치 리포트 알려줘"), "키움증권")
        self.assertIsNone(_stock_from_text("증권사 리포트 보여줘"))


if __name__ == "__main__":
    unittest.main()
