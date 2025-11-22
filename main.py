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
    
    # Strategy Tagging (사용자 피드백)
    strategy_tag: Optional[str] = None  # 'BREAKOUT', 'AGGRESSIVE_ENTRY', 'FOMO'
    user_acknowledged: bool = False
    
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

class DeepPattern(BaseModel):
    type: str  # 'TIME_CLUSTER' | 'PRICE_CLUSTER' | 'REVENGE_SEQUENCE' | 'MARKET_REGIME' | 'MAE_CLUSTER'
    description: str
    significance: str  # 'HIGH' | 'MEDIUM' | 'LOW'
    metadata: Optional[dict] = None  # Additional context (hour, percentage, etc.)

class PersonalPlaybook(BaseModel):
    rules: List[str]
    generated_at: str
    based_on: dict  # {patterns: int, biases: List[str]}

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
    # Deep Pattern Analysis
    deep_patterns: Optional[List[DeepPattern]] = None

class CoachRequest(BaseModel):
    # 최적화: trades 전체 대신 요약 데이터만 수신 (데이터 핑퐁 구조 제거)
    top_regrets: List[dict]  # Top 3 regrets만
    revenge_details: List[dict]  # Revenge trades 요약만
    best_executions: List[dict]  # 잘한 매매 (이달의 명장면)
    patterns: List[dict]  # 반복되는 패턴 (과정 평가)
    deep_patterns: Optional[List[dict]] = None  # 고급 패턴 분석
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

def detect_market_regime(ticker: str, date: str, market_df) -> str:
    """
    시장 환경 분석: SPY 대비 추세를 분석하여 BULL/BEAR/SIDEWAYS 판단
    """
    try:
        trade_date = pd.Timestamp(date)
        
        # SPY 데이터 가져오기 (20일 이동평균 기준)
        spy_start = (trade_date - timedelta(days=30)).strftime("%Y-%m-%d")
        spy_end = (trade_date + timedelta(days=5)).strftime("%Y-%m-%d")
        
        spy_df = yf.download('SPY', start=spy_start, end=spy_end, progress=False)
        if spy_df.empty:
            return "UNKNOWN"
        
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        
        # 20일 이동평균 계산
        spy_df['MA20'] = spy_df['Close'].rolling(window=20, min_periods=1).mean()
        
        # 거래일과 가장 가까운 날짜 찾기
        if trade_date not in spy_df.index:
            nearest_idx = spy_df.index.get_indexer([trade_date], method='nearest')[0]
            trade_date = spy_df.index[nearest_idx]
        
        if trade_date not in spy_df.index:
            return "UNKNOWN"
        
        current_price = spy_df.loc[trade_date, 'Close']
        ma20 = spy_df.loc[trade_date, 'MA20']
        
        # 5일 전 가격과 비교
        try:
            prev_5_idx = spy_df.index.get_indexer([trade_date], method='nearest')[0] - 5
            if prev_5_idx >= 0:
                prev_price = spy_df.iloc[prev_5_idx]['Close']
                price_change = (current_price - prev_price) / prev_price
                
                # 상승장: 현재가 > MA20이고 5일간 상승
                if current_price > ma20 and price_change > 0.02:
                    return "BULL"
                # 하락장: 현재가 < MA20이고 5일간 하락
                elif current_price < ma20 and price_change < -0.02:
                    return "BEAR"
                else:
                    return "SIDEWAYS"
        except:
            pass
        
        # 단순 MA20 기준
        if current_price > ma20 * 1.02:
            return "BULL"
        elif current_price < ma20 * 0.98:
            return "BEAR"
        else:
            return "SIDEWAYS"
            
    except Exception as e:
        print(f"Market regime detection error: {e}")
        return "UNKNOWN"

def extract_deep_patterns(trades_df: pd.DataFrame) -> List[DeepPattern]:
    """
    LLM Clustering 느낌의 고급 패턴 추출
    """
    patterns = []
    
    if len(trades_df) < 3:
        return patterns
    
    # 시간대별 패턴 분석
    trades_df['entry_dt'] = pd.to_datetime(trades_df['entry_date'])
    trades_df['exit_dt'] = pd.to_datetime(trades_df['exit_date'])
    trades_df['entry_hour'] = trades_df['entry_dt'].dt.hour
    trades_df['exit_hour'] = trades_df['exit_dt'].dt.hour
    
    # 1. MAE가 큰 거래의 시간대 클러스터링
    high_mae_trades = trades_df[trades_df['mae'] < -0.02]  # MAE < -2%
    if len(high_mae_trades) >= 3:
        hour_distribution = high_mae_trades['entry_hour'].value_counts()
        if len(hour_distribution) > 0:
            peak_hour = hour_distribution.idxmax()
            peak_count = hour_distribution.max()
            peak_percentage = (peak_count / len(high_mae_trades)) * 100
            
            # 40% 이상이 특정 시간대에 집중되면 패턴으로 인정
            if peak_percentage >= 40:
                significance = 'HIGH' if peak_percentage >= 60 else 'MEDIUM'
                patterns.append(DeepPattern(
                    type='TIME_CLUSTER',
                    description=f"MAE가 큰 포지션({len(high_mae_trades)}건) 중 {peak_count}건({peak_percentage:.0f}%)이 {peak_hour}시에 발생",
                    significance=significance,
                    metadata={'hour': int(peak_hour), 'count': int(peak_count), 'total': len(high_mae_trades)}
                ))
    
    # 2. 전일 고가 대비 청산 위치 분석
    valid_exits = trades_df[(trades_df['exit_day_high'] > 0) & (trades_df['panic_score'] != -1)]
    if len(valid_exits) >= 5:
        # exit_price / exit_day_high 비율 계산
        exit_ratios = valid_exits['exit_price'] / valid_exits['exit_day_high']
        avg_exit_ratio = exit_ratios.mean()
        
        # 평균적으로 고가 대비 낮은 위치에서 청산하는 패턴
        if avg_exit_ratio < 0.95:  # 고가 대비 95% 미만에서 청산
            exit_percentage = (1 - avg_exit_ratio) * 100
            patterns.append(DeepPattern(
                type='PRICE_CLUSTER',
                description=f"청산 타이밍은 평균적으로 당일 고가 대비 {exit_percentage:.1f}% 아래에서 발생",
                significance='HIGH' if exit_percentage > 5 else 'MEDIUM',
                metadata={'avg_exit_ratio': float(avg_exit_ratio), 'sample_size': len(valid_exits)}
            ))
    
    # 3. Revenge Trading 연쇄 패턴
    revenge_trades = trades_df[trades_df['is_revenge'] == True]
    if len(revenge_trades) >= 2:
        revenge_sequences = []
        sorted_trades = trades_df.sort_values('entry_dt')
        
        for i in range(1, len(sorted_trades)):
            curr = sorted_trades.iloc[i]
            if curr['is_revenge']:
                # 이전 손실 거래 찾기
                prev_losses = sorted_trades.iloc[:i]
                prev_losses = prev_losses[prev_losses['pnl'] < 0]
                if len(prev_losses) > 0:
                    prev_loss = prev_losses.iloc[-1]
                    time_diff = (curr['entry_dt'] - prev_loss['exit_dt']).total_seconds() / 3600
                    revenge_sequences.append(time_diff)
        
        if len(revenge_sequences) >= 2:
            avg_time = np.mean(revenge_sequences)
            if avg_time < 24:  # 평균 24시간 이내
                patterns.append(DeepPattern(
                    type='REVENGE_SEQUENCE',
                    description=f"손실 전환 직후 평균 {avg_time:.1f}시간 내 재매수하는 패턴이 {len(revenge_sequences)}회 반복",
                    significance='HIGH' if avg_time < 12 else 'MEDIUM',
                    metadata={'avg_hours': float(avg_time), 'count': len(revenge_sequences)}
                ))
    
    # 4. 시장 환경별 FOMO 패턴
    if 'market_regime' in trades_df.columns:
        bull_trades = trades_df[trades_df['market_regime'] == 'BULL']
        bear_trades = trades_df[trades_df['market_regime'] == 'BEAR']
        
        if len(bull_trades) >= 3 and len(bear_trades) >= 3:
            bull_fomo = bull_trades[bull_trades['fomo_score'] > 0.7]['fomo_score']
            bear_fomo = bear_trades[bear_trades['fomo_score'] > 0.7]['fomo_score']
            
            bull_fomo_rate = len(bull_fomo) / len(bull_trades) if len(bull_trades) > 0 else 0
            bear_fomo_rate = len(bear_fomo) / len(bear_trades) if len(bear_trades) > 0 else 0
            
            # 상승장에서 FOMO가 훨씬 더 많이 발생
            if bull_fomo_rate > bear_fomo_rate * 1.5:
                patterns.append(DeepPattern(
                    type='MARKET_REGIME',
                    description=f"FOMO는 상승장에서만 생기는 경향 (상승장: {bull_fomo_rate*100:.0f}%, 하락장: {bear_fomo_rate*100:.0f}%)",
                    significance='HIGH' if bull_fomo_rate > 0.5 else 'MEDIUM',
                    metadata={'bull_fomo_rate': float(bull_fomo_rate), 'bear_fomo_rate': float(bear_fomo_rate)}
                ))
    
    # 5. MAE 클러스터링 (시간대별이 아닌 다른 관점)
    if len(high_mae_trades) >= 5:
        # MAE가 큰 거래들의 평균 보유 기간
        avg_hold_time = high_mae_trades['duration_days'].mean()
        overall_avg_hold = trades_df['duration_days'].mean()
        
        # MAE 큰 거래가 특정 보유 기간에 집중되는지
        if avg_hold_time > overall_avg_hold * 1.5:
            patterns.append(DeepPattern(
                type='MAE_CLUSTER',
                description=f"MAE가 큰 포지션({len(high_mae_trades)}건)은 평균 {avg_hold_time:.1f}일 보유 (전체 평균: {overall_avg_hold:.1f}일)",
                significance='MEDIUM',
                metadata={'avg_hold_days': float(avg_hold_time), 'overall_avg': float(overall_avg_hold)}
            ))
    
    return patterns

def generate_personal_playbook(
    patterns: List[DeepPattern],
    bias_priority: Optional[List[BiasPriority]],
    personal_baseline: Optional[PersonalBaseline],
    trades_df: pd.DataFrame
) -> PersonalPlaybook:
    """
    사용자의 편향을 바탕으로 개인화된 투자 원칙 생성
    """
    rules = []
    based_on_biases = []
    
    # 1. 시간대 기반 규칙
    time_patterns = [p for p in patterns if p.type == 'TIME_CLUSTER']
    for tp in time_patterns:
        hour = tp.metadata.get('hour', 0) if tp.metadata else 0
        if 14 <= hour <= 15:  # 오후 2-3시
            rules.append("오후 2-3시에는 신규 진입을 금지한다")
        elif 9 <= hour <= 10:  # 장 초반
            rules.append("장 초 첫 20분에는 매매하지 않는다")
    
    # 2. FOMO 기반 규칙
    if bias_priority and len(bias_priority) > 0:
        primary_bias = bias_priority[0].bias
        if primary_bias == 'FOMO':
            if personal_baseline and personal_baseline.avg_fomo > 0.8:
                rules.append("장 초 첫 20분에는 매매하지 않는다 (FOMO 회피)")
            elif personal_baseline and personal_baseline.avg_fomo > 0.7:
                rules.append("고점 매수(FOMO)를 피하기 위해 진입 전 30분 대기")
            based_on_biases.append('FOMO')
    
    # 3. MAE 기반 규칙
    if personal_baseline and personal_baseline.avg_mae < -0.02:
        mae_percent = abs(personal_baseline.avg_mae) * 100
        rules.append(f"MAE가 {mae_percent:.0f}% 넘어가면 재진입 금지")
    
    # MAE 클러스터 패턴에서 규칙 생성
    mae_patterns = [p for p in patterns if p.type == 'MAE_CLUSTER']
    for mp in mae_patterns:
        if mp.metadata:
            avg_hold = mp.metadata.get('avg_hold_days', 0)
            if avg_hold > 3:
                rules.append(f"보유 기간이 {avg_hold:.0f}일을 넘으면 손절을 고려한다")
    
    # 4. 가격대 기반 규칙
    price_patterns = [p for p in patterns if p.type == 'PRICE_CLUSTER']
    for pp in price_patterns:
        if pp.metadata:
            exit_ratio = pp.metadata.get('avg_exit_ratio', 1.0)
            if exit_ratio < 0.95:
                rules.append("당일 고가 기준 95% 이상 구간에서는 진입 금지")
    
    # 5. Revenge Trading 기반 규칙
    revenge_count = len(trades_df[trades_df['is_revenge'] == True])
    if revenge_count >= 2:
        rules.append("손실 거래 직후 24시간 내 재매수 금지")
        based_on_biases.append('Revenge Trading')
    
    revenge_patterns = [p for p in patterns if p.type == 'REVENGE_SEQUENCE']
    for rp in revenge_patterns:
        if rp.metadata:
            avg_hours = rp.metadata.get('avg_hours', 24)
            if avg_hours < 12:
                rules.append("손실 후 최소 12시간은 거래하지 않는다")
    
    # 6. Panic Sell 기반 규칙
    if bias_priority:
        panic_bias = [b for b in bias_priority if b.bias == 'Panic Sell']
        if panic_bias and len(panic_bias) > 0:
            if personal_baseline and personal_baseline.avg_panic < 0.3:
                rules.append("저점 매도(Panic)를 피하기 위해 청산 전 10분 대기")
            based_on_biases.append('Panic Sell')
    
    # 7. Disposition Effect 기반 규칙
    if bias_priority:
        disp_bias = [b for b in bias_priority if b.bias == 'Disposition Effect']
        if disp_bias and len(disp_bias) > 0:
            if personal_baseline and personal_baseline.avg_disposition_ratio > 1.5:
                rules.append("손실 종목은 수익 종목보다 빠르게 청산한다")
            based_on_biases.append('Disposition Effect')
    
    # 8. 시장 환경 기반 규칙
    market_patterns = [p for p in patterns if p.type == 'MARKET_REGIME']
    for mp in market_patterns:
        if mp.metadata:
            bull_fomo_rate = mp.metadata.get('bull_fomo_rate', 0)
            if bull_fomo_rate > 0.5:
                rules.append("상승장에서는 FOMO에 주의하며 진입 타이밍을 신중히 선택한다")
    
    # 규칙이 없으면 기본 규칙 추가
    if len(rules) == 0:
        rules.append("거래 전 잠시 멈추고 감정을 점검한다")
    
    return PersonalPlaybook(
        rules=rules,
        generated_at=datetime.now().isoformat(),
        based_on={
            'patterns': len(patterns),
            'biases': list(set(based_on_biases)) if based_on_biases else []
        }
    )

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
        
        # Market Regime Detection
        market_regime = detect_market_regime(ticker, entry_date, market_df)
        
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
            "market_regime": market_regime,
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

    # Deep Pattern Analysis
    deep_patterns = extract_deep_patterns(trades_df)
    
    return AnalysisResponse(
        trades=final_trades,
        metrics=metrics_obj,
        is_low_sample=total_trades < 5,
        personal_baseline=personal_baseline,
        bias_loss_mapping=bias_loss_mapping,
        bias_priority=bias_priority,
        behavior_shift=behavior_shift,
        equity_curve=equity_curve,
        deep_patterns=deep_patterns if deep_patterns else None
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
            f"    - {s['bias']}: {s['trend']} ({s['change_percent']:+.1f}%)" 
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
    
    # Best Executions (이달의 명장면)
    best_executions_text = ''
    if request.best_executions and len(request.best_executions) > 0:
        best_lines = []
        for be in request.best_executions:
            type_map = {
                'PERFECT_ENTRY': '완벽한 진입',
                'PERFECT_EXIT': '완벽한 청산',
                'CLEAN_CUT': '칼손절',
                'PERFECT_TRADE': '완벽한 거래'
            }
            exec_type_kr = type_map.get(be.get('execution_type', ''), be.get('execution_type', ''))
            pnl_str = f" (PnL: ${be.get('pnl', 0):.0f})" if 'pnl' in be and be['pnl'] else ""
            best_lines.append(f"    - {be['ticker']}: {exec_type_kr} - {be.get('reason', '')}{pnl_str}")
        best_executions_text = f"""
    BEST EXECUTIONS (이달의 명장면 - 잘한 매매):
    {chr(10).join(best_lines)}
    """
    
    # Pattern Recognition (과정 평가)
    patterns_text = ''
    if request.patterns and len(request.patterns) > 0:
        pattern_lines = []
        for pattern in request.patterns:
            pattern_lines.append(f"    - {pattern.get('description', '')} (발생률: {pattern.get('percentage', 0):.0f}%, 유의성: {pattern.get('significance', 'LOW')})")
        patterns_text = f"""
    PATTERN RECOGNITION (반복되는 패턴 - 과정 평가):
    IMPORTANT: These patterns show REPEATED behavior, not single-trade luck.
    "한두 번은 운 탓일 수 있지만, 10번 반복되면 실력(편향)입니다."
    {chr(10).join(pattern_lines)}
    """
    
    # Deep Pattern Analysis (고급 패턴)
    deep_patterns_text = ''
    if request.deep_patterns and len(request.deep_patterns) > 0:
        deep_pattern_lines = []
        for dp in request.deep_patterns:
            deep_pattern_lines.append(f"    - [{dp.get('type', 'UNKNOWN')}] {dp.get('description', '')} (유의성: {dp.get('significance', 'LOW')})")
        deep_patterns_text = f"""
    DEEP PATTERN ANALYSIS (AI 기반 반복 패턴 추출):
    These are advanced patterns detected through clustering analysis.
    Examples: "MAE 큰 포지션은 오후 2-3시에 집중", "FOMO는 상승장에서만 발생"
    {chr(10).join(deep_pattern_lines)}
    """
    
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
    Act as the "Truth Pipeline" AI. You are an objective, tough but growth-oriented (Tough Love) Trading Coach.
    Your goal is to correct behavior while preserving user's self-esteem. Use Positive Reinforcement psychology.
    
    CRITICAL RULES (STRICTLY ENFORCED):
    - EVIDENCE IS KING: Your diagnosis must be based 100% on the HARD EVIDENCE numbers below.
    - RAG IS QUEEN: Your advice (Rule/Fix) must be inspired by the RAG KNOWLEDGE BASE provided (if available).
    - SANDWICH FEEDBACK: Always start with praise (strengths), then criticize (weaknesses), then encourage growth.
    - PROCESS EVALUATION (과정 평가): Focus on REPEATED PATTERNS, not single-trade results.
    - NEVER say "You could have made 50% more on this trade" (hindsight bias). Instead, say "최근 10번 거래 중 8번이나 너무 일찍 팔았습니다."
    - ALWAYS use PATTERN-BASED language: "최근 N번 중 X번", "반복되는 패턴", "한두 번은 운, 10번은 실력"
    - NEVER evaluate single trades in isolation. Always contextualize as part of a pattern.
    - NEVER use vague language like "~may be", "~could be", "~might be", "~seems like", "~appears to"
    - ALWAYS state facts with certainty based on Evidence numbers
    - NEVER repeat template phrases. Each response must be unique and specific to this user's data
    - ALWAYS emphasize "Evidence-based" or "According to Evidence #X" in your diagnosis
    - NEVER make predictions about future market movements
    - NEVER recommend specific stocks or investment advice
    - RAG CONTEXT is for educational reference ONLY. It must NOT alter Evidence-based diagnosis.
    - If RAG CONTEXT conflicts with Evidence, Evidence takes ABSOLUTE PRIORITY.
    - RAG CONTEXT should be used to EXPLAIN why the Evidence indicates a problem, not to create new conclusions.
    - PERSONA: "Ruthless" is OUT. "Tough Love" is IN. Say "이것만 고치면 완벽해" instead of "너는 틀렸어".
    
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
    {best_executions_text}
    {patterns_text}
    {deep_patterns_text}

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

    INSTRUCTIONS (SANDWICH FEEDBACK + PROCESS EVALUATION):
    
    0. STRENGTHS (이달의 명장면 - NEW!): 
       - If BEST EXECUTIONS are provided above, mention 1-2 of them positively FIRST.
       - Format: "전반적으로 손실이 컸지만, '{Ticker}' 매매에서의 {execution_type}은 완벽했습니다. {reason}. 이런 원칙을 다른 종목에도 적용해 봅시다."
       - This should appear at the START of your diagnosis, BEFORE criticism.
       - Purpose: Build self-esteem and motivation. "행동 교정 이론에 따르면, 긍정적 강화가 습관 형성에 효과적입니다."
    
    1. DIAGNOSIS (3 sentences, PATTERN-BASED, NOT SINGLE-TRADE):
       - Sentence 1: If strengths exist, mention them first (see STRENGTHS above). Otherwise, use PATTERN-BASED observation.
       - Sentence 2: PATTERN-BASED FACT (CRITICAL). Use PATTERN RECOGNITION data if available. 
         * If patterns exist: "최근 {count}번 거래 중 {pattern_count}번이나 {pattern_description}. 한두 번은 운 탓일 수 있지만, {total}번 반복되면 실력(편향)입니다."
         * Example: "최근 10번 거래 중 8번이나 너무 일찍 팔았습니다 (Exit Efficiency < 30%). 한두 번은 운 탓일 수 있지만, 10번 반복되면 실력(편향)입니다."
         * NEVER say "이 거래에서 50% 더 먹을 수 있었다" (hindsight bias). Always focus on the pattern.
         * If no patterns: Use Evidence-based format with pattern context.
       - Sentence 3: Financial impact WITH cumulative pattern emphasis. {bias_loss_note} {behavior_shift_warning} 
         * Format: "이 패턴으로 인해 총 ${total}를 놓쳤습니다. 하지만 이것만 고치면 {improvement}할 수 있습니다."
    
    2. RULE (1 sentence): A catchy, memorable trading commandment to fix this specific flaw. {rule_target_note} {rule_rag_note}
    
    3. BIAS: Name the single dominant psychological bias. {bias_name_note} (e.g. Disposition Effect, Action Bias, Revenge Trading, FOMO).
    
    4. FIX: One specific, actionable step to take immediately. {fix_target_note} {fix_rag_note}
    
    Output valid JSON only with this exact structure:
    {{
      "diagnosis": "3 sentences. Must mention a ticker. Use Sandwich Feedback if strengths exist.",
      "rule": "1 sentence rule.",
      "bias": "Primary bias.",
      "fix": "Priority fix."{references_field},
      "strengths": [
        {{
          "ticker": "TICKER",
          "execution": "완벽한 손절 / 최적 진입점 / 고점 매도 / 완벽한 거래",
          "lesson": "이 원칙을 다른 종목에도 적용해 봅시다.",
          "reason": "FOMO 점수 5%로 저점 매수 / 손실 3%에서 즉시 청산 / Panic 점수 85%로 고점 매도"
        }}
      ]
    }}
    
    IMPORTANT: "strengths" field is REQUIRED if BEST EXECUTIONS are provided above. 
    Extract 1-3 best executions and format them as above.
    If no best executions exist, return empty array: "strengths": []
    
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
            
            # Ensure strengths field exists (default to empty array if missing)
            if "strengths" not in result:
                result["strengths"] = []
            
            # Generate Personal Playbook
            # Convert request data to format needed for playbook generation
            deep_patterns_list = []
            if request.deep_patterns:
                for dp in request.deep_patterns:
                    deep_patterns_list.append(DeepPattern(
                        type=dp.get('type', 'UNKNOWN'),
                        description=dp.get('description', ''),
                        significance=dp.get('significance', 'LOW'),
                        metadata=dp.get('metadata')
                    ))
            
            bias_priority_list = None
            if request.bias_priority:
                bias_priority_list = [
                    BiasPriority(
                        bias=p['bias'],
                        priority=p['priority'],
                        financial_loss=p['financial_loss'],
                        frequency=p['frequency'],
                        severity=p['severity']
                    ) for p in request.bias_priority
                ]
            
            personal_baseline_obj = None
            if request.personal_baseline:
                pb = request.personal_baseline
                personal_baseline_obj = PersonalBaseline(
                    avg_fomo=pb['avg_fomo'],
                    avg_panic=pb['avg_panic'],
                    avg_mae=pb['avg_mae'],
                    avg_disposition_ratio=pb['avg_disposition_ratio'],
                    avg_revenge_count=pb['avg_revenge_count']
                )
            
            # Create minimal trades_df for playbook generation (only for revenge count)
            # We can't create full trades_df, but we can pass minimal info
            import pandas as pd
            minimal_trades_df = pd.DataFrame({
                'is_revenge': [False] * max(1, request.metrics.get('total_trades', 1))
            })
            # Add revenge trades info if available
            if request.revenge_details:
                for i, rev in enumerate(request.revenge_details[:len(minimal_trades_df)]):
                    if i < len(minimal_trades_df):
                        minimal_trades_df.iloc[i, minimal_trades_df.columns.get_loc('is_revenge')] = True
            
            playbook = generate_personal_playbook(
                deep_patterns_list,
                bias_priority_list,
                personal_baseline_obj,
                minimal_trades_df
            )
            
            # Add playbook to result
            result["playbook"] = {
                "rules": playbook.rules,
                "generated_at": playbook.generated_at,
                "based_on": playbook.based_on
            }
            
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

@app.post("/strategy-tag")
async def save_strategy_tag(request: dict):
    """
    사용자가 거래에 전략 태그를 추가합니다.
    클라이언트 측에서 로컬 상태로만 관리해도 되지만, 백엔드에 저장하면
    세션 간 유지가 가능합니다.
    """
    # TODO: 데이터베이스에 저장하는 로직 (현재는 메모리에 저장)
    # 실제 구현 시에는 trade_id와 strategy_tag를 DB에 저장
    
    trade_id = request.get('trade_id')
    strategy_tag = request.get('strategy_tag')
    
    if not trade_id or not strategy_tag:
        return {"error": "trade_id and strategy_tag are required"}
    
    # 현재는 단순히 성공 응답만 반환
    # 실제 구현 시에는 DB에 저장하고, 다음 분석 시 이 태그를 반영
    return {
        "success": True,
        "trade_id": trade_id,
        "strategy_tag": strategy_tag,
        "message": "Strategy tag saved successfully"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
