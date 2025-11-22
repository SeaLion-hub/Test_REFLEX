import { AnalysisResult, AIAnalysis } from "../types";

export const getAIInterpretation = async (data: AnalysisResult): Promise<AIAnalysis> => {
  // 백엔드 /coach 엔드포인트 호출
  try {
    const response = await fetch('http://localhost:8000/coach', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trades: data.trades.map(t => ({
          ticker: t.ticker,
          entry_date: t.entryDate,
          entry_price: t.entryPrice,
          exit_date: t.exitDate,
          exit_price: t.exitPrice,
          qty: t.qty,
          pnl: t.pnl,
          regret: t.regret,
          is_revenge: t.isRevenge,
        })),
        metrics: {
          total_trades: data.metrics.totalTrades,
          win_rate: data.metrics.winRate,
          profit_factor: data.metrics.profitFactor,
          fomo_score: data.metrics.fomoIndex,
          panic_score: data.metrics.panicIndex,
          disposition_ratio: data.metrics.dispositionRatio,
          revenge_trading_count: data.metrics.revengeTradingCount,
          truth_score: data.metrics.truthScore,
          total_regret: data.metrics.totalRegret,
        },
        is_low_sample: data.isLowSample,
        personal_baseline: data.personalBaseline ? {
          avg_fomo: data.personalBaseline.avgFomo,
          avg_panic: data.personalBaseline.avgPanic,
          avg_mae: data.personalBaseline.avgMae,
          avg_disposition_ratio: data.personalBaseline.avgDispositionRatio,
          avg_revenge_count: data.personalBaseline.avgRevengeCount,
        } : null,
        bias_loss_mapping: data.biasLossMapping ? {
          fomo_loss: data.biasLossMapping.fomoLoss,
          panic_loss: data.biasLossMapping.panicLoss,
          revenge_loss: data.biasLossMapping.revengeLoss,
          disposition_loss: data.biasLossMapping.dispositionLoss,
        } : null,
        bias_priority: data.biasPriority,
        behavior_shift: data.behaviorShift,
      }),
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

