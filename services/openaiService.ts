import { AnalysisResult, AIAnalysis, BehavioralMetrics, PersonalBaseline, BiasLossMapping, EnrichedTrade, TradeStrength, PatternMetric } from "../types";

/**
 * 타입 안전한 매퍼 함수들
 * 백엔드 snake_case와 프론트엔드 camelCase 간의 변환을 중앙 집중화
 */

interface CoachRequestMetrics {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  fomo_score: number;
  panic_score: number;
  disposition_ratio: number;
  revenge_trading_count: number;
  truth_score: number;
  total_regret: number;
}

interface CoachRequestPersonalBaseline {
  avg_fomo: number;
  avg_panic: number;
  avg_mae: number;
  avg_disposition_ratio: number;
  avg_revenge_count: number;
}

interface CoachRequestBiasLossMapping {
  fomo_loss: number;
  panic_loss: number;
  revenge_loss: number;
  disposition_loss: number;
}

interface BestExecution {
  ticker: string;
  execution_type: string; // "PERFECT_ENTRY", "PERFECT_EXIT", "CLEAN_CUT", "PERFECT_TRADE"
  fomo_score?: number;
  panic_score?: number;
  pnl?: number;
  reason: string; // 설명
}

interface CoachRequestPayload {
  top_regrets: Array<{ ticker: string; regret: number }>;
  revenge_details: Array<{ ticker: string; pnl: number }>;
  best_executions: Array<BestExecution>; // 잘한 매매
  patterns: Array<PatternMetric>; // 반복되는 패턴
  metrics: CoachRequestMetrics;
  is_low_sample: boolean;
  personal_baseline: CoachRequestPersonalBaseline | null;
  bias_loss_mapping: CoachRequestBiasLossMapping | null;
  bias_priority: AnalysisResult['biasPriority'];
  behavior_shift: AnalysisResult['behaviorShift'];
}

/**
 * BehavioralMetrics를 백엔드 형식으로 변환
 */
const mapMetricsToBackend = (metrics: BehavioralMetrics): CoachRequestMetrics => {
  return {
    total_trades: metrics.totalTrades,
    win_rate: metrics.winRate,
    profit_factor: metrics.profitFactor,
    fomo_score: metrics.fomoIndex,
    panic_score: metrics.panicIndex,
    disposition_ratio: metrics.dispositionRatio,
    revenge_trading_count: metrics.revengeTradingCount,
    truth_score: metrics.truthScore,
    total_regret: metrics.totalRegret,
  };
};

/**
 * PersonalBaseline을 백엔드 형식으로 변환
 */
const mapPersonalBaselineToBackend = (
  baseline: PersonalBaseline
): CoachRequestPersonalBaseline => {
  return {
    avg_fomo: baseline.avgFomo,
    avg_panic: baseline.avgPanic,
    avg_mae: baseline.avgMae,
    avg_disposition_ratio: baseline.avgDispositionRatio,
    avg_revenge_count: baseline.avgRevengeCount,
  };
};

/**
 * BiasLossMapping을 백엔드 형식으로 변환
 */
const mapBiasLossMappingToBackend = (
  mapping: BiasLossMapping
): CoachRequestBiasLossMapping => {
  return {
    fomo_loss: mapping.fomoLoss,
    panic_loss: mapping.panicLoss,
    revenge_loss: mapping.revengeLoss,
    disposition_loss: mapping.dispositionLoss,
  };
};

/**
 * Best Execution 찾기 (이달의 명장면)
 * 잘한 매매를 자동으로 발굴합니다.
 */
const findBestExecutions = (trades: EnrichedTrade[]): BestExecution[] => {
  if (trades.length === 0) return [];

  const validTrades = trades.filter(t => t.fomoScore !== -1 && t.panicScore !== -1);
  if (validTrades.length === 0) return [];

  const bestExecutions: BestExecution[] = [];

  // 1. 완벽한 진입 (최저 FOMO 점수)
  const bestEntry = [...validTrades]
    .filter(t => t.fomoScore !== -1)
    .sort((a, b) => a.fomoScore - b.fomoScore)[0];
  
  if (bestEntry && bestEntry.fomoScore < 0.3) {
    bestExecutions.push({
      ticker: bestEntry.ticker,
      execution_type: "PERFECT_ENTRY",
      fomo_score: bestEntry.fomoScore,
      pnl: bestEntry.pnl,
      reason: `FOMO 점수 ${(bestEntry.fomoScore * 100).toFixed(0)}%로 저점 매수`
    });
  }

  // 2. 완벽한 청산 (최고 Panic 점수 - panicScore가 높을수록 고점 매도)
  const bestExit = [...validTrades]
    .filter(t => t.panicScore !== -1)
    .sort((a, b) => b.panicScore - a.panicScore)[0];
  
  if (bestExit && bestExit.panicScore > 0.7) {
    bestExecutions.push({
      ticker: bestExit.ticker,
      execution_type: "PERFECT_EXIT",
      panic_score: bestExit.panicScore,
      pnl: bestExit.pnl,
      reason: `Panic 점수 ${(bestExit.panicScore * 100).toFixed(0)}%로 고점 매도`
    });
  }

  // 3. 칼손절 (손실이 작고 빠른 청산)
  const cleanCuts = validTrades
    .filter(t => t.pnl < 0 && Math.abs(t.pnl) < 100 && t.durationDays < 1 && t.panicScore !== -1 && t.panicScore < 0.4)
    .sort((a, b) => a.durationDays - b.durationDays);
  
  if (cleanCuts.length > 0) {
    const cleanest = cleanCuts[0];
    bestExecutions.push({
      ticker: cleanest.ticker,
      execution_type: "CLEAN_CUT",
      panic_score: cleanest.panicScore,
      pnl: cleanest.pnl,
      reason: `손실 ${Math.abs(cleanest.pnl).toFixed(0)}달러, ${cleanest.durationDays.toFixed(1)}일 내 칼손절`
    });
  }

  // 4. 완벽한 거래 (진입 + 청산 모두 우수)
  const perfectTrades = validTrades.filter(t => 
    t.fomoScore < 0.3 && t.panicScore > 0.7 && t.pnl > 0
  );
  
  if (perfectTrades.length > 0) {
    const best = perfectTrades.sort((a, b) => b.pnl - a.pnl)[0];
    bestExecutions.push({
      ticker: best.ticker,
      execution_type: "PERFECT_TRADE",
      fomo_score: best.fomoScore,
      panic_score: best.panicScore,
      pnl: best.pnl,
      reason: `저점 매수(${(best.fomoScore * 100).toFixed(0)}%) + 고점 매도(${(best.panicScore * 100).toFixed(0)}%)`
    });
  }

  // 최대 3개만 반환
  return bestExecutions.slice(0, 3);
};

/**
 * 패턴 인식 (과정 평가)
 * 최근 N건 거래를 분석하여 반복되는 패턴을 감지합니다.
 */
const detectPatterns = (trades: EnrichedTrade[]): PatternMetric[] => {
  if (trades.length < 3) return []; // 최소 3건 필요

  const validTrades = trades.filter(t => t.fomoScore !== -1 && t.panicScore !== -1);
  if (validTrades.length < 3) return [];

  // 시간순 정렬 (최신순)
  const sortedTrades = [...validTrades].sort((a, b) => 
    new Date(b.entryDate).getTime() - new Date(a.entryDate).getTime()
  );

  // 최근 10건 (또는 전체가 10건 미만이면 전체)
  const recentCount = Math.min(10, sortedTrades.length);
  const recentTrades = sortedTrades.slice(0, recentCount);

  const patterns: PatternMetric[] = [];

  // 1. FOMO 패턴 (최근 N건 중 FOMO > 70%인 횟수)
  const fomoCount = recentTrades.filter(t => t.fomoScore > 0.7).length;
  const fomoPercentage = (fomoCount / recentCount) * 100;
  if (fomoCount >= 5) { // 5건 이상이면 의미있는 패턴
    patterns.push({
      pattern: 'FOMO',
      description: `최근 ${recentCount}번 거래 중 ${fomoCount}번이나 고점 매수(FOMO > 70%)`,
      count: fomoCount,
      total: recentCount,
      percentage: fomoPercentage,
      significance: fomoPercentage >= 70 ? 'HIGH' : fomoPercentage >= 50 ? 'MEDIUM' : 'LOW'
    });
  }

  // 2. Exit Efficiency 패턴 (Panic Score < 30%, 이전에는 Panic이었지만 이제는 Exit Efficiency)
  const lowExitCount = recentTrades.filter(t => t.panicScore < 0.3).length;
  const exitPercentage = (lowExitCount / recentCount) * 100;
  if (lowExitCount >= 5) {
    patterns.push({
      pattern: 'EXIT_EFFICIENCY',
      description: `최근 ${recentCount}번 거래 중 ${lowExitCount}번이나 저점 매도(Exit Efficiency < 30%)`,
      count: lowExitCount,
      total: recentCount,
      percentage: exitPercentage,
      significance: exitPercentage >= 70 ? 'HIGH' : exitPercentage >= 50 ? 'MEDIUM' : 'LOW'
    });
  }

  // 3. Early Exit 패턴 (Regret이 있는 거래 - 너무 일찍 파는 경향)
  const regretTrades = recentTrades.filter(t => (t.regret || 0) > 0);
  const earlyExitCount = regretTrades.length;
  const earlyExitPercentage = (earlyExitCount / recentCount) * 100;
  if (earlyExitCount >= 5) {
    patterns.push({
      pattern: 'EARLY_EXIT',
      description: `최근 ${recentCount}번 거래 중 ${earlyExitCount}번이나 너무 일찍 팔았습니다 (누적 Regret: $${regretTrades.reduce((sum, t) => sum + (t.regret || 0), 0).toFixed(0)})`,
      count: earlyExitCount,
      total: recentCount,
      percentage: earlyExitPercentage,
      significance: earlyExitPercentage >= 70 ? 'HIGH' : earlyExitPercentage >= 50 ? 'MEDIUM' : 'LOW'
    });
  }

  // 4. Revenge Trading 패턴
  const revengeCount = recentTrades.filter(t => t.isRevenge).length;
  const revengePercentage = (revengeCount / recentCount) * 100;
  if (revengeCount >= 2) { // Revenge는 2건만 있어도 패턴
    patterns.push({
      pattern: 'REVENGE',
      description: `최근 ${recentCount}번 거래 중 ${revengeCount}번이나 복수 매매(Revenge Trading)`,
      count: revengeCount,
      total: recentCount,
      percentage: revengePercentage,
      significance: revengeCount >= 3 ? 'HIGH' : 'MEDIUM'
    });
  }

  // 5. Disposition Effect 패턴 (손익거래별 보유 기간 분석)
  const winners = recentTrades.filter(t => t.pnl > 0);
  const losers = recentTrades.filter(t => t.pnl <= 0);
  if (winners.length >= 2 && losers.length >= 2) {
    const avgWinHold = winners.reduce((sum, t) => sum + t.durationDays, 0) / winners.length;
    const avgLossHold = losers.reduce((sum, t) => sum + t.durationDays, 0) / losers.length;
    const dispositionRatio = avgWinHold > 0 ? avgLossHold / avgWinHold : 0;
    
    if (dispositionRatio > 1.5) {
      patterns.push({
        pattern: 'DISPOSITION',
        description: `최근 거래에서 손실 종목을 수익 종목보다 ${dispositionRatio.toFixed(1)}배 더 오래 보유하는 패턴`,
        count: losers.length,
        total: recentCount,
        percentage: (losers.length / recentCount) * 100,
        significance: dispositionRatio > 2.0 ? 'HIGH' : 'MEDIUM'
      });
    }
  }

  // 유의성 순으로 정렬 (HIGH -> MEDIUM -> LOW)
  const significanceOrder = { 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 };
  patterns.sort((a, b) => significanceOrder[b.significance] - significanceOrder[a.significance]);

  // 최대 3개만 반환
  return patterns.slice(0, 3);
};

/**
 * AnalysisResult를 백엔드 요청 페이로드로 변환
 */
const mapAnalysisResultToCoachRequest = (data: AnalysisResult): CoachRequestPayload => {
  // Top 3 regrets만 계산 (백엔드로 전송할 최소 데이터)
  const topRegrets = [...data.trades]
    .sort((a, b) => (b.regret || 0) - (a.regret || 0))
    .slice(0, 3)
    .map(t => ({
      ticker: t.ticker,
      regret: t.regret || 0,
    }));

  // Revenge trades 요약 정보만
  const revengeDetails = data.trades
    .filter(t => t.isRevenge)
    .map(t => ({
      ticker: t.ticker,
      pnl: t.pnl,
    }));

  // Best Executions 찾기
  const bestExecutions = findBestExecutions(data.trades);

  // 패턴 인식 (또는 이미 계산된 패턴 사용)
  const patterns = data.patterns || detectPatterns(data.trades);

  return {
    top_regrets: topRegrets,
    revenge_details: revengeDetails,
    best_executions: bestExecutions,
    patterns: patterns,
    metrics: mapMetricsToBackend(data.metrics),
    is_low_sample: data.isLowSample,
    personal_baseline: data.personalBaseline 
      ? mapPersonalBaselineToBackend(data.personalBaseline)
      : null,
    bias_loss_mapping: data.biasLossMapping 
      ? mapBiasLossMappingToBackend(data.biasLossMapping)
      : null,
    bias_priority: data.biasPriority,
    behavior_shift: data.behaviorShift,
  };
};

export const getAIInterpretation = async (data: AnalysisResult): Promise<AIAnalysis> => {
  // 백엔드 /coach 엔드포인트 호출
  // 최적화: trades 전체 대신 top_regrets만 전송 (데이터 핑퐁 구조 제거)
  try {
    const requestPayload = mapAnalysisResultToCoachRequest(data);

    const response = await fetch('http://localhost:8000/coach', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestPayload),
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }

    const result = await response.json();
    return result as AIAnalysis;
  } catch (error) {
    console.error("Backend Coach API Error:", error);
    return {
      diagnosis: "AI Analysis unavailable. Please ensure the backend server is running.",
      rule: "Cut losers faster than you think.",
      bias: "Service Error",
      fix: "Check backend connection."
    };
  }
};

