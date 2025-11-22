from typing import List, Optional
from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    pass

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
    
    market_regime: str = "UNKNOWN"
    is_revenge: bool = False
    
    strategy_tag: Optional[str] = None
    user_acknowledged: bool = False
    
    fomo_score: float = -1.0
    panic_score: float = -1.0
    mae: float = 0.0
    mfe: float = 0.0
    efficiency: float = 0.0
    regret: float = 0.0
    
    entry_day_high: float = 0.0
    entry_day_low: float = 0.0
    exit_day_high: float = 0.0
    exit_day_low: float = 0.0

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
    bias: str
    priority: int
    financial_loss: float
    frequency: float
    severity: float

class BehaviorShift(BaseModel):
    bias: str
    recent_value: float
    baseline_value: float
    change_percent: float
    trend: str

class EquityCurvePoint(BaseModel):
    date: str
    cumulative_pnl: float
    fomo_score: Optional[float] = None
    panic_score: Optional[float] = None
    is_revenge: bool
    ticker: str
    pnl: float

class DeepPattern(BaseModel):
    type: str
    description: str
    significance: str
    metadata: Optional[dict] = None

class PersonalPlaybook(BaseModel):
    rules: List[str]
    generated_at: str
    based_on: dict

class AnalysisResponse(BaseModel):
    trades: List[EnrichedTrade]
    metrics: BehavioralMetrics
    is_low_sample: bool
    personal_baseline: Optional[PersonalBaseline] = None
    bias_loss_mapping: Optional[BiasLossMapping] = None
    bias_priority: Optional[List[BiasPriority]] = None
    behavior_shift: Optional[List[BehaviorShift]] = None
    equity_curve: List[EquityCurvePoint] = []
    deep_patterns: Optional[List[DeepPattern]] = None

class CoachRequest(BaseModel):
    top_regrets: List[dict]
    revenge_details: List[dict]
    best_executions: List[dict]
    patterns: List[dict]
    deep_patterns: Optional[List[dict]] = None
    metrics: dict
    is_low_sample: bool
    personal_baseline: Optional[dict] = None
    bias_loss_mapping: Optional[dict] = None
    bias_priority: Optional[List[dict]] = None
    behavior_shift: Optional[List[dict]] = None