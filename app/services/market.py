import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

@lru_cache(maxsize=2000)
def fetch_market_data_cached(ticker: str, start_date: str, end_date: str):
    return fetch_market_data(ticker, start_date, end_date)

@lru_cache(maxsize=500)
def fetch_intraday_data_cached(ticker: str, date: str, interval: str = "5m"):
    """
    분봉 데이터 캐싱 (5분봉: 최근 60일, 1분봉: 최근 7일)
    
    Args:
        ticker: 종목 코드
        date: 날짜 (YYYY-MM-DD)
        interval: "1m" 또는 "5m"
    
    Returns:
        DataFrame 또는 None
    """
    try:
        trade_date = pd.to_datetime(date)
        
        # yfinance 제한: 1분봉은 최근 7일, 5분봉은 최근 60일
        if interval == "1m":
            max_lookback = 7
        elif interval == "5m":
            max_lookback = 60
        else:
            return None
        
        # 최근 데이터인지 확인
        days_ago = (pd.Timestamp.now() - trade_date).days
        if days_ago > max_lookback:
            return None  # 너무 오래된 데이터는 분봉 불가
        
        # 분봉 데이터 다운로드
        start_date = trade_date.strftime("%Y-%m-%d")
        end_date = (trade_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        df = yf.download(
            ticker, 
            start=start_date, 
            end=end_date, 
            interval=interval,
            progress=False
        )
        
        if df.empty:
            # 한국 주식 시도
            if ticker.isdigit():
                df = yf.download(
                    f"{ticker}.KS", 
                    start=start_date, 
                    end=end_date, 
                    interval=interval,
                    progress=False
                )
                if df.empty:
                    df = yf.download(
                        f"{ticker}.KQ", 
                        start=start_date, 
                        end=end_date, 
                        interval=interval,
                        progress=False
                    )
        
        if df.empty:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        return df
        
    except Exception as e:
        print(f"Error fetching intraday data for {ticker} on {date}: {e}")
        return None

def calculate_mae_mfe_daily(
    entry_dt_full: pd.Timestamp,
    exit_dt_full: pd.Timestamp,
    entry_price: float,
    day_df: pd.DataFrame,
    adjust_func
) -> tuple[float, float]:
    """
    일봉 데이터 기반 MAE/MFE 계산 (기존 로직, fallback용)
    """
    try:
        entry_date = entry_dt_full.normalize()
        exit_date = exit_dt_full.normalize()
        
        if entry_date not in day_df.index:
            indexer = day_df.index.get_indexer([entry_date], method='nearest')
            if len(indexer) > 0 and indexer[0] != -1:
                entry_date = day_df.index[indexer[0]]
        
        if exit_date not in day_df.index:
            indexer = day_df.index.get_indexer([exit_date], method='nearest')
            if len(indexer) > 0 and indexer[0] != -1:
                exit_date = day_df.index[indexer[0]]
        
        holding_data = day_df.loc[entry_date:exit_date]
        
        min_low_raw = holding_data['Low'].min() if not holding_data.empty else day_df.loc[entry_date]['Low']
        min_low_adj = adjust_func(min_low_raw)
        mae = (min_low_adj - entry_price) / entry_price
        
        max_high_raw = holding_data['High'].max() if not holding_data.empty else day_df.loc[entry_date]['High']
        max_high_adj = adjust_func(max_high_raw)
        mfe = (max_high_adj - entry_price) / entry_price
        
        return (mae, mfe)
    except:
        return (0.0, 0.0)

def calculate_mae_mfe_intraday(
    entry_dt_full: pd.Timestamp,
    exit_dt_full: pd.Timestamp,
    entry_price: float,
    exit_price: float,
    ticker: str,
    day_df: pd.DataFrame,
    adjust_func
) -> tuple[float, float]:
    """
    분봉 데이터를 사용한 정밀 MAE/MFE 계산
    
    Args:
        entry_dt_full: 진입 시간 (시간 포함)
        exit_dt_full: 청산 시간 (시간 포함)
        entry_price: 진입 가격
        exit_price: 청산 가격
        ticker: 종목 코드
        day_df: 일봉 데이터 (fallback용)
        adjust_func: 액면분할 보정 함수
    
    Returns:
        tuple: (mae, mfe) - 실패 시 일봉 기반 값 반환
    """
    try:
        entry_date_str = entry_dt_full.strftime("%Y-%m-%d")
        exit_date_str = exit_dt_full.strftime("%Y-%m-%d")
        
        # 5분봉 데이터 시도 (더 긴 기간 지원)
        intraday_df = fetch_intraday_data_cached(ticker, entry_date_str, "5m")
        
        if intraday_df is None or intraday_df.empty:
            # Fallback: 일봉 데이터 사용
            return calculate_mae_mfe_daily(entry_dt_full, exit_dt_full, entry_price, day_df, adjust_func)
        
        # 진입 시간과 청산 시간 사이의 분봉 데이터 필터링
        entry_time = entry_dt_full
        exit_time = exit_dt_full
        
        # 같은 날짜인 경우
        if entry_date_str == exit_date_str:
            mask = (intraday_df.index >= entry_time) & (intraday_df.index <= exit_time)
            holding_data = intraday_df[mask]
        else:
            # 다른 날짜: 진입일 이후 + 청산일 이전 데이터
            # 진입일 데이터
            entry_day_data = intraday_df[intraday_df.index.date == entry_dt_full.date()]
            entry_mask = entry_day_data.index >= entry_time
            
            # 청산일 데이터
            exit_intraday_df = fetch_intraday_data_cached(ticker, exit_date_str, "5m")
            if exit_intraday_df is not None and not exit_intraday_df.empty:
                exit_day_data = exit_intraday_df[exit_intraday_df.index.date == exit_dt_full.date()]
                exit_mask = exit_day_data.index <= exit_time
                
                holding_data_list = []
                if not entry_day_data[entry_mask].empty:
                    holding_data_list.append(entry_day_data[entry_mask])
                if not exit_day_data[exit_mask].empty:
                    holding_data_list.append(exit_day_data[exit_mask])
                
                if holding_data_list:
                    holding_data = pd.concat(holding_data_list)
                else:
                    holding_data = pd.DataFrame()
            else:
                # 청산일 분봉 데이터가 없으면 진입일만 사용
                holding_data = entry_day_data[entry_mask] if not entry_day_data[entry_mask].empty else pd.DataFrame()
        
        if holding_data.empty:
            # Fallback: 일봉 데이터 사용
            return calculate_mae_mfe_daily(entry_dt_full, exit_dt_full, entry_price, day_df, adjust_func)
        
        # MAE/MFE 계산
        min_low = holding_data['Low'].min()
        max_high = holding_data['High'].max()
        
        min_low_adj = adjust_func(min_low)
        max_high_adj = adjust_func(max_high)
        
        mae = (min_low_adj - entry_price) / entry_price
        mfe = (max_high_adj - entry_price) / entry_price
        
        return (mae, mfe)
        
    except Exception as e:
        print(f"Error calculating intraday MAE/MFE: {e}")
        # Fallback: 일봉 데이터 사용
        return calculate_mae_mfe_daily(entry_dt_full, exit_dt_full, entry_price, day_df, adjust_func)

def calculate_volume_weight(current_volume: float, avg_volume: float) -> float:
    """
    Volume Weight 계산 공식 (MVP 안전성 우선)
    
    Args:
        current_volume: 현재 거래 시점의 거래량
        avg_volume: 20일 이동평균 거래량
    
    Returns:
        volume_weight: 1.0, 1.2, 또는 1.5
    """
    if avg_volume <= 0:
        return 1.0  # 안전장치: 평균 거래량이 없으면 가중치 없음
    
    volume_ratio = current_volume / avg_volume
    
    if volume_ratio < 1.0:
        return 1.0  # 평소보다 낮은 거래량
    elif volume_ratio < 2.5:
        return 1.0  # 일반적인 거래량
    elif volume_ratio < 5.0:
        return 1.2  # 경고 구간: 거래량 스파이크
    else:
        return 1.5  # 극단적 구간: 심각한 투매/FOMO

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
        
        # 1. FOMO Score BASE (개선: 매수 시간까지의 범위 사용)
        ticker = str(row['ticker'])
        entry_date_str = entry_dt_full.strftime("%Y-%m-%d")
        
        # 일봉 데이터 기본값 (항상 정의)
        entry_high_adj = adjust(entry_day['High'])
        entry_low_adj = adjust(entry_day['Low'])
        
        # 분봉 데이터로 매수 시간까지의 고가/저가 확인
        intraday_df = fetch_intraday_data_cached(ticker, entry_date_str, "5m")
        
        if intraday_df is not None and not intraday_df.empty:
            # 매수 시간까지의 분봉 데이터
            entry_time_mask = intraday_df.index <= entry_dt_full
            pre_entry_data = intraday_df[entry_time_mask]
            
            if not pre_entry_data.empty:
                # 매수 시간까지의 실제 고가/저가
                range_high = pre_entry_data['High'].max()
                range_low = pre_entry_data['Low'].min()
                
                range_high_adj = adjust(range_high)
                range_low_adj = adjust(range_low)
                day_range = range_high_adj - range_low_adj
            else:
                # 분봉 데이터가 없으면 일봉 사용
                day_range = entry_high_adj - entry_low_adj
                range_low_adj = entry_low_adj
        else:
            # 분봉 데이터 없으면 일봉 사용
            day_range = entry_high_adj - entry_low_adj
            range_low_adj = entry_low_adj
        
        fomo_score_base = 0.5
        if day_range > 0:
            fomo_score_base = (user_price - range_low_adj) / day_range
        
        fomo_score_base = max(0.0, min(1.0, fomo_score_base))

        # Volume Weight 계산 (진입 시점)
        volume_weight_entry = 1.0
        try:
            past_data_entry = df.loc[:entry_date]
            if len(past_data_entry) >= 20:
                avg_vol_entry = past_data_entry['Volume'].rolling(window=20).mean().iloc[-1]
                current_vol_entry = float(entry_day['Volume'])
                if avg_vol_entry > 0:
                    volume_weight_entry = calculate_volume_weight(current_vol_entry, avg_vol_entry)
        except Exception as e:
            pass

        # Contextual FOMO (거래량 가중치 적용 - 하위 호환성 유지)
        fomo_score = fomo_score_base
        if volume_weight_entry > 1.0 and fomo_score_base > 0.7:
            fomo_score = min(1.0, fomo_score_base * volume_weight_entry)

        # 2. Panic Score BASE (가중치 적용 전 순수 점수)
        exit_high_adj = adjust(exit_day['High'])
        exit_low_adj = adjust(exit_day['Low'])
        user_exit_price = float(row['exit_price'])
        
        exit_range = exit_high_adj - exit_low_adj
        panic_score_base = 0.5
        if exit_range > 0:
            panic_score_base = (user_exit_price - exit_low_adj) / exit_range
        
        panic_score_base = max(0.0, min(1.0, panic_score_base))

        # Volume Weight 계산 (청산 시점)
        volume_weight_exit = 1.0
        try:
            past_data_exit = df.loc[:exit_date]
            if len(past_data_exit) >= 20:
                avg_vol_exit = past_data_exit['Volume'].rolling(window=20).mean().iloc[-1]
                current_vol_exit = float(exit_day['Volume'])
                if avg_vol_exit > 0:
                    volume_weight_exit = calculate_volume_weight(current_vol_exit, avg_vol_exit)
        except Exception as e:
            pass

        # Contextual Panic (거래량 가중치 적용 - 하위 호환성 유지)
        panic_score = panic_score_base
        if volume_weight_exit > 1.0 and panic_score_base < 0.3:
            # 0.8 = 2.0 - 1.2 (volume_weight 1.2일 때 panic_score를 0.8배로 감소)
            panic_score = max(0.0, panic_score_base * (2.0 - volume_weight_exit))
            
        # 3. MAE / MFE (개선: 분봉 데이터 사용)
        mae, mfe = calculate_mae_mfe_intraday(
            entry_dt_full,
            exit_dt_full,
            user_price,
            user_exit_price,
            ticker,
            df,
            adjust
        )
        
        # 4. Efficiency (분봉 기반 MFE 사용)
        # mfe는 이미 분봉 데이터로 계산됨
        max_potential = user_price * mfe  # mfe는 (max_high - entry_price) / entry_price
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
            "fomo_score_base": float(fomo_score_base),  # 분해용: 가중치 적용 전 순수 점수
            "panic_score_base": float(panic_score_base),  # 분해용: 가중치 적용 전 순수 점수
            "volume_weight_entry": float(volume_weight_entry),  # 분해용: 진입 시점 거래량 가중치
            "volume_weight_exit": float(volume_weight_exit),  # 분해용: 청산 시점 거래량 가중치
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
            "fomo_score": -1.0, "panic_score": -1.0, 
            "fomo_score_base": -1.0, "panic_score_base": -1.0,
            "volume_weight_entry": 1.0, "volume_weight_exit": 1.0,
            "mae": 0.0, "mfe": 0.0,
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