import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

@lru_cache(maxsize=2000)
def fetch_market_data_cached(ticker: str, start_date: str, end_date: str):
    return fetch_market_data(ticker, start_date, end_date)

def fetch_market_data(ticker: str, start_date: str, end_date: str):
    try:
        # [시간 기능 추가] 입력이 'YYYY-MM-DD HH:MM:SS'여도 날짜만 추출해서 API 요청
        start_dt = pd.to_datetime(start_date).normalize()
        end_dt = pd.to_datetime(end_date).normalize()
        
        # 20일 이평선 및 거래량 분석을 위해 40일 전 데이터부터 확보
        buffer_start = (start_dt - timedelta(days=40)).strftime("%Y-%m-%d")
        buffer_end = (end_dt + timedelta(days=10)).strftime("%Y-%m-%d")
        
        # auto_adjust=False 유지 (액면분할 보정은 calculate_metrics에서 수행)
        df = yf.download(ticker, start=buffer_start, end=buffer_end, progress=False, auto_adjust=False)
        
        if df.empty:
            if ticker.isdigit():
                df = yf.download(f"{ticker}.KS", start=buffer_start, end=buffer_end, progress=False, auto_adjust=False)
                if df.empty:
                    df = yf.download(f"{ticker}.KQ", start=buffer_start, end=buffer_end, progress=False, auto_adjust=False)
        
        if df.empty:
            return None
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def calculate_metrics(row, df):
    try:
        # [시간 기능 추가] 시간 정보를 포함한 Timestamp 생성
        entry_dt_full = pd.Timestamp(row['entry_date'])
        exit_dt_full = pd.Timestamp(row['exit_date'])
        
        # [시간 기능 추가] 시장 데이터(일봉) 매칭을 위해 시간 제거 (00:00:00으로 정규화)
        entry_date = entry_dt_full.normalize()
        exit_date = exit_dt_full.normalize()
        
        # --- 인덱스 찾기 로직 (주말/휴일 보정) ---
        if entry_date not in df.index:
            if not df.index.empty:
                indexer = df.index.get_indexer([entry_date], method='nearest')
                if len(indexer) > 0 and indexer[0] != -1:
                    entry_date = df.index[indexer[0]]
            
        if entry_date not in df.index:
             raise ValueError(f"Entry date {entry_date.date()} not found in market data")

        entry_day = df.loc[entry_date]
        
        # --- 액면분할(Stock Split) 자동 보정 로직 (기존 유지) ---
        market_high = float(entry_day['High'])
        user_price = float(row['entry_price'])
        
        split_ratio = 1.0
        if market_high > 0:
            ratio = user_price / market_high
            if ratio > 2.0 or ratio < 0.5:
                # 단순 비율 적용 (정수배가 아닐 수 있음)
                split_ratio = ratio
        
        def adjust(price):
            return price * split_ratio
        # ----------------------------------------------------

        if exit_date not in df.index:
            if not df.index.empty:
                indexer = df.index.get_indexer([exit_date], method='nearest')
                if len(indexer) > 0 and indexer[0] != -1:
                    exit_date = df.index[indexer[0]]
        
        if exit_date not in df.index:
             raise ValueError(f"Exit date {exit_date.date()} not found in market data")

        exit_day = df.loc[exit_date]
        holding_data = df.loc[entry_date:exit_date]
        
        # 1. FOMO Score (보정된 가격 사용)
        entry_high_adj = adjust(entry_day['High'])
        entry_low_adj = adjust(entry_day['Low'])
        
        day_range = entry_high_adj - entry_low_adj
        fomo_score = 0.5
        if day_range > 0:
            fomo_score = (user_price - entry_low_adj) / day_range
        
        fomo_score = max(0.0, min(1.0, fomo_score))

        # --- Contextual FOMO (거래량 가중치) ---
        try:
            past_data = df.loc[:entry_date]
            if len(past_data) >= 20:
                avg_vol = past_data['Volume'].rolling(window=20).mean().iloc[-1]
                current_vol = float(entry_day['Volume'])
                
                # 평소 거래량의 2.5배 이상 폭발 & 이미 고점 매수(0.7 이상)인 경우 가중 처벌
                if avg_vol > 0 and current_vol > (avg_vol * 2.5) and fomo_score > 0.7:
                    fomo_score = min(1.0, fomo_score * 1.2)
        except Exception as e:
            pass
        # ---------------------------------------

        # 2. Panic Score
        exit_high_adj = adjust(exit_day['High'])
        exit_low_adj = adjust(exit_day['Low'])
        user_exit_price = float(row['exit_price'])
        
        exit_range = exit_high_adj - exit_low_adj
        panic_score = 0.5
        if exit_range > 0:
            panic_score = (user_exit_price - exit_low_adj) / exit_range
        
        panic_score = max(0.0, min(1.0, panic_score))
            
        # 3. MAE / MFE
        min_low_raw = holding_data['Low'].min() if not holding_data.empty else entry_day['Low']
        min_low_adj = adjust(min_low_raw)
        mae = (min_low_adj - user_price) / user_price
        
        max_high_raw = holding_data['High'].max() if not holding_data.empty else entry_day['High']
        max_high_adj = adjust(max_high_raw)
        mfe = (max_high_adj - user_price) / user_price
        
        # 4. Efficiency
        max_potential = max_high_adj - user_price
        realized = user_exit_price - user_price
        efficiency = 0.0
        if max_potential > 0:
            efficiency = max(0.0, realized / max_potential)
            
        # 5. Regret
        try:
            next_3_idx = df.index.get_loc(exit_date) + 1
            post_exit_data = df.iloc[next_3_idx : next_3_idx + 3]
            regret_amount = 0.0
            if not post_exit_data.empty:
                post_max_raw = post_exit_data['High'].max()
                post_max_adj = adjust(post_max_raw)
                regret_amount = max(0, (post_max_adj - user_exit_price) * row['qty'])
        except:
            regret_amount = 0.0
            
        return {
            "fomo_score": float(fomo_score),
            "panic_score": float(panic_score),
            "mae": float(mae),
            "mfe": float(mfe),
            "efficiency": float(efficiency),
            "regret": float(regret_amount),
            "entry_day_high": float(entry_high_adj),
            "entry_day_low": float(entry_low_adj),
            "exit_day_high": float(exit_high_adj),
            "exit_day_low": float(exit_low_adj)
        }

    except Exception as e:
        # print(f"Metric calc error: {e}")
        return {
            "fomo_score": -1.0, "panic_score": -1.0, "mae": 0.0, "mfe": 0.0,
            "efficiency": 0.0, "regret": 0.0, 
            "entry_day_high": 0.0, "entry_day_low": 0.0,
            "exit_day_high": 0.0, "exit_day_low": 0.0
        }

def detect_market_regime(ticker: str, date: str, market_df) -> str:
    try:
        # [시간 기능 추가] 날짜만 추출하여 정규화
        trade_date = pd.to_datetime(date).normalize()
        
        spy_start = (trade_date - timedelta(days=30)).strftime("%Y-%m-%d")
        spy_end = (trade_date + timedelta(days=5)).strftime("%Y-%m-%d")
        
        spy_df = yf.download('SPY', start=spy_start, end=spy_end, progress=False)
        if spy_df.empty:
            return "UNKNOWN"
        
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        
        spy_df['MA20'] = spy_df['Close'].rolling(window=20, min_periods=1).mean()
        
        if trade_date not in spy_df.index:
            if not spy_df.index.empty:
                indexer = spy_df.index.get_indexer([trade_date], method='nearest')
                if len(indexer) > 0 and indexer[0] != -1:
                    trade_date = spy_df.index[indexer[0]]
        
        if trade_date not in spy_df.index:
            return "UNKNOWN"
        
        current_price = spy_df.loc[trade_date, 'Close']
        ma20 = spy_df.loc[trade_date, 'MA20']
        
        try:
            prev_5_idx = spy_df.index.get_indexer([trade_date], method='nearest')[0] - 5
            if prev_5_idx >= 0:
                prev_price = spy_df.iloc[prev_5_idx]['Close']
                price_change = (current_price - prev_price) / prev_price
                
                if current_price > ma20 and price_change > 0.02: return "BULL"
                elif current_price < ma20 and price_change < -0.02: return "BEAR"
                else: return "SIDEWAYS"
        except:
            pass
        
        if current_price > ma20 * 1.02: return "BULL"
        elif current_price < ma20 * 0.98: return "BEAR"
        else: return "SIDEWAYS"
            
    except Exception as e:
        return "UNKNOWN"