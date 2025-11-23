
export enum AnalysisStatus {
  IDLE = 'IDLE',
  ANALYZING = 'ANALYZING',
  COMPLETE = 'COMPLETE',
  ERROR = 'ERROR'
}

export type MarketRegime = 'BULL' | 'BEAR' | 'SIDEWAYS' | 'UNKNOWN';

export interface RawCsvRow {
  ticker: string;
  date: string;
  action: 'BUY' | 'SELL'; // Used for Log format
  price: number;
  qty: number;
  // Optional for Paired format compatibility
  exitDate?: string;
  exitPrice?: number;
}

export interface EnrichedTrade {
  id: string;
  ticker: string;
  entryDate: string;
  entryPrice: number;
  exitDate: string;
  exitPrice: number;
  qty: number;
  
  pnl: number;
  returnPct: number;
  durationDays: number;
  
  // Real/Simulated market data metrics
  entryDayHigh: number;
  entryDayLow: number;
  exitDayHigh: number;
  exitDayLow: number;
  holdingHigh?: number; // For MFE
  holdingLow?: number; // For MAE
  postExitHigh3Day: number; // For Regret
  
  // Context flags
  marketRegime: MarketRegime;
  isRevenge: boolean;
  
  // Strategy Tagging (사용자 피드백)
  strategyTag?: 'BREAKOUT' | 'AGGRESSIVE_ENTRY' | 'FOMO' | 'PLANNED_CUT' | null; // 전략 태그
  userAcknowledged?: boolean; // 사용자가 소명했는지 여부
  
  // Computed Trade Metrics
  fomoScore: number; // 0-1 (Entry relative to day range, 1 = Bought Top)
  panicScore: number; // 0-1 (Exit relative to day range, 0 = Sold Bottom)
  mae: number; // Max Adverse Excursion %
  mfe: number; // Max Favorable Excursion %
  efficiency: number; // Captured move %
  regret: number; // Missed profit $
  
  // Contextual Score 분해 필드 (조건부 포함)
  baseScore?: number | null; // volume/regime 가중치 적용 전 순수 심리 지표 기반 점수
  volumeWeight?: number | null; // 거래량 가중치 (1.0, 1.2, 1.5)
  regimeWeight?: number | null; // 시장 국면 가중치 (0.8, 1.0, 1.5)
  contextualScore?: number | null; // baseScore * volumeWeight * regimeWeight (표시용, 0~150 clamp)
}

export interface BehavioralMetrics {
  totalTrades: number;
  winRate: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  
  // Advanced
  fomoIndex: number; // Avg FOMO score
  panicIndex: number; // Avg Panic score
  dispositionRatio: number; // Holding winners vs losers duration ratio
  revengeTradingCount: number; // Trades entered < 24h after a loss on same ticker
  
  // Risk/Return
  sharpeRatio: number;
  sortinoRatio: number;
  alpha: number; // Vs Benchmark (simulated)
  maxDrawdown: number; // Maximum Drawdown (%)
  
  // Simulation
  luckPercentile: number; // Monte Carlo result (0-100)
  
  // Aggregates
  totalRegret: number; // Total money left on table
  truthScore: number; // Composite score 0-100
}

export interface RAGReference {
  title: string;
  definition: string;  // 학술적/심리적 개념 설명
  connection: string;  // 시스템 지표와의 연결 (지표 명칭 포함 필수)
  prescription: string;  // 구체적인 행동 지침
}

export interface TradeStrength {
  ticker: string;
  execution: string; // "완벽한 손절", "최적 진입점", "고점 매도" 등
  lesson: string; // "이 원칙을 다른 종목에도..."
  reason: string; // "FOMO 점수 5%로 저점 매수", "손실 3%에서 즉시 청산" 등
}

export interface DeepPattern {
  type: 'TIME_CLUSTER' | 'PRICE_CLUSTER' | 'REVENGE_SEQUENCE' | 'MARKET_REGIME' | 'MAE_CLUSTER';
  description: string;
  significance: 'HIGH' | 'MEDIUM' | 'LOW';
  metadata?: Record<string, any>; // Additional context (hour, percentage, etc.)
}

export interface PersonalPlaybook {
  // 3A: 3단계 고정 구조
  plan_step_1: string;  // 첫 번째 행동 계획 (숫자 인용 필수)
  plan_step_2: string;  // 두 번째 행동 계획 (숫자 인용 필수)
  plan_step_3: string;  // 세 번째 행동 계획 (숫자 인용 필수)
  generated_at: string;
  based_on: {
    primary_bias?: string;
    patterns: number;
    biases: string[];
  };
  // 하위 호환성을 위한 rules 필드 (deprecated)
  rules?: string[];
}

export interface NewsVerification {
  verdict: 'GUILTY' | 'INNOCENT' | 'UNKNOWN'; // 판결
  reasoning: string; // 판단 근거 (한국어)
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'; // 확신도
  newsTitles: string[]; // 참조한 뉴스 헤드라인
  source: 'cache' | 'search' | 'none'; // 데이터 출처
  relevanceCheck?: 'RELEVANT' | 'IRRELEVANT'; // 뉴스 적합성
  relevantCount?: number; // 적합한 뉴스 개수
}

export interface AIAnalysis {
  diagnosis: string; // 3 sentences
  rule: string; // 1 sentence behavioral rule
  bias: string; // Primary bias
  fix: string; // Priority fix
  references?: RAGReference[]; // RAG 카드 (옵션)
  strengths?: TradeStrength[]; // 잘한 매매 (이달의 명장면)
  deep_patterns?: DeepPattern[]; // 고급 패턴 분석
  playbook?: PersonalPlaybook; // Personal Playbook
  newsVerification?: NewsVerification; // 뉴스 검증 결과 (별도 API 호출)
}

// Perfect Edition: Personal Baseline
export interface PersonalBaseline {
  avgFomo: number; // 평균 FOMO 점수
  avgPanic: number; // 평균 Panic 점수
  avgMae: number; // 평균 MAE
  avgDispositionRatio: number; // 평균 Disposition Ratio
  avgRevengeCount: number; // 평균 Revenge Trading 횟수
}

// Perfect Edition: Bias Loss Mapping
export interface BiasLossMapping {
  fomoLoss: number; // FOMO로 인한 손실 금액
  panicLoss: number; // Panic Sell로 인한 손실 금액
  revengeLoss: number; // Revenge Trading으로 인한 손실 금액
  dispositionLoss: number; // Disposition Effect로 놓친 수익
}

// Bias-Free Metrics (기회비용 반영)
export interface BiasFreeMetrics {
  currentPnL: number; // 현재 총 손익
  potentialPnL: number; // 편향 제거 후 잠재 손익
  biasLoss: number; // 편향으로 인한 직접 손실
  opportunityCost: number; // 벤치마크 대비 기회비용 (음수면 기회 상실)
  adjustedImprovement: number; // 실제 개선액 (기회비용 반영)
}

// Perfect Edition: Bias Priority
export interface BiasPriority {
  bias: 'FOMO' | 'Panic Sell' | 'Revenge Trading' | 'Disposition Effect';
  priority: number; // 1 = 최우선
  financialLoss: number; // 금전 피해
  frequency: number; // 발생 빈도
  severity: number; // 심각도 (0-1)
}

// Perfect Edition: Behavior Shift
export interface BehaviorShift {
  bias: 'FOMO' | 'Panic Sell' | 'Revenge Trading' | 'Disposition Effect';
  recentValue: number; // 최근 3건 평균
  baselineValue: number; // 기존 평균
  changePercent: number; // 변화율 (%)
  trend: 'IMPROVING' | 'WORSENING' | 'STABLE'; // 개선/악화/안정
}

// Pattern Recognition (과정 평가)
export interface PatternMetric {
  pattern: 'FOMO' | 'EXIT_EFFICIENCY' | 'EARLY_EXIT' | 'REVENGE' | 'DISPOSITION';
  description: string; // "최근 10번 거래 중 8번이나..."
  count: number; // 패턴 발생 횟수
  total: number; // 전체 거래 수 (분모)
  percentage: number; // 발생 비율
  significance: 'HIGH' | 'MEDIUM' | 'LOW'; // 통계적 유의성
}

export interface EquityCurvePoint {
  date: string;
  cumulative_pnl: number;
  fomo_score?: number | null;
  panic_score?: number | null;
  is_revenge: boolean;
  ticker: string;
  pnl: number;
  trade_id?: string | null;  // 거래 ID (클릭 인터랙션용)
  base_score?: number | null;  // 분해 필드
  volume_weight?: number | null;
  regime_weight?: number | null;
  contextual_score?: number | null;
  market_regime?: string | null;  // 툴팁용
  benchmark_cumulative_pnl?: number | null;  // SPY 누적 수익률
}

export interface AnalysisResult {
  trades: EnrichedTrade[];
  metrics: BehavioralMetrics;
  isLowSample: boolean;
  revengeTrades: EnrichedTrade[]; // Specific trades for AI to critique
  dataSource: 'BACKEND_TRUTH' | 'CLIENT_DEMO';
  
  // Perfect Edition
  personalBaseline?: PersonalBaseline;
  biasLossMapping?: BiasLossMapping;
  biasFreeMetrics?: BiasFreeMetrics; // 기회비용 반영 시뮬레이션
  biasPriority?: BiasPriority[];
  behaviorShift?: BehaviorShift[];
  equityCurve?: EquityCurvePoint[];
  
  // Pattern Recognition (과정 평가)
  patterns?: PatternMetric[]; // 반복되는 패턴 감지
  
  // Deep Pattern Analysis (고급 패턴)
  deepPatterns?: DeepPattern[]; // AI 기반 반복 패턴 추출
  benchmarkLoadFailed?: boolean;  // SPY 데이터 로드 실패 여부
}
