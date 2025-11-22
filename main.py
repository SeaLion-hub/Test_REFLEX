from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from typing import List, Optional
from pydantic import BaseModel
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
import os
from openai import OpenAI
import json

app = FastAPI(title="Truth Pipeline Engine")

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    pass

# --- DATA MODELS ---
class TradePosition(BaseModel):
    ticker: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    qty: int = 1

class BehavioralMetrics(BaseModel):
    total_trades: int
    win_rate: float
    profit_factor: float
    fomo_score: float
    panic_score: float
    disposition_ratio: float
    revenge_trading_count: int
    truth_score: int
    # Advanced Performance Metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    alpha: float = 0.0
    luck_percentile: float = 50.0

class EnrichedTrade(BaseModel):
    id: str
    ticker: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    qty: int
    pnl: float
    return_pct: float
    duration_days: int
    
    # Context
    market_regime: str = "UNKNOWN"
    is_revenge: bool = False
    
    # Metrics
    fomo_score: float = -1.0
    panic_score: float = -1.0
    mae: float = 0.0
    mfe: float = 0.0
    efficiency: float = 0.0
    regret: float = 0.0
    
    # Market Data (Optional for debug)
    entry_day_high: float = 0.0
    entry_day_low: float = 0.0
    exit_day_high: float = 0.0
    exit_day_low: float = 0.0

# Perfect Edition Models
class PersonalBaseline(BaseModel):
    avg_fomo: float
    avg_panic: float
    avg_mae: float
    avg_disposition_ratio: float
    avg_revenge_count: float

class BiasLossMapping(BaseModel):
    fomo_loss: float
    panic_loss: float
    revenge_loss: float
    disposition_loss: float

class BiasPriority(BaseModel):
    bias: str  # 'FOMO' | 'Panic Sell' | 'Revenge Trading' | 'Disposition Effect'
    priority: int
    financial_loss: float
    frequency: float
    severity: float

class BehaviorShift(BaseModel):
    bias: str
    recent_value: float
    baseline_value: float
    change_percent: float
    trend: str  # 'IMPROVING' | 'WORSENING' | 'STABLE'

class EquityCurvePoint(BaseModel):
    date: str
    cumulative_pnl: float
    fomo_score: Optional[float] = None
    panic_score: Optional[float] = None
    is_revenge: bool
    ticker: str
    pnl: float

class AnalysisResponse(BaseModel):
    trades: List[EnrichedTrade]
    metrics: BehavioralMetrics
    is_low_sample: bool
    # Perfect Edition (Optional)
    personal_baseline: Optional[PersonalBaseline] = None
    bias_loss_mapping: Optional[BiasLossMapping] = None
    bias_priority: Optional[List[BiasPriority]] = None
    behavior_shift: Optional[List[BehaviorShift]] = None
    equity_curve: List[EquityCurvePoint] = []

class CoachRequest(BaseModel):
    trades: List[dict]
    metrics: dict
    is_low_sample: bool
    personal_baseline: Optional[dict] = None
    bias_loss_mapping: Optional[dict] = None
    bias_priority: Optional[List[dict]] = None
    behavior_shift: Optional[List[dict]] = None

# --- HELPER FUNCTIONS ---

@lru_cache(maxsize=1000)
def fetch_market_data_cached(ticker: str, start_date: str, end_date: str):
    """
    LRU Cache를 사용한 시장 데이터 가져오기
    캐시 키는 함수 파라미터로 자동 생성됩니다.
    """
    return fetch_market_data(ticker, start_date, end_date)

def fetch_market_data(ticker: str, start_date: str, end_date: str):
    """
    Fetches market data from yfinance.
    Buffers start_date by -5 days and end_date by +5 days to ensure coverage.
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        buffer_start = (start_dt - timedelta(days=10)).strftime("%Y-%m-%d")
        buffer_end = (end_dt + timedelta(days=10)).strftime("%Y-%m-%d")
        
        # yfinance download
        df = yf.download(ticker, start=buffer_start, end=buffer_end, progress=False)
        
        if df.empty:
            # Try adding .KS for Korean stocks if pure number
            if ticker.isdigit():
                df = yf.download(f"{ticker}.KS", start=buffer_start, end=buffer_end, progress=False)
        
        if df.empty:
            return None
            
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def calculate_metrics(row, df):
    """
    Calculates MAE, MFE, FOMO, Panic, Efficiency, Regret based on OHLC data
    """
    try:
        entry_date = pd.Timestamp(row['entry_date'])
        exit_date = pd.Timestamp(row['exit_date'])
        
        # Entry Day Data
        if entry_date not in df.index:
            # Find nearest prior date
            entry_date = df.index[df.index.get_indexer([entry_date], method='nearest')[0]]
            
        entry_day = df.loc[entry_date]
        
        # Exit Day Data
        if exit_date not in df.index:
            exit_date = df.index[df.index.get_indexer([exit_date], method='nearest')[0]]
            
        exit_day = df.loc[exit_date]
        
        # Holding Period Data
        holding_data = df.loc[entry_date:exit_date]
        
        # 1. FOMO Score (Entry Price vs Day Range)
        day_range = entry_day['High'] - entry_day['Low']
        fomo_score = 0.5 # Default
        if day_range > 0:
            fomo_score = (row['entry_price'] - entry_day['Low']) / day_range
            
        # 2. Panic Score (Exit Price vs Day Range)
        exit_range = exit_day['High'] - exit_day['Low']
        panic_score = 0.5 # Default
        if exit_range > 0:
            panic_score = (row['exit_price'] - exit_day['Low']) / exit_range
            
        # 3. MAE (Max Adverse Excursion) - Lowest Low during holding vs Entry
        min_low = holding_data['Low'].min()
        mae = (min_low - row['entry_price']) / row['entry_price']
        
        # 4. MFE (Max Favorable Excursion) - Highest High during holding vs Entry
        max_high = holding_data['High'].max()
        mfe = (max_high - row['entry_price']) / row['entry_price']
        
        # 5. Profit Efficiency (Realized PnL / Max Potential PnL)
        # Max Potential = (Max High - Entry) if Long
        max_potential = max_high - row['entry_price']
        realized = row['exit_price'] - row['entry_price']
        efficiency = 0.0
        if max_potential > 0:
            efficiency = max(0.0, realized / max_potential)
            
        # 6. Regret (Exit + 3 Days Max High vs Exit Price)
        # Look 3 days forward from exit
        try:
            next_3_idx = df.index.get_loc(exit_date) + 1
            post_exit_data = df.iloc[next_3_idx : next_3_idx + 3]
            if not post_exit_data.empty:
                post_max = post_exit_data['High'].max()
                regret_amount = max(0, (post_max - row['exit_price']) * row['qty'])
            else:
                regret_amount = 0.0
        except:
            regret_amount = 0.0
            
        return {
            "fomo_score": float(fomo_score),
            "panic_score": float(panic_score),
            "mae": float(mae),
            "mfe": float(mfe),
            "efficiency": float(efficiency),
            "regret": float(regret_amount),
            "entry_day_high": float(entry_day['High']),
            "entry_day_low": float(entry_day['Low']),
            "exit_day_high": float(exit_day['High']),
            "exit_day_low": float(exit_day['Low'])
        }

    except Exception as e:
        print(f"Metric calc error: {e}")
        return {
            "fomo_score": -1.0, "panic_score": -1.0, "mae": 0.0, "mfe": 0.0,
            "efficiency": 0.0, "regret": 0.0, 
            "entry_day_high": 0.0, "entry_day_low": 0.0,
            "exit_day_high": 0.0, "exit_day_low": 0.0
        }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_trades(file: UploadFile):
    # 1. Parse CSV
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
        # Normalize columns
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        
        # Validate Required Columns (Strict 6 Fields)
        required = {'ticker', 'entry_date', 'entry_price', 'exit_date', 'exit_price'}
        if not required.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required}")
            
        if 'qty' not in df.columns:
            df['qty'] = 1
            
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid CSV format")

    enriched_trades = []
    
    # 2. Process Each Trade
    for _, row in df.iterrows():
        ticker = str(row['ticker'])
        entry_date = str(row['entry_date'])
        exit_date = str(row['exit_date'])
        
        # Fetch Market Data (with caching)
        market_df = fetch_market_data_cached(ticker, entry_date, exit_date)
        
        metrics = {
            "fomo_score": -1.0, "panic_score": -1.0, "mae": 0.0, "mfe": 0.0,
            "efficiency": 0.0, "regret": 0.0, 
            "entry_day_high": 0.0, "entry_day_low": 0.0,
            "exit_day_high": 0.0, "exit_day_low": 0.0
        }
        
        if market_df is not None:
            metrics = calculate_metrics(row, market_df)
            
        # Basic Calc
        pnl = (row['exit_price'] - row['entry_price']) * row['qty']
        ret_pct = (row['exit_price'] - row['entry_price']) / row['entry_price']
        
        # Duration
        d1 = datetime.strptime(entry_date, "%Y-%m-%d")
        d2 = datetime.strptime(exit_date, "%Y-%m-%d")
        duration = (d2 - d1).days
        
        enriched_trades.append({
            "id": f"{ticker}-{entry_date}",
            "ticker": ticker,
            "entry_date": entry_date,
            "entry_price": row['entry_price'],
            "exit_date": exit_date,
            "exit_price": row['exit_price'],
            "qty": row['qty'],
            "pnl": pnl,
            "return_pct": ret_pct,
            "duration_days": duration,
            "market_regime": "UNKNOWN", # Placeholder for now
            "is_revenge": False, # Calculated later
            **metrics
        })
        
    # 3. Aggregate Metrics
    trades_df = pd.DataFrame(enriched_trades)
    
    # Revenge Trading Logic (Sort by time)
    trades_df['entry_dt'] = pd.to_datetime(trades_df['entry_date'])
    trades_df['exit_dt'] = pd.to_datetime(trades_df['exit_date'])
    trades_df = trades_df.sort_values('entry_dt')
    
    revenge_count = 0
    for i in range(1, len(trades_df)):
        curr = trades_df.iloc[i]
        # Check previous trades for same ticker within 24h loss
        prev_candidates = trades_df.iloc[:i]
        same_ticker = prev_candidates[prev_candidates['ticker'] == curr['ticker']]
        
        is_revenge = False
        for _, prev in same_ticker.iterrows():
            if prev['pnl'] < 0:
                # Check time diff
                prev_exit = pd.to_datetime(prev['exit_date'])
                curr_entry = pd.to_datetime(curr['entry_date'])
                if 0 <= (curr_entry - prev_exit).days <= 1:
                    is_revenge = True
                    break
        
        if is_revenge:
            trades_df.at[trades_df.index[i], 'is_revenge'] = True
            revenge_count += 1
            
    # Final Metrics
    total_trades = len(trades_df)
    winners = trades_df[trades_df['pnl'] > 0]
    losers = trades_df[trades_df['pnl'] <= 0]
    
    win_rate = len(winners) / total_trades if total_trades > 0 else 0
    avg_win = winners['pnl'].mean() if not winners.empty else 0
    avg_loss = abs(losers['pnl'].mean()) if not losers.empty else 0
    profit_factor = (avg_win * len(winners)) / (avg_loss * len(losers)) if avg_loss > 0 else 0
    
    # Behavioral Avgs (Exclude -1/Invalid)
    valid_fomo = trades_df[trades_df['fomo_score'] != -1]['fomo_score']
    fomo_index = valid_fomo.mean() if not valid_fomo.empty else 0
    
    valid_panic = trades_df[trades_df['panic_score'] != -1]['panic_score']
    # Panic Score in UI is "How close to bottom did I sell?". 0 = Sold Bottom (Bad), 1 = Sold Top (Good).
    # BUT Specification says: "Panic Sell Score (Exit Price 위치값: intraday 저가 대비 얼마나 공포 매도인지)"
    # If result is low (close to day low), it means panic. 
    # So we want to invert it for "Badness"? 
    # Let's keep raw 0-1 score: 0 means sold at Low.
    panic_index = valid_panic.mean() if not valid_panic.empty else 0
    
    # Disposition Ratio
    avg_win_hold = winners['duration_days'].mean() if not winners.empty else 0
    avg_loss_hold = losers['duration_days'].mean() if not losers.empty else 0
    disposition_ratio = avg_loss_hold / avg_win_hold if avg_win_hold > 0 else 0
    
    # Advanced Performance Metrics: Sharpe, Sortino, Alpha
    returns = trades_df['return_pct'].tolist()
    avg_return = np.mean(returns) if returns else 0.0
    
    # Sharpe Ratio: (Return - Risk Free Rate) / StdDev
    # Risk-free rate assumed to be 2% annual (0.02/252 daily)
    std_dev = np.std(returns) if len(returns) > 1 else 0.0
    sharpe_ratio = (avg_return - 0.02/252) / std_dev if std_dev > 0 else 0.0
    
    # Sortino Ratio: Return / Downside Deviation
    downside_returns = [r for r in returns if r < 0]
    downside_dev = np.sqrt(np.mean([r**2 for r in downside_returns])) if downside_returns else 0.0
    sortino_ratio = avg_return / downside_dev if downside_dev > 0 else 0.0
    
    # Alpha: Excess return vs Benchmark (SPY)
    # Fetch SPY data for the same period
    alpha = 0.0
    try:
        if len(trades_df) > 0:
            min_date = trades_df['entry_dt'].min()
            max_date = trades_df['exit_dt'].max()
            spy_start = (min_date - timedelta(days=10)).strftime("%Y-%m-%d")
            spy_end = (max_date + timedelta(days=10)).strftime("%Y-%m-%d")
            
            spy_df = yf.download('SPY', start=spy_start, end=spy_end, progress=False)
            if not spy_df.empty:
                if isinstance(spy_df.columns, pd.MultiIndex):
                    spy_df.columns = spy_df.columns.get_level_values(0)
                
                # Calculate SPY return for the same period
                spy_start_price = spy_df.iloc[0]['Close']
                spy_end_price = spy_df.iloc[-1]['Close']
                spy_return = (spy_end_price - spy_start_price) / spy_start_price
                
                # Alpha = Portfolio Return - Benchmark Return
                portfolio_return = avg_return * len(trades_df)  # Approximate total return
                alpha = portfolio_return - spy_return
    except Exception as e:
        print(f"Benchmark calculation error: {e}")
        alpha = avg_return  # Fallback to avg return
    
    # Monte Carlo Simulation (Luck Percentile)
    luck_percentile = 50.0
    is_low_sample = total_trades < 5
    if not is_low_sample and len(trades_df) > 0:
        simulations = 1000
        realized_total_pnl = trades_df['pnl'].sum()
        all_pnls = trades_df['pnl'].tolist()
        better_outcomes = 0
        
        np.random.seed(42)  # For reproducibility
        for _ in range(simulations):
            sim_total = sum(np.random.choice(all_pnls) for _ in range(total_trades))
            if sim_total > realized_total_pnl:
                better_outcomes += 1
        
        luck_percentile = (better_outcomes / simulations) * 100
    
    # Truth Score Calculation (Simple Version)
    base_score = 50
    base_score += (win_rate * 20)
    base_score -= (fomo_index * 20)
    # If panic index is low (sold near bottom), that's bad. So we want to penalize LOW panic index.
    # Let's say Panic Index 0.1 (Sold near low) -> Bad.
    # We subtract (1 - panic_index) * 20? -> If 0.1, subtract 0.9*20 = 18 points.
    base_score -= ((1 - panic_index) * 20) 
    base_score -= max(0, (disposition_ratio - 1) * 10)
    base_score -= (revenge_count * 5)
    if not is_low_sample:
        base_score += (sharpe_ratio * 5)  # Add Sharpe bonus
    else:
        base_score += 5  # Low sample bonus
    
    truth_score = int(max(0, min(100, base_score)))
    
    # --- PERFECT EDITION CALCULATIONS ---
    
    # 1. Personal Baseline (개인 기준선)
    personal_baseline = None
    if total_trades >= 3:
        valid_mae = trades_df[trades_df['mae'] != 0]['mae']
        avg_mae = valid_mae.mean() if not valid_mae.empty else 0
        
        personal_baseline = PersonalBaseline(
            avg_fomo=fomo_index,
            avg_panic=panic_index,
            avg_mae=abs(avg_mae) if avg_mae < 0 else 0,  # MAE is negative, we want absolute
            avg_disposition_ratio=disposition_ratio,
            avg_revenge_count=revenge_count / total_trades if total_trades > 0 else 0
        )
    
    # 2. Bias Loss Mapping (편향별 금전 피해)
    bias_loss_mapping = None
    if total_trades > 0:
        # FOMO Loss: High FOMO trades (fomo_score > 0.7) that resulted in losses
        high_fomo_trades = trades_df[(trades_df['fomo_score'] > 0.7) & (trades_df['fomo_score'] != -1)]
        fomo_loss = abs(high_fomo_trades[high_fomo_trades['pnl'] < 0]['pnl'].sum()) if not high_fomo_trades.empty else 0
        
        # Panic Loss: Low Panic Score trades (panic_score < 0.3) that resulted in losses
        low_panic_trades = trades_df[(trades_df['panic_score'] < 0.3) & (trades_df['panic_score'] != -1)]
        panic_loss = abs(low_panic_trades[low_panic_trades['pnl'] < 0]['pnl'].sum()) if not low_panic_trades.empty else 0
        
        # Revenge Loss: All revenge trades that resulted in losses
        revenge_trades = trades_df[trades_df['is_revenge'] == True]
        revenge_loss = abs(revenge_trades[revenge_trades['pnl'] < 0]['pnl'].sum()) if not revenge_trades.empty else 0
        
        # Disposition Loss: Winners sold too early (regret from winners)
        winners_with_regret = trades_df[(trades_df['pnl'] > 0) & (trades_df['regret'] > 0)]
        disposition_loss = winners_with_regret['regret'].sum() if not winners_with_regret.empty else 0
        
        bias_loss_mapping = BiasLossMapping(
            fomo_loss=float(fomo_loss),
            panic_loss=float(panic_loss),
            revenge_loss=float(revenge_loss),
            disposition_loss=float(disposition_loss)
        )
    
    # 3. Bias Prioritization (우선순위 모델)
    bias_priority = None
    if bias_loss_mapping:
        priorities = []
        
        # Calculate frequency and severity for each bias
        # FOMO
        high_fomo_count = len(trades_df[(trades_df['fomo_score'] > 0.7) & (trades_df['fomo_score'] != -1)])
        fomo_frequency = high_fomo_count / total_trades if total_trades > 0 else 0
        fomo_severity = min(1.0, fomo_index / 0.8) if fomo_index > 0 else 0
        if bias_loss_mapping.fomo_loss > 0 or fomo_frequency > 0.3:
            priorities.append(BiasPriority(
                bias='FOMO',
                priority=0,  # Will be set after sorting
                financial_loss=bias_loss_mapping.fomo_loss,
                frequency=fomo_frequency,
                severity=fomo_severity
            ))
        
        # Panic Sell
        low_panic_count = len(trades_df[(trades_df['panic_score'] < 0.3) & (trades_df['panic_score'] != -1)])
        panic_frequency = low_panic_count / total_trades if total_trades > 0 else 0
        panic_severity = min(1.0, (1 - panic_index) / 0.8) if panic_index < 1 else 0
        if bias_loss_mapping.panic_loss > 0 or panic_frequency > 0.3:
            priorities.append(BiasPriority(
                bias='Panic Sell',
                priority=0,
                financial_loss=bias_loss_mapping.panic_loss,
                frequency=panic_frequency,
                severity=panic_severity
            ))
        
        # Revenge Trading
        revenge_frequency = revenge_count / total_trades if total_trades > 0 else 0
        revenge_severity = min(1.0, revenge_count / 3.0) if revenge_count > 0 else 0
        if bias_loss_mapping.revenge_loss > 0 or revenge_count > 0:
            priorities.append(BiasPriority(
                bias='Revenge Trading',
                priority=0,
                financial_loss=bias_loss_mapping.revenge_loss,
                frequency=revenge_frequency,
                severity=revenge_severity
            ))
        
        # Disposition Effect
        disposition_frequency = len(winners_with_regret) / len(winners) if not winners.empty else 0
        disposition_severity = min(1.0, (disposition_ratio - 1) / 1.5) if disposition_ratio > 1 else 0
        if bias_loss_mapping.disposition_loss > 0 or disposition_ratio > 1.2:
            priorities.append(BiasPriority(
                bias='Disposition Effect',
                priority=0,
                financial_loss=bias_loss_mapping.disposition_loss,
                frequency=disposition_frequency,
                severity=disposition_severity
            ))
        
        # Sort by composite score: (financial_loss * 0.5) + (frequency * 0.2) + (severity * 0.3)
        # Higher score = higher priority (worse)
        for i, p in enumerate(priorities):
            composite_score = (p.financial_loss * 0.5) + (p.frequency * 10000 * 0.2) + (p.severity * 10000 * 0.3)
            priorities[i] = BiasPriority(
                bias=p.bias,
                priority=0,  # Will be set after sorting
                financial_loss=p.financial_loss,
                frequency=p.frequency,
                severity=p.severity
            )
        
        # Sort by composite score (descending) and assign priority
        priorities.sort(key=lambda x: (x.financial_loss * 0.5) + (x.frequency * 10000 * 0.2) + (x.severity * 10000 * 0.3), reverse=True)
        for i, p in enumerate(priorities):
            priorities[i] = BiasPriority(
                bias=p.bias,
                priority=i + 1,
                financial_loss=p.financial_loss,
                frequency=p.frequency,
                severity=p.severity
            )
        
        bias_priority = priorities if priorities else None
    
    # 4. Behavior Shift Detection (행동 변화 탐지)
    behavior_shift = None
    if total_trades >= 6:  # Need at least 6 trades (3 recent + 3 baseline)
        # Recent 3 trades
        recent_trades = trades_df.tail(3)
        # Baseline (all except recent 3)
        baseline_trades = trades_df.head(max(1, total_trades - 3))
        
        # Calculate recent vs baseline for each bias
        shifts = []
        
        # FOMO Shift
        recent_fomo = recent_trades[recent_trades['fomo_score'] != -1]['fomo_score'].mean() if not recent_trades[recent_trades['fomo_score'] != -1].empty else 0
        baseline_fomo = baseline_trades[baseline_trades['fomo_score'] != -1]['fomo_score'].mean() if not baseline_trades[baseline_trades['fomo_score'] != -1].empty else 0
        if baseline_fomo > 0:
            fomo_change = ((recent_fomo - baseline_fomo) / baseline_fomo) * 100
            fomo_trend = 'IMPROVING' if fomo_change < -5 else 'WORSENING' if fomo_change > 5 else 'STABLE'
            shifts.append(BehaviorShift(
                bias='FOMO',
                recent_value=recent_fomo,
                baseline_value=baseline_fomo,
                change_percent=fomo_change,
                trend=fomo_trend
            ))
        
        # Panic Shift
        recent_panic = recent_trades[recent_trades['panic_score'] != -1]['panic_score'].mean() if not recent_trades[recent_trades['panic_score'] != -1].empty else 0
        baseline_panic = baseline_trades[baseline_trades['panic_score'] != -1]['panic_score'].mean() if not baseline_trades[baseline_trades['panic_score'] != -1].empty else 0
        if baseline_panic > 0:
            panic_change = ((recent_panic - baseline_panic) / baseline_panic) * 100
            # For panic, higher is better, so improvement = increase
            panic_trend = 'IMPROVING' if panic_change > 5 else 'WORSENING' if panic_change < -5 else 'STABLE'
            shifts.append(BehaviorShift(
                bias='Panic Sell',
                recent_value=recent_panic,
                baseline_value=baseline_panic,
                change_percent=panic_change,
                trend=panic_trend
            ))
        
        # Revenge Shift
        recent_revenge = len(recent_trades[recent_trades['is_revenge'] == True])
        baseline_revenge = len(baseline_trades[baseline_trades['is_revenge'] == True])
        baseline_revenge_rate = baseline_revenge / len(baseline_trades) if len(baseline_trades) > 0 else 0
        recent_revenge_rate = recent_revenge / len(recent_trades) if len(recent_trades) > 0 else 0
        if baseline_revenge_rate > 0 or recent_revenge_rate > 0:
            revenge_change = ((recent_revenge_rate - baseline_revenge_rate) / (baseline_revenge_rate + 0.01)) * 100
            revenge_trend = 'IMPROVING' if revenge_change < -10 else 'WORSENING' if revenge_change > 10 else 'STABLE'
            shifts.append(BehaviorShift(
                bias='Revenge Trading',
                recent_value=recent_revenge_rate,
                baseline_value=baseline_revenge_rate,
                change_percent=revenge_change,
                trend=revenge_trend
            ))
        
        # Disposition Shift
        recent_winners = recent_trades[recent_trades['pnl'] > 0]
        recent_losers = recent_trades[recent_trades['pnl'] <= 0]
        baseline_winners = baseline_trades[baseline_trades['pnl'] > 0]
        baseline_losers = baseline_trades[baseline_trades['pnl'] <= 0]
        
        recent_disposition = (recent_losers['duration_days'].mean() / recent_winners['duration_days'].mean()) if (not recent_winners.empty and not recent_losers.empty and recent_winners['duration_days'].mean() > 0) else 0
        baseline_disposition = (baseline_losers['duration_days'].mean() / baseline_winners['duration_days'].mean()) if (not baseline_winners.empty and not baseline_losers.empty and baseline_winners['duration_days'].mean() > 0) else 0
        
        if baseline_disposition > 0 and recent_disposition > 0:
            disposition_change = ((recent_disposition - baseline_disposition) / baseline_disposition) * 100
            # Lower disposition ratio is better, so improvement = decrease
            disposition_trend = 'IMPROVING' if disposition_change < -10 else 'WORSENING' if disposition_change > 10 else 'STABLE'
            shifts.append(BehaviorShift(
                bias='Disposition Effect',
                recent_value=recent_disposition,
                baseline_value=baseline_disposition,
                change_percent=disposition_change,
                trend=disposition_trend
            ))
        
        behavior_shift = shifts if shifts else None
    
    # Equity Curve 계산 (시간순 정렬 후 누적)
    trades_df_sorted = trades_df.sort_values('entry_dt')
    trades_df_sorted['cumulative_pnl'] = trades_df_sorted['pnl'].cumsum()
    
    equity_curve = []
    for _, row in trades_df_sorted.iterrows():
        equity_curve.append(EquityCurvePoint(
            date=row['entry_date'],
            cumulative_pnl=float(row['cumulative_pnl']),
            fomo_score=float(row['fomo_score']) if row['fomo_score'] != -1 else None,
            panic_score=float(row['panic_score']) if row['panic_score'] != -1 else None,
            is_revenge=bool(row['is_revenge']),
            ticker=row['ticker'],
            pnl=float(row['pnl'])
        ))
    
    metrics_obj = BehavioralMetrics(
        total_trades=total_trades,
        win_rate=win_rate,
        profit_factor=profit_factor,
        fomo_score=fomo_index,
        panic_score=panic_index,
        disposition_ratio=disposition_ratio,
        revenge_trading_count=revenge_count,
        truth_score=truth_score,
        sharpe_ratio=float(sharpe_ratio),
        sortino_ratio=float(sortino_ratio),
        alpha=float(alpha),
        luck_percentile=float(luck_percentile)
    )
    
    # Convert back to list of EnrichedTrade
    final_trades = []
    for _, row in trades_df.iterrows():
        final_trades.append(EnrichedTrade(
            id=row['id'],
            ticker=row['ticker'],
            entry_date=row['entry_date'],
            entry_price=row['entry_price'],
            exit_date=row['exit_date'],
            exit_price=row['exit_price'],
            qty=row['qty'],
            pnl=row['pnl'],
            return_pct=row['return_pct'],
            duration_days=row['duration_days'],
            market_regime=row['market_regime'],
            is_revenge=row['is_revenge'],
            fomo_score=row['fomo_score'],
            panic_score=row['panic_score'],
            mae=row['mae'],
            mfe=row['mfe'],
            efficiency=row['efficiency'],
            regret=row['regret'],
            entry_day_high=row['entry_day_high'],
            entry_day_low=row['entry_day_low'],
            exit_day_high=row['exit_day_high'],
            exit_day_low=row['exit_day_low']
        ))

    return AnalysisResponse(
        trades=final_trades,
        metrics=metrics_obj,
        is_low_sample=total_trades < 5,
        personal_baseline=personal_baseline,
        bias_loss_mapping=bias_loss_mapping,
        bias_priority=bias_priority,
        behavior_shift=behavior_shift,
        equity_curve=equity_curve
    )

@app.post("/coach")
async def get_ai_coach(request: CoachRequest):
    """
    OpenAI API를 백엔드에서 호출하여 AI 분석을 반환합니다.
    프론트엔드는 이 엔드포인트만 호출합니다.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {
            "diagnosis": "API Key missing. Please configure OPENAI_API_KEY environment variable.",
            "rule": "No rule generated.",
            "bias": "N/A",
            "fix": "Add OPENAI_API_KEY to your environment"
        }
    
    openai = OpenAI(api_key=api_key)
    
    # Prompt 생성 (기존 openaiService.ts와 동일한 로직)
    top_regrets = sorted(request.trades, key=lambda x: x.get('regret', 0), reverse=True)[:3]
    top_regrets_str = [f"{t['ticker']} (Missed ${t.get('regret', 0):.0f})" for t in top_regrets]
    
    revenge_details = [t for t in request.trades if t.get('is_revenge')]
    revenge_str = ', '.join([f"{t['ticker']} (-${abs(t.get('pnl', 0)):.0f})" for t in revenge_details]) if revenge_details else "None"
    
    # Personal Baseline 텍스트
    personal_baseline_text = ''
    if request.personal_baseline:
        pb = request.personal_baseline
        personal_baseline_text = f"""
    PERSONAL BASELINE (Your Historical Average):
    - Avg FOMO: {(pb['avg_fomo'] * 100):.0f}% (Current: {(request.metrics['fomo_score'] * 100):.0f}%)
    - Avg Panic: {(pb['avg_panic'] * 100):.0f}% (Current: {(request.metrics['panic_score'] * 100):.0f}%)
    - Avg Disposition: {pb['avg_disposition_ratio']:.1f}x (Current: {request.metrics['disposition_ratio']:.1f}x)
    """
    
    # Bias Loss Mapping 텍스트
    bias_loss_text = ''
    if request.bias_loss_mapping:
        blm = request.bias_loss_mapping
        bias_loss_text = f"""
    BIAS LOSS MAPPING (Financial Impact):
    - FOMO Loss: -${blm['fomo_loss']:.0f}
    - Panic Sell Loss: -${blm['panic_loss']:.0f}
    - Revenge Trading Loss: -${blm['revenge_loss']:.0f}
    - Disposition Effect (Missed): -${blm['disposition_loss']:.0f}
    """
    
    # Bias Priority 텍스트
    bias_priority_text = ''
    if request.bias_priority and len(request.bias_priority) > 0:
        bias_priority_text = f"""
    FIX PRIORITY (Ranked by Impact):
    {chr(10).join([f"    {i+1}. {p['bias']}: -${p['financial_loss']:.0f} (Frequency: {(p['frequency']*100):.0f}%, Severity: {(p['severity']*100):.0f}%)" for i, p in enumerate(request.bias_priority)])}
    """
    
    # Behavior Shift 텍스트
    behavior_shift_text = ''
    if request.behavior_shift and len(request.behavior_shift) > 0:
        behavior_shift_text = f"""
    BEHAVIOR SHIFT (Recent 3 vs Baseline):
    {chr(10).join([f"    - {s['bias']}: {s['trend']} ({(s['change_percent']:+.1f)}%)" for s in request.behavior_shift])}
    """
    
    # Total Regret 계산
    total_regret = sum(t.get('regret', 0) for t in request.trades)
    
    # Total Bias Loss 계산
    total_bias_loss = 0
    if request.bias_loss_mapping:
        total_bias_loss = (request.bias_loss_mapping['fomo_loss'] + 
                          request.bias_loss_mapping['panic_loss'] + 
                          request.bias_loss_mapping['revenge_loss'] + 
                          request.bias_loss_mapping['disposition_loss'])
    
    prompt = f"""
    Act as the "Truth Pipeline" AI. You are an objective, slightly ruthless, data-driven Trading Coach.
    Your goal is to correct behavior, not predict markets.
    
    USER PROFILE:
    - Mode: {"NOVICE / LOW SAMPLE (Focus on specific mistakes)" if request.is_low_sample else "EXPERIENCED (Focus on statistics)"}
    
    HARD EVIDENCE:
    1. TRUTH SCORE: {request.metrics['truth_score']}/100
    2. DISCIPLINE (FOMO): You bought at {(request.metrics['fomo_score'] * 100):.0f}% of the day's range on average. (High = Bad)
    3. NERVES (Panic): You sold at {(request.metrics['panic_score'] * 100):.0f}% of the day's range on average. (High = Bad)
    4. PATIENCE (Disposition): You hold losers {request.metrics['disposition_ratio']:.1f}x longer than winners.
    5. EMOTION (Revenge): {request.metrics['revenge_trading_count']} revenge trades detected. Tickers: {revenge_str}.
    6. REGRET: You left ${total_regret:.0f} on the table. Top misses: {', '.join(top_regrets_str)}.

    {personal_baseline_text}
    {bias_loss_text}
    {bias_priority_text}
    {behavior_shift_text}

    EVIDENCE STRUCTURE (You MUST reference these numbers in your diagnosis):
    - Evidence #1: FOMO Score {(request.metrics['fomo_score'] * 100):.0f}% (Threshold > 70% is bad){f" vs Your Average {(request.personal_baseline['avg_fomo'] * 100):.0f}%" if request.personal_baseline else ''}
    - Evidence #2: Panic Sell Score {(request.metrics['panic_score'] * 100):.0f}% (Threshold > 70% is bad){f" vs Your Average {(request.personal_baseline['avg_panic'] * 100):.0f}%" if request.personal_baseline else ''}
    - Evidence #3: Disposition Ratio {request.metrics['disposition_ratio']:.1f}x (Threshold > 1.5x is bad){f" vs Your Average {request.personal_baseline['avg_disposition_ratio']:.1f}x" if request.personal_baseline else ''}
    - Evidence #4: Revenge Trading Count {request.metrics['revenge_trading_count']} (Threshold > 0 is bad)
    - Evidence #5: Total Regret ${total_regret:.0f}
    {f"- Evidence #6: Total Bias Loss -${total_bias_loss:.0f}" if total_bias_loss > 0 else ''}
    {f"- Evidence #7: Priority Fix #1 is {request.bias_priority[0]['bias']} (Loss: -${request.bias_priority[0]['financial_loss']:.0f})" if request.bias_priority and len(request.bias_priority) > 0 else ''}

    INSTRUCTIONS:
    1. DIAGNOSIS (3 sentences): 
       - Sentence 1: Direct, slightly harsh observation of their biggest flaw. {f"Focus on {request.bias_priority[0]['bias']} (Priority #1, Loss: -${request.bias_priority[0]['financial_loss']:.0f})." if request.bias_priority and len(request.bias_priority) > 0 else ''}
       - Sentence 2: EVIDENCE-BASED FACT. You MUST strictly follow this format: "According to Evidence #X, you [specific action] on [Ticker]." {f"Compare to your personal baseline when relevant." if request.personal_baseline else ''} Example: "According to Evidence #1, you bought GME at 93% of the day's range, well above your average of 78%."
       - Sentence 3: The financial impact. {f"Mention specific loss amounts from Bias Loss Mapping if significant." if request.bias_loss_mapping else ''} {f"Note any worsening trends from Behavior Shift." if request.behavior_shift and any(s['trend'] == 'WORSENING' for s in request.behavior_shift) else ''}
    2. RULE (1 sentence): A catchy, memorable trading commandment to fix this specific flaw. {f"Target {request.bias_priority[0]['bias']} specifically." if request.bias_priority and len(request.bias_priority) > 0 else ''}
    3. BIAS: Name the single dominant psychological bias. {f"Use: {request.bias_priority[0]['bias']}" if request.bias_priority and len(request.bias_priority) > 0 else ''} (e.g. Disposition Effect, Action Bias, Revenge Trading, FOMO).
    4. FIX: One specific, actionable step to take immediately. {f"Focus on fixing {request.bias_priority[0]['bias']} first (highest financial impact)." if request.bias_priority and len(request.bias_priority) > 0 else ''}

    Output valid JSON only with this exact structure:
    {{
      "diagnosis": "3 sentences. Must mention a ticker.",
      "rule": "1 sentence rule.",
      "bias": "Primary bias.",
      "fix": "Priority fix."
    }}
    """
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a data-driven trading coach. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        content = completion.choices[0].message.content
        if content:
            return json.loads(content)
        else:
            raise ValueError("No content returned")
            
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return {
            "diagnosis": "AI Analysis unavailable. Focus on your Win Rate and Profit Factor manually.",
            "rule": "Cut losers faster than you think.",
            "bias": "Service Error",
            "fix": "Check API Key or Network."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
