from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from typing import List, Optional, Tuple
from pydantic import BaseModel
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
import os
from openai import OpenAI
import json
from pathlib import Path

# --- RAG GLOBAL SETTINGS ---
BASE_DIR = Path(__file__).parent
RAG_FILE_PATH = BASE_DIR / "rag_cards.json"
RAG_EMBED_PATH = BASE_DIR / "rag_embeddings.npy"
RAG_CARDS: List[dict] = []
RAG_EMBEDDINGS: Optional[np.ndarray] = None

# --- RAG HELPER FUNCTIONS ---

def get_embeddings_batch(texts: List[str], client: OpenAI) -> List[List[float]]:
    """
    한 번의 API 호출로 여러 텍스트의 임베딩을 생성 (Batch Processing)
    비용 절감 및 속도 향상
    """
    try:
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def cosine_similarity_top_k(
    query_vec: np.ndarray, 
    target_vecs: np.ndarray, 
    k: int = 2, 
    threshold: float = 0.4
) -> Tuple[List[int], List[float]]:
    """
    Numpy만을 사용한 가벼운 코사인 유사도 계산
    Returns: (indices, scores)
    """
    if target_vecs is None or len(target_vecs) == 0:
        return [], []
    
    # Normalize
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    target_norms = target_vecs / (np.linalg.norm(target_vecs, axis=1, keepdims=True) + 1e-9)
    
    # Dot product
    similarities = np.dot(target_norms, query_norm)
    
    # Top K selection
    top_k_indices = np.argsort(similarities)[-k:][::-1]
    
    results = []
    scores = []
    
    for idx in top_k_indices:
        score = float(similarities[idx])
        if score >= threshold:
            results.append(int(idx))
            scores.append(score)
    
    return results, scores

def load_rag_index():
    """서버 시작 시 RAG 데이터 및 임베딩 로드"""
    global RAG_CARDS, RAG_EMBEDDINGS
    
    try:
        # 1. Load JSON
        if not RAG_FILE_PATH.exists():
            print(f"⚠ Warning: {RAG_FILE_PATH} not found. RAG feature disabled.")
            RAG_CARDS = []
            RAG_EMBEDDINGS = None
            return
        
        with open(RAG_FILE_PATH, "r", encoding="utf-8") as f:
            RAG_CARDS = json.load(f)
        
        if not RAG_CARDS:
            print("⚠ Warning: RAG cards file is empty. RAG feature disabled.")
            RAG_EMBEDDINGS = None
            return
        
        print(f"✓ Loaded {len(RAG_CARDS)} RAG cards from {RAG_FILE_PATH}")
        
        # 2. Load Embeddings (파일이 없으면 예외 처리 - 생성은 관리자 스크립트로 분리)
        if RAG_EMBED_PATH.exists():
            try:
                RAG_EMBEDDINGS = np.load(RAG_EMBED_PATH)
                # 카드 개수와 임베딩 개수가 다르면 경고
                if len(RAG_EMBEDDINGS) != len(RAG_CARDS):
                    print(f"⚠ Warning: Embeddings count ({len(RAG_EMBEDDINGS)}) doesn't match cards count ({len(RAG_CARDS)}).")
                    print("⚠ RAG feature disabled. Please regenerate embeddings using generate_embeddings.py")
                    RAG_EMBEDDINGS = None
                else:
                    print(f"✓ Loaded {len(RAG_EMBEDDINGS)} embeddings from {RAG_EMBED_PATH}")
            except Exception as e:
                print(f"⚠ Error loading embeddings file: {e}")
                print("⚠ RAG feature disabled. Please regenerate embeddings using generate_embeddings.py")
                RAG_EMBEDDINGS = None
        else:
            # 파일이 없으면 경고만 출력 (생성은 하지 않음)
            print(f"⚠ Warning: {RAG_EMBED_PATH} not found. RAG feature disabled.")
            print("⚠ To enable RAG, generate embeddings using: python generate_embeddings.py")
            print("⚠ Or ensure rag_embeddings.npy is committed to Git repository.")
            RAG_EMBEDDINGS = None
                
    except Exception as e:
        print(f"❌ Error loading RAG index: {e}")
        import traceback
        traceback.print_exc()
        RAG_CARDS = []
        RAG_EMBEDDINGS = None

# FastAPI 버전 호환성 처리
try:
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """서버 시작 시 RAG 데이터 로드 (FastAPI 0.93+)"""
        load_rag_index()
        yield
        # Shutdown logic if needed
    
    app = FastAPI(title="Truth Pipeline Engine", lifespan=lifespan)
except:
    # Fallback for older FastAPI versions
    app = FastAPI(title="Truth Pipeline Engine")
    
    @app.on_event("startup")
    async def startup_event():
        """서버 시작 시 RAG 데이터 로드 (FastAPI < 0.93)"""
        load_rag_index()

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
    # 최적화: trades 전체 대신 요약 데이터만 수신 (데이터 핑퐁 구조 제거)
    top_regrets: List[dict]  # Top 3 regrets만
    revenge_details: List[dict]  # Revenge trades 요약만
    metrics: dict
    is_low_sample: bool
    personal_baseline: Optional[dict] = None
    bias_loss_mapping: Optional[dict] = None
    bias_priority: Optional[List[dict]] = None
    behavior_shift: Optional[List[dict]] = None

# --- HELPER FUNCTIONS ---

@lru_cache(maxsize=2000)  # Increased cache size for large CSV files
def fetch_market_data_cached(ticker: str, start_date: str, end_date: str):
    """
    LRU Cache를 사용한 시장 데이터 가져오기
    캐시 키는 함수 파라미터로 자동 생성됩니다.
    대량 CSV 처리 시 중복 요청을 방지합니다.
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
            # Try adding .KS or .KQ for Korean stocks if pure number
            if ticker.isdigit():
                # Try KOSPI first (.KS)
                df = yf.download(f"{ticker}.KS", start=buffer_start, end=buffer_end, progress=False)
                if df.empty:
                    # Try KOSDAQ (.KQ)
                    df = yf.download(f"{ticker}.KQ", start=buffer_start, end=buffer_end, progress=False)
        
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
    
    # Performance optimization: Pre-fetch unique ticker-date ranges
    # This reduces redundant API calls for large CSV files
    unique_ticker_ranges = {}
    for _, row in df.iterrows():
        ticker = str(row['ticker'])
        entry_date = str(row['entry_date'])
        exit_date = str(row['exit_date'])
        key = (ticker, entry_date, exit_date)
        if key not in unique_ticker_ranges:
            unique_ticker_ranges[key] = fetch_market_data_cached(ticker, entry_date, exit_date)
    
    # 2. Process Each Trade
    for _, row in df.iterrows():
        ticker = str(row['ticker'])
        entry_date = str(row['entry_date'])
        exit_date = str(row['exit_date'])
        
        # Use pre-fetched market data
        market_df = unique_ticker_ranges.get((ticker, entry_date, exit_date))
        
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
    # Check if we have any valid market data
    valid_fomo = trades_df[trades_df['fomo_score'] != -1]['fomo_score']
    fomo_index = valid_fomo.mean() if not valid_fomo.empty else 0
    
    valid_panic = trades_df[trades_df['panic_score'] != -1]['panic_score']
    # Panic Score in UI is "How close to bottom did I sell?". 0 = Sold Bottom (Bad), 1 = Sold Top (Good).
    # BUT Specification says: "Panic Sell Score (Exit Price 위치값: intraday 저가 대비 얼마나 공포 매도인지)"
    # If result is low (close to day low), it means panic. 
    # So we want to invert it for "Badness"? 
    # Let's keep raw 0-1 score: 0 means sold at Low.
    panic_index = valid_panic.mean() if not valid_panic.empty else 0
    
    # If all trades failed to fetch market data, warn but continue
    if valid_fomo.empty and valid_panic.empty:
        print("Warning: All trades failed to fetch market data. Metrics will be limited.")
    
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
    
    # --- 1. RAG Query Generation Strategy ---
    primary_bias = request.bias_priority[0]['bias'] if request.bias_priority and len(request.bias_priority) > 0 else None
    
    # 쿼리 생성 전략: 편향이 명확하면 편향 중심, 아니면 수치 기반
    query = ""
    if primary_bias:
        # 편향 이름과 관련 키워드를 조합하여 의미론적 검색 강화
        fomo_score = request.metrics.get('fomo_score', 0)
        panic_score = request.metrics.get('panic_score', 0)
        
        if primary_bias == "FOMO":
            if fomo_score > 0.8:
                query = "FOMO extreme high entry chasing panic buying impulse"
            else:
                query = "FOMO chasing high entry impulse fear of missing out"
        elif primary_bias == "Panic Sell":
            if panic_score < 0.2:
                query = "Panic Sell extreme loss aversion selling low fear"
            else:
                query = "Panic Sell loss aversion selling low fear"
        elif primary_bias == "Revenge Trading":
            query = "Revenge Trading anger emotional recovery tilt overtrading"
        elif primary_bias == "Disposition Effect":
            query = "Disposition Effect holding losers selling winners too early"
        else:
            query = f"{primary_bias} trading psychology bias"
    else:
        # 편향이 감지되지 않은 경우 (성공적인 매매 or 데이터 부족)
        if request.metrics.get('win_rate', 0) > 0.6:
            query = "Winning psychology consistency discipline"
        else:
            query = "Trading psychology basics risk management"
    
    # --- 2. RAG Retrieval (Tag Filtering + Vector Search) ---
    rag_context_text = ""
    retrieved_cards_for_response = []  # For JSON response
    
    if RAG_CARDS and RAG_EMBEDDINGS is not None:
        try:
            # A. 태그 기반 필터링 (Filtering) - 검색 범위 좁히기
            filtered_indices = []
            if primary_bias:
                target_tags = []
                if primary_bias == "FOMO": 
                    target_tags = ["FOMO", "entry", "chasing"]
                elif primary_bias == "Panic Sell": 
                    target_tags = ["Panic Sell", "exit", "loss_aversion"]
                elif primary_bias == "Revenge Trading": 
                    target_tags = ["Revenge Trading", "revenge", "emotion"]
                elif primary_bias == "Disposition Effect": 
                    target_tags = ["Disposition Effect", "holding_loser"]
                
                # 태그가 하나라도 겹치면 후보군에 포함
                for idx, card in enumerate(RAG_CARDS):
                    if any(t in card.get('tags', []) for t in target_tags):
                        filtered_indices.append(idx)
            
            # 필터링 된 카드가 없으면 전체 대상
            if not filtered_indices:
                filtered_indices = list(range(len(RAG_CARDS)))
            
            # B. 벡터 검색 (Vector Search)
            query_embeddings = get_embeddings_batch([query], openai)
            if query_embeddings and len(query_embeddings) > 0:
                query_vec = np.array(query_embeddings[0])
                
                # 필터링된 임베딩만 추출하여 검색
                target_vecs = RAG_EMBEDDINGS[filtered_indices]
                
                # Threshold 동적 조정
                threshold = 0.4 if primary_bias else 0.6
                
                # Top 2, Threshold 적용
                local_indices, scores = cosine_similarity_top_k(query_vec, target_vecs, k=2, threshold=threshold)
                
                # 실제 인덱스로 매핑
                final_indices = [filtered_indices[i] for i in local_indices]
                retrieved_cards = [RAG_CARDS[i] for i in final_indices]
                
                if retrieved_cards:
                    rag_text_lines = []
                    for card in retrieved_cards:
                        rag_text_lines.append(f"- PRINCIPLE: {card['title']}")
                        rag_text_lines.append(f"  INSIGHT: {card['content']}")
                        rag_text_lines.append(f"  ACTION: {card['action']}")
                    
                    rag_context_text = f"""
    RAG KNOWLEDGE BASE (Behavioral Finance Principles - Reference Only):
    The following principles are retrieved based on your primary bias: '{primary_bias if primary_bias else "General Trading Psychology"}'.
    
    CRITICAL: These principles are for EXPLANATION and ADVICE only. 
    Evidence numbers above take ABSOLUTE PRIORITY over these principles.
    If Evidence conflicts with RAG principles, Evidence is correct.
    
    {chr(10).join(rag_text_lines)}
    """
                    
                    # Store retrieved cards for JSON response
                    retrieved_cards_for_response = [
                        {
                            "title": card['title'],
                            "content": card['content'],
                            "action": card['action']
                        }
                        for card in retrieved_cards
                    ]
                else:
                    retrieved_cards_for_response = []
        except Exception as e:
            print(f"RAG Logic Error: {e}")
            import traceback
            traceback.print_exc()
            rag_context_text = ""  # 명시적으로 빈 문자열
            retrieved_cards_for_response = []
            # 코칭은 계속 진행
    
    # Prompt 생성 (프론트엔드에서 이미 요약 데이터로 전송됨)
    top_regrets_str = [f"{t['ticker']} (Missed ${t.get('regret', 0):.0f})" for t in request.top_regrets]
    
    revenge_str = ', '.join([f"{t['ticker']} (-${abs(t.get('pnl', 0)):.0f})" for t in request.revenge_details]) if request.revenge_details else "None"
    
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
        behavior_shift_lines = [
            f"    - {s['bias']}: {s['trend']} ({(s['change_percent']:+.1f)}%)" 
            for s in request.behavior_shift
        ]
        behavior_shift_text = f"""
    BEHAVIOR SHIFT (Recent 3 vs Baseline):
    {chr(10).join(behavior_shift_lines)}
    """
    
    # Total Regret 계산 (metrics에서 가져옴)
    total_regret = request.metrics.get('total_regret', 0)
    
    # Total Bias Loss 계산
    total_bias_loss = 0
    if request.bias_loss_mapping:
        total_bias_loss = (request.bias_loss_mapping['fomo_loss'] + 
                          request.bias_loss_mapping['panic_loss'] + 
                          request.bias_loss_mapping['revenge_loss'] + 
                          request.bias_loss_mapping['disposition_loss'])
    
    # 프롬프트 구성 요소를 변수로 분리 (복잡도 개선)
    primary_bias_info = ""
    if request.bias_priority and len(request.bias_priority) > 0:
        primary_bias = request.bias_priority[0]['bias']
        primary_loss = request.bias_priority[0]['financial_loss']
        primary_bias_info = f"Focus on {primary_bias} (Priority #1, Loss: -${primary_loss:.0f})."
    
    personal_baseline_note = "Compare to your personal baseline when relevant." if request.personal_baseline else ""
    bias_loss_note = "Mention specific loss amounts from Bias Loss Mapping if significant." if request.bias_loss_mapping else ""
    behavior_shift_warning = ""
    if request.behavior_shift and any(s['trend'] == 'WORSENING' for s in request.behavior_shift):
        behavior_shift_warning = "Note any worsening trends from Behavior Shift."
    
    evidence_fomo_text = f"Evidence #1: FOMO Score {(request.metrics['fomo_score'] * 100):.0f}% (Clinical threshold > 70% = FOMO)"
    if request.personal_baseline:
        evidence_fomo_text += f" vs Your Average {(request.personal_baseline['avg_fomo'] * 100):.0f}%"
    
    evidence_panic_text = f"Evidence #2: Panic Sell Score {(request.metrics['panic_score'] * 100):.0f}% (Clinical threshold < 30% = Panic)"
    if request.personal_baseline:
        evidence_panic_text += f" vs Your Average {(request.personal_baseline['avg_panic'] * 100):.0f}%"
    
    evidence_disposition_text = f"Evidence #3: Disposition Ratio {request.metrics['disposition_ratio']:.1f}x (Clinical threshold > 1.5x = Disposition Effect)"
    if request.personal_baseline:
        evidence_disposition_text += f" vs Your Average {request.personal_baseline['avg_disposition_ratio']:.1f}x"
    
    evidence_priority_text = ""
    if request.bias_priority and len(request.bias_priority) > 0:
        evidence_priority_text = f"- Evidence #7: Priority Fix #1 is {request.bias_priority[0]['bias']} (Loss: -${request.bias_priority[0]['financial_loss']:.0f})"
    
    rule_target_note = f"Target {request.bias_priority[0]['bias']} specifically." if request.bias_priority and len(request.bias_priority) > 0 else ""
    rule_rag_note = "If RAG KNOWLEDGE BASE is provided above, base your rule on the 'ACTION' items from RAG principles." if rag_context_text else ""
    
    bias_name_note = f"Use: {request.bias_priority[0]['bias']}" if request.bias_priority and len(request.bias_priority) > 0 else ""
    fix_target_note = f"Focus on fixing {request.bias_priority[0]['bias']} first (highest financial impact)." if request.bias_priority and len(request.bias_priority) > 0 else ""
    fix_rag_note = "Combine the RAG 'ACTION' items with the user's specific context from Evidence above." if rag_context_text else ""
    
    references_field = f',\n      "references": [{{"title": "...", "content": "...", "action": "..."}}]' if rag_context_text else ''
    
    prompt = f"""
    Act as the "Truth Pipeline" AI. You are an objective, slightly ruthless, data-driven Trading Coach.
    Your goal is to correct behavior, not predict markets.
    
    CRITICAL RULES (STRICTLY ENFORCED):
    - EVIDENCE IS KING: Your diagnosis must be based 100% on the HARD EVIDENCE numbers below.
    - RAG IS QUEEN: Your advice (Rule/Fix) must be inspired by the RAG KNOWLEDGE BASE provided (if available).
    - NEVER use vague language like "~may be", "~could be", "~might be", "~seems like", "~appears to"
    - ALWAYS state facts with certainty based on Evidence numbers
    - NEVER repeat template phrases. Each response must be unique and specific to this user's data
    - ALWAYS emphasize "Evidence-based" or "According to Evidence #X" in your diagnosis
    - NEVER make predictions about future market movements
    - NEVER recommend specific stocks or investment advice
    - RAG CONTEXT is for educational reference ONLY. It must NOT alter Evidence-based diagnosis.
    - If RAG CONTEXT conflicts with Evidence, Evidence takes ABSOLUTE PRIORITY.
    - RAG CONTEXT should be used to EXPLAIN why the Evidence indicates a problem, not to create new conclusions.
    
    USER PROFILE:
    - Mode: {"NOVICE / LOW SAMPLE (Focus on specific mistakes)" if request.is_low_sample else "EXPERIENCED (Focus on statistics)"}
    
    HARD EVIDENCE (Clinical Thresholds - Conservative):
    - FOMO Threshold: >70% of day's range = Clinical FOMO (based on behavioral finance research)
    - Panic Sell Threshold: <30% of day's range = Clinical Panic (based on behavioral finance research)
    - Disposition Threshold: >1.5x ratio = Clinical Disposition Effect (based on Shefrin & Statman research)
    - Revenge Trading: Any trade <24h after loss = Clinical Revenge Trading
    
    1. TRUTH SCORE: {request.metrics['truth_score']}/100
    2. DISCIPLINE (FOMO): You bought at {(request.metrics['fomo_score'] * 100):.0f}% of the day's range on average. (Clinical threshold: >70% indicates FOMO)
    3. NERVES (Panic): You sold at {(request.metrics['panic_score'] * 100):.0f}% of the day's range on average. (Clinical threshold: <30% indicates panic selling)
    4. PATIENCE (Disposition): You hold losers {request.metrics['disposition_ratio']:.1f}x longer than winners. (Clinical threshold: >1.5x indicates Disposition Effect)
    5. EMOTION (Revenge): {request.metrics['revenge_trading_count']} revenge trades detected. Tickers: {revenge_str}.
    6. REGRET: You left ${total_regret:.0f} on the table. Top misses: {', '.join(top_regrets_str)}.

    {personal_baseline_text}
    {bias_loss_text}
    {bias_priority_text}
    {behavior_shift_text}

    EVIDENCE STRUCTURE (You MUST reference these numbers in your diagnosis):
    - {evidence_fomo_text}
    - {evidence_panic_text}
    - {evidence_disposition_text}
    - Evidence #4: Revenge Trading Count {request.metrics['revenge_trading_count']} (Any count > 0 = Revenge Trading)
    - Evidence #5: Total Regret ${total_regret:.0f}
    {f"- Evidence #6: Total Bias Loss -${total_bias_loss:.0f}" if total_bias_loss > 0 else ''}
    {evidence_priority_text}

    {rag_context_text}

    IMPORTANT CLARIFICATION:
    - These metrics detect BEHAVIORAL BIASES, not technical trading patterns
    - High FOMO score does NOT mean "breakout trading" or "momentum strategy" - it means buying near day's high due to fear of missing out
    - Low Panic score does NOT mean "stop-loss discipline" - it means selling near day's low due to panic
    - This system analyzes PSYCHOLOGICAL ERRORS, not trading strategies

    INSTRUCTIONS:
    1. DIAGNOSIS (3 sentences, EVIDENCE-BASED, NO VAGUE LANGUAGE): 
       - Sentence 1: Direct, slightly harsh observation of their biggest flaw. {primary_bias_info}
       - Sentence 2: EVIDENCE-BASED FACT. You MUST strictly follow this format: "According to Evidence #X, you [specific action] on [Ticker] at [specific price/percentage]." {personal_baseline_note} Example: "According to Evidence #1, you bought GME at 93% of the day's range ($347.51), exceeding the clinical FOMO threshold of 70% and your average of 78%."
       - Sentence 3: The financial impact with specific numbers. {bias_loss_note} {behavior_shift_warning}
    2. RULE (1 sentence): A catchy, memorable trading commandment to fix this specific flaw. {rule_target_note} {rule_rag_note}
    3. BIAS: Name the single dominant psychological bias. {bias_name_note} (e.g. Disposition Effect, Action Bias, Revenge Trading, FOMO).
    4. FIX: One specific, actionable step to take immediately. {fix_target_note} {fix_rag_note}
    
    Output valid JSON only with this exact structure:
    {{
      "diagnosis": "3 sentences. Must mention a ticker.",
      "rule": "1 sentence rule.",
      "bias": "Primary bias.",
      "fix": "Priority fix."{references_field}
    }}
    
    NOTE: "references" field is optional. Include it only if RAG KNOWLEDGE BASE was provided above.
    If RAG was not provided, omit the "references" field entirely.
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
        
        # Check if response has choices
        if not completion.choices or len(completion.choices) == 0:
            raise ValueError("OpenAI API returned empty choices array")
        
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("OpenAI API returned no content")
        
        # Parse JSON with error handling
        try:
            result = json.loads(content)
            # Validate required fields
            required_fields = ["diagnosis", "rule", "bias", "fix"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # If RAG cards were retrieved but not in AI response, add them manually
            if retrieved_cards_for_response and "references" not in result:
                result["references"] = retrieved_cards_for_response
            
            return result
        except json.JSONDecodeError as json_err:
            print(f"JSON parsing error: {json_err}")
            print(f"Raw content: {content[:200]}...")  # Log first 200 chars
            raise ValueError(f"Invalid JSON response from OpenAI: {json_err}")
            
    except ValueError as ve:
        print(f"Validation Error: {ve}")
        return {
            "diagnosis": "AI Analysis unavailable. Focus on your Win Rate and Profit Factor manually.",
            "rule": "Cut losers faster than you think.",
            "bias": "Service Error",
            "fix": "Check API Key or Network."
        }
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
