"""네이버 종목분석 리포트 파이프라인: 수집 → 리포트별 요약 → 종목별 DB 저장."""
from __future__ import annotations

import asyncio
import time

from database.client import research_row, summary_failed
from kstock_signal.analyzers.report_summarizer import ReportSummarizer
from kstock_signal.collectors.naver_report import NaverReportCollector


class ResearchPipeline:
    def __init__(self, config: dict, router, db=None) -> None:
        self.collector  = NaverReportCollector(config)
        self.summarizer = ReportSummarizer(router, config)
        self.db = db
        self.retry_wait = 20

    async def run(self) -> list[dict]:
        """새 리포트를 요약해 저장하고, 저장한 행(research_reports 형식) 목록을 돌려줍니다."""
        reports = await self.collector.collect(self.db.known_report_ids if self.db else None)
        return await asyncio.to_thread(self.process, reports)

    def process(self, reports: list[dict]) -> list[dict]:
        summaries = []
        for i, rpt in enumerate(reports, 1):
            print(f"   📝 [{i}/{len(reports)}] {rpt.get('stock_name')} · {rpt.get('firm')} 요약 중...")
            summaries.append(self.summarizer.summarize(rpt))
        # Gemini 과부하(503) 등으로 실패한 건은 잠시 뒤 한 번 더 시도. 그래도 실패하면 다음 실행 때 다시 시도됩니다.
        retry = [i for i, s in enumerate(summaries) if needs_retry(s)]
        if retry:
            print(f"   ⏳ 요약 실패 {len(retry)}건 — {self.retry_wait}초 후 재시도")
            time.sleep(self.retry_wait)
            for i in retry:
                summaries[i] = self.summarizer.summarize(reports[i])
        rows = [research_row(rpt, s) for rpt, s in zip(reports, summaries)]
        if self.db and rows:
            try:
                n = self.db.save_research_reports(rows)
                print(f"💾 리서치 리포트 {n}건 저장")
            except Exception as e:  # noqa: BLE001 — DB 실패해도 리포트 발송은 계속
                print(f"   ⚠️  리서치 리포트 저장 실패: {e}")
        return rows


def needs_retry(summary: dict) -> bool:
    """모델 호출 실패로 최소 요약만 된 경우."""
    return summary_failed({"summary_model": summary.get("model"), "summary": summary})
