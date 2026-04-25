import yfinance as yf
import requests

class MarketDataCollector:
    """시장 데이터 수집 (확장된 종목 리스트)"""
    
    def __init__(self, config):
        self.config = config
        
        # 모니터링 종목 (카테고리별)
        self.symbols = {
            # 주요 지수
            'indices': {
                'SPX': '^GSPC',      # S&P 500
                'NASDAQ': '^IXIC',   # NASDAQ
                'DOW': '^DJI',       # Dow Jones
                'RUSSELL': '^RUT',   # Russell 2000
                'KOSPI': '^KS11',    # KOSPI
                'KOSDAQ': '^KQ11',   # KOSDAQ
            },
            
            # 채권/금리
            'bonds': {
                'US10Y': '^TNX',     # 10년물
                'US30Y': '^TYX',     # 30년물
                'TLT': 'TLT',        # 20년 국채 ETF
                'HYG': 'HYG',        # 하이일드 채권
            },
            
            # 원자재/통화
            'commodities': {
                'OIL': 'CL=F',       # WTI
                'GOLD': 'GC=F',      # 금 선물
                'DXY': 'DX-Y.NYB',   # 달러 인덱스
            },
            
            # 암호화폐
            'crypto': {
                'BTC': 'BTC-USD',
                'ETH': 'ETH-USD',
                'SOL': 'SOL-USD',
                'XRP': 'XRP-USD',
            },
            
            # 섹터 ETF
            'sector_etf': {
                'SOXX': 'SOXX',      # 반도체
                'SMH': 'SMH',        # 반도체 홀더스
                'SOXL': 'SOXL',      # 3배 레버리지 반도체
                'XLK': 'XLK',        # 기술
                'XLF': 'XLF',        # 금융
                'XLE': 'XLE',        # 에너지
                'XLV': 'XLV',        # 헬스케어
                'XLY': 'XLY',        # 경기소비재
                'XLP': 'XLP',        # 필수소비재
                'XLI': 'XLI',        # 산업재
                'XLB': 'XLB',        # 소재
                'XBI': 'XBI',        # 바이오
                'ITB': 'ITB',        # 주택건설
                'XHB': 'XHB',        # 주택건설
                'IYR': 'IYR',        # 부동산
                'VNQ': 'VNQ',        # 부동산 (Vanguard)
                'KRE': 'KRE',        # 지역은행
                'XRT': 'XRT',        # 소매
            },
            
            # 스타일/시가총액 ETF
            'style_etf': {
                'SPY': 'SPY',        # S&P 500
                'QQQ': 'QQQ',        # NASDAQ 100
                'QQQM': 'QQQM',      # NASDAQ 100 (mini)
                'TQQQ': 'TQQQ',      # 3배 NASDAQ
                'DIA': 'DIA',        # Dow
                'IWM': 'IWM',        # Russell 2000 (소형주)
                'IWF': 'IWF',        # Russell 1000 Growth (대형 성장)
                'VUG': 'VUG',        # 대형 성장
                'IVW': 'IVW',        # S&P 500 성장
                'IWO': 'IWO',        # Russell 2000 성장 (소형 성장)
                'IJH': 'IJH',        # S&P 400 (중형주)
                'MDY': 'MDY',        # S&P 400 (중형주)
                'IJT': 'IJT',        # S&P 600 성장 (소형 성장)
                'RSP': 'RSP',        # S&P 500 동일가중
            },
            
            # 테마/특수 ETF
            'theme_etf': {
                'LIT': 'LIT',        # 리튬/배터리
                'XOP': 'XOP',        # 석유/가스 탐사
                'IGV': 'IGV',        # 소프트웨어
                'VEA': 'VEA',        # 선진국 (미국 제외)
                'EWY': 'EWY',        # 한국
                'INDA': 'INDA',      # 인도
                'IBIT': 'IBIT',      # 비트코인 ETF
            },
            
            # 변동성/배당
            'special': {
                'VIX': '^VIX',       # 변동성 지수
                'SCHD': 'SCHD',      # 배당 ETF
                'VIG': 'VIG',        # 배당성장 ETF
            }
        }
    
    def get_yahoo_data(self, symbol):
        """Yahoo Finance에서 데이터 수집"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 현재가
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
            
            # 전일종가
            prev_close = info.get('previousClose', price)
            
            # 변화량/변화율 계산
            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close else 0
            
            return {
                'price': round(price, 2),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'previous_close': round(prev_close, 2)
            }
        except Exception as e:
            print(f"   ⚠️  {symbol} 수집 실패: {str(e)[:50]}")
            return None
    
    def get_crypto_data_coingecko(self, crypto_id):
        """CoinGecko에서 암호화폐 데이터 수집"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': crypto_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if crypto_id in data:
                price = data[crypto_id]['usd']
                change_24h = data[crypto_id].get('usd_24h_change', 0)
                
                return {
                    'price': round(price, 2),
                    'change_percent': round(change_24h, 2)
                }
        except:
            pass
        
        return None
    
    def get_all_market_data(self):
        """모든 시장 데이터 수집"""
        print("📊 실시간 시장 데이터 수집 중...")
        
        all_data = {}
        total_count = 0
        success_count = 0
        
        # 카테고리별 수집
        for category, symbols in self.symbols.items():
            for name, symbol in symbols.items():
                total_count += 1
                
                # 암호화폐는 CoinGecko 우선 시도
                if category == 'crypto':
                    crypto_ids = {
                        'BTC': 'bitcoin',
                        'ETH': 'ethereum',
                        'SOL': 'solana',
                        'XRP': 'ripple'
                    }
                    
                    data = self.get_crypto_data_coingecko(crypto_ids.get(name))
                    if not data:
                        data = self.get_yahoo_data(symbol)
                else:
                    data = self.get_yahoo_data(symbol)
                
                if data:
                    all_data[name] = data
                    success_count += 1
        
        print(f"✅ 시장 데이터: {success_count}/{total_count}개 수집 완료\n")
        
        return all_data
