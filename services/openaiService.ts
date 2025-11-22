import { AnalysisResult, AIAnalysis, BehavioralMetrics, PersonalBaseline, BiasLossMapping } from "../types";

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

interface CoachRequestPayload {
  top_regrets: Array<{ ticker: string; regret: number }>;
  revenge_details: Array<{ ticker: string; pnl: number }>;
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

  return {
    top_regrets: topRegrets,
    revenge_details: revengeDetails,
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

