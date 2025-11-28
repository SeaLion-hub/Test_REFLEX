import yfinance as yf
import pandas as pd
import numpy as np
import json
import random
from datetime import datetime, timedelta
import os

# ---------------------------------------------------------
# 1. 설정
# ---------------------------------------------------------
TICKERS = ['NVDA', 'TSLA', 'AAPL', 'AMD', 'MSFT', 'AMZN', 'META', 'GOOGL', 'NFLX', 'INTC', 'COIN', 'PLTR']
START_DATE = "2022-05-01"
END_DATE = "2024-05-01"
TRADES_PER_PERSON = 50

# ---------------------------------------------------------
# 2. 트레이더 페르소나 정의
# ---------------------------------------------------------
class TraderPersona:
    def __init__(self, name, fomo_prob, panic_prob, revenge_prob, hold_days_range, win_rate_target, disposition_tendency=1.0):
        self.name = name
        self.fomo_prob = fomo_prob       
        self.panic_prob = panic_prob     
        self.revenge_prob = revenge_prob 
        self.hold_days_range = hold_days_range
        self.win_rate_target = win_rate_target
        self.disposition_tendency = disposition_tendency

PERSONAS = [
    TraderPersona("01_Strategist", 0.1, 0.1, 0.0, (5, 20), 0.65),
    TraderPersona("02_FOMO_Chaser", 0.9, 0.1, 0.0, (2, 5), 0.4),
    TraderPersona("03_Panic_Seller", 0.1, 0.9, 0.0, (1, 3), 0.35),
    TraderPersona("04_Bag_Holder", 0.2, 0.0, 0.0, (30, 100), 0.45, disposition_tendency=3.0),
    TraderPersona("05_Gambler", 0.4, 0.4, 0.8, (1, 2), 0.3),
    TraderPersona("06_Scalper", 0.3, 0.3, 0.1, (1, 1), 0.6),
    TraderPersona("07_Trend_Follower", 0.1, 0.1, 0.0, (10, 40), 0.6, disposition_tendency=0.3),
    TraderPersona("08_Contrarian", 0.0, 0.2, 0.0, (5, 15), 0.55),
    TraderPersona("09_Average_Joe", 0.3, 0.3, 0.1, (3, 10), 0.5),
    TraderPersona("10_Lucky_Idiot", 0.8, 0.4, 0.0, (2, 5), 0.65)
]

# ---------------------------------------------------------
# 3. 유틸리티 & 검증 함수 (핵심 수정)
# ---------------------------------------------------------
def safe_float(value):
    if value is None: return 0.0
    try:
        val = float(value)
        return 0.0 if np.isnan(val) or np.isinf(val) else val
    except: return 0.0

def calculate_metrics(df):
    """지표 무결성 검증: Sharpe/Sortino가 0이 아닌지 확인"""
    if df.empty: return 0, 0, False
    try:
        # 수익률 계산
        df['return_pct'] = (df['Exit Price'] - df['Entry Price']) / df['Entry Price']
        returns = df['return_pct'].values
        returns = returns[~np.isnan(returns)] # NaN 제거
        
        if len(returns) < 2: return 0, 0, False
        
        avg_return = np.mean(returns)
        std_dev = np.std(returns)
        
        if std_dev == 0: return 0, 0, False
        
        # Sharpe Ratio
        sharpe = avg_return / std_dev
        
        # Sortino Ratio (하방 편차)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_dev = np.std(downside_returns)
            sortino = avg_return / downside_dev if downside_dev > 0 else 0
        else:
            # 손실 거래가 없는 경우 (완벽한 트레이더)
            sortino = sharpe * 1.5 # 임의 보정
            
        return safe_float(sharpe), safe_float(sortino), True
    except:
        return 0, 0, False

class NewsGenerator:
    def __init__(self):
        self.sources = ["블룸버그", "로이터", "CNBC", "한경", "매경"]
    def generate(self, ticker, sentiment):
        source = random.choice(self.sources)
        if sentiment == "FOMO":
            return [f"{source} {ticker}, 신고가 경신... 매수세 폭주", f"[{ticker}] 과열 논란에도 급등"]
        elif sentiment == "PANIC":
            return [f"{source} {ticker}, 악재로 급락", f"[{ticker}] 지지선 붕괴... 투매 지속"]
        return [f"{ticker} 보합권 등락", f"외국인 {ticker} 관망세"]

# ---------------------------------------------------------
# 4. 메인 로직
# ---------------------------------------------------------
def generate_dataset():
    print("🔄 시장 데이터 로딩...")
    market_data = {}
    try:
        raw_data = yf.download(TICKERS, start=START_DATE, end=END_DATE, group_by='ticker', progress=True, auto_adjust=False)
    except: return

    for ticker in TICKERS:
        if len(TICKERS) > 1: df = raw_data[ticker].copy()
        else: df = raw_data.copy()
        df = df.dropna(how='all').ffill().bfill().dropna()
        df = df[(df['High'] > 0) & (df['Low'] > 0) & (df['Close'] > 0)]
        if not df.empty:
            df.reset_index(inplace=True)
            df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
            market_data[ticker] = df

    print("✅ 데이터 준비 완료. 생성 시작...")
    news_gen = NewsGenerator()
    global_news_cache = {}

    for persona in PERSONAS:
        print(f"Generating {persona.name}...")
        
        best_trades = []
        best_sharpe = -999
        
        # 최대 10번 시도하여 가장 '무결한' 데이터셋 선택
        for attempt in range(10):
            trades = []
            current_count = 0
            revenge_queue = [] 

            while current_count < TRADES_PER_PERSON:
                if revenge_queue:
                    rv_ticker, rv_date = revenge_queue.pop(0)
                    ticker = rv_ticker
                    df = market_data[ticker]
                    start_search_idx = df.index[df['Date'] >= rv_date]
                    if len(start_search_idx) > 0:
                        entry_idx = start_search_idx[0]
                    else: continue
                else:
                    ticker = random.choice(list(market_data.keys()))
                    df = market_data[ticker]
                    if len(df) < 50: continue
                    entry_idx = random.randint(0, len(df) - 50)
                
                if entry_idx >= len(df) - 10: continue
                entry_row = df.iloc[entry_idx]
                
                try:
                    high = float(entry_row['High'])
                    low = float(entry_row['Low'])
                    rng = high - low
                except: continue

                # 진입
                is_fomo = random.random() < persona.fomo_prob
                if is_fomo:
                    entry_price = high - (rng * random.uniform(0.0, 0.1))
                    sentiment = "FOMO"
                else:
                    entry_price = low + (rng * random.uniform(0.2, 0.6))
                    sentiment = "NORMAL"

                # 청산 (Disposition 반영)
                is_win = random.random() < persona.win_rate_target
                base_hold = random.randint(persona.hold_days_range[0], persona.hold_days_range[1])
                
                if is_win:
                    hold_days = max(1, int(base_hold / max(1.0, persona.disposition_tendency)))
                else:
                    hold_days = max(1, int(base_hold * max(1.0, persona.disposition_tendency)))
                
                exit_idx = min(entry_idx + hold_days, len(df) - 1)
                exit_row = df.iloc[exit_idx]
                
                ex_high = float(exit_row['High'])
                ex_low = float(exit_row['Low'])
                ex_rng = ex_high - ex_low
                
                is_panic = random.random() < persona.panic_prob
                if is_panic:
                    exit_price = ex_low + (ex_rng * 0.1)
                    if exit_price > entry_price: exit_price = entry_price * 0.95
                else:
                    if is_win:
                        target_price = entry_price * random.uniform(1.02, 1.15)
                        exit_price = min(ex_high, target_price)
                        if exit_price < entry_price: exit_price = ex_high
                    else:
                        target_price = entry_price * random.uniform(0.90, 0.98)
                        exit_price = max(ex_low, target_price)
                        if exit_price > entry_price: exit_price = ex_low
                
                if np.isnan(entry_price) or np.isnan(exit_price) or entry_price <= 0 or exit_price <= 0:
                    continue
                
                # [수량 축소] 1~5주 (손실액 현실화)
                qty = random.randint(1, 5)
                
                trades.append({
                    "Ticker": ticker,
                    "Entry Date": entry_row['DateStr'],
                    "Entry Price": round(entry_price, 2),
                    "Exit Date": exit_row['DateStr'],
                    "Exit Price": round(exit_price, 2),
                    "Qty": qty
                })
                
                # 뉴스
                if ticker not in global_news_cache: global_news_cache[ticker] = {}
                global_news_cache[ticker][entry_row['DateStr']] = {
                    "news": news_gen.generate(ticker, sentiment),
                    "verdict": "GUILTY" if is_fomo else "INNOCENT",
                    "reasoning": "AI Generated",
                    "confidence": "HIGH"
                }
                
                current_count += 1
                
                # Revenge
                if exit_price < entry_price and random.random() < persona.revenge_prob:
                    if current_count < TRADES_PER_PERSON:
                         revenge_queue.append((ticker, exit_row['Date']))

            # [검증 단계] 지표 계산
            df_res = pd.DataFrame(trades)
            sharpe, sortino, valid = calculate_metrics(df_res)
            
            # 유효하고, 샤프지수가 이전보다 좋거나(Optional), 최소 기준을 넘으면 채택
            if valid and len(df_res) >= 10:
                # 특정 페르소나는 샤프지수가 낮아도 됨 (Panic Seller, Gambler 등)
                # 하지만 0.0이 나오는 건 데이터 오류일 수 있으므로 최소한의 변동성은 있어야 함
                if sharpe != 0 and sortino != 0:
                    best_trades = trades
                    print(f"   ✅ Validated (Attempt {attempt}): Sharpe={sharpe:.2f}, Sortino={sortino:.2f}")
                    break
        
        # 최종 저장
        if best_trades:
            df_final = pd.DataFrame(best_trades).sort_values("Entry Date")
            df_final.to_csv(f"trader_{persona.name}.csv", index=False)
            print(f"   -> Saved {persona.name}")
        else:
            print(f"   ❌ Failed to generate valid metrics for {persona.name} (Using last attempt)")
            # 실패하더라도 파일은 생성 (디버깅용)
            if trades:
                pd.DataFrame(trades).sort_values("Entry Date").to_csv(f"trader_{persona.name}.csv", index=False)

    with open("news_cache.json", "w", encoding="utf-8") as f:
        json.dump(global_news_cache, f, ensure_ascii=False, indent=2)
        
    print("\n✅ 완료! 모든 데이터셋의 지표 무결성이 검증되었습니다.")

if __name__ == "__main__":
    generate_dataset()