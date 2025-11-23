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
    
    # Contextual Score 분해 필드 (조건부 포함)
    # Base Score: volume/regime 가중치 적용 전 순수 심리 지표 기반 점수
    base_score: Optional[float] = None
    # Volume Weight: 거래량 가중치 (1.0, 1.2, 1.5)
    volume_weight: Optional[float] = None
    # Regime Weight: 시장 국면 가중치 (0.8, 1.0, 1.5)
    regime_weight: Optional[float] = None
    # Contextual Score: base_score * volume_weight * regime_weight (표시용, 0~150 clamp)
    contextual_score: Optional[float] = None

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
    trade_id: Optional[str] = None  # 거래 ID (클릭 인터랙션용)
    base_score: Optional[float] = None  # 분해 필드
    volume_weight: Optional[float] = None
    regime_weight: Optional[float] = None
    contextual_score: Optional[float] = None
    market_regime: Optional[str] = None  # 툴팁용

class DeepPattern(BaseModel):
    type: str
    description: str
    significance: str
    metadata: Optional[dict] = None

class PersonalPlaybook(BaseModel):
    # 3A: 3단계 고정 구조로 변경
    plan_step_1: str  # 첫 번째 행동 계획 (숫자 인용 필수)
    plan_step_2: str  # 두 번째 행동 계획 (숫자 인용 필수)
    plan_step_3: str  # 세 번째 행동 계획 (숫자 인용 필수)
    generated_at: str
    based_on: dict
    # 하위 호환성을 위한 rules 필드 (deprecated)
    rules: Optional[List[str]] = None

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

class NewsVerification(BaseModel):
    """뉴스 검증 결과"""
    verdict: str  # "GUILTY" | "INNOCENT" | "UNKNOWN"
    reasoning: str  # 판단 근거 (한국어)
    confidence: str  # "HIGH" | "MEDIUM" | "LOW"
    news_titles: List[str]  # 참조한 뉴스 헤드라인
    source: str  # "cache" | "search" | "none"
    relevance_check: Optional[str] = None  # "RELEVANT" | "IRRELEVANT"
    relevant_count: Optional[int] = None

class NewsVerificationRequest(BaseModel):
    """뉴스 검증 요청"""
    ticker: str
    date: str
    fomo_score: float

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