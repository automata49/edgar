from playwright.async_api import async_playwright
import asyncio

async def capture_finviz_heatmap():
    """Finviz S&P 500 섹터 히트맵 캡처"""
    browser = None
    try:
        async with async_playwright() as p:
            # 브라우저 시작 (타임아웃 60초)
            browser = await p.chromium.launch(
                headless=True,
                timeout=60000
            )
            
            # 페이지 생성
            page = await browser.new_page(
                viewport={'width': 1920, 'height': 1080}
            )
            
            # 페이지 로드 (타임아웃 30초)
            await page.goto(
                'https://finviz.com/map.ashx?t=sec',
                wait_until='networkidle',
                timeout=30000
            )
            
            # 히트맵 로딩 대기 (5초)
            await asyncio.sleep(5)
            
            # 스크린샷
            screenshot_path = '/tmp/finviz_heatmap.png'
            await page.screenshot(
                path=screenshot_path,
                full_page=False
            )
            
            # 브라우저 종료
            await browser.close()
            
            return screenshot_path
            
    except asyncio.TimeoutError:
        print("   ⚠️  Finviz 타임아웃 (30초 초과)")
        if browser:
            await browser.close()
        return None
    except Exception as e:
        print(f"   ⚠️  Finviz 캡처 에러: {str(e)[:100]}")
        if browser:
            try:
                await browser.close()
            except:
                pass
        return None
