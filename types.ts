
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
  
  // Computed Trade Metrics
  fomoScore: number; // 0-1 (Entry relative to day range, 1 = Bought Top)
  panicScore: number; // 0-1 (Exit relative to day range, 0 = Sold Bottom)
  mae: number; // Max Adverse Excursion %
  mfe: number; // Max Favorable Excursion %
  efficiency: number; // Captured move %
  regret: number; // Missed profit $
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
  
  // Simulation
  luckPercentile: number; // Monte Carlo result (0-100)
  
  // Aggregates
  totalRegret: number; // Total money left on table
  truthScore: number; // Composite score 0-100
}

export interface AIAnalysis {
  diagnosis: string; // 3 sentences
  rule: string; // 1 sentence behavioral rule
  bias: string; // Primary bias
  fix: string; // Priority fix
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

export interface EquityCurvePoint {
  date: string;
  cumulative_pnl: number;
  fomo_score?: number | null;
  panic_score?: number | null;
  is_revenge: boolean;
  ticker: string;
  pnl: number;
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
  biasPriority?: BiasPriority[];
  behaviorShift?: BehaviorShift[];
  equityCurve?: EquityCurvePoint[];
}
