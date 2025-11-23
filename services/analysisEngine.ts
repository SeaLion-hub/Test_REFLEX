import { EnrichedTrade, RawCsvRow, AnalysisResult } from '../types';

// --- CONSTANTS & MOCK DB (For Fallback/Demo Mode Only) ---

// Enhanced Mock DB to ensure "Truth" in Demo Mode.
const LOCAL_MARKET_DB: Record<string, Record<string, { h: number; l: number; c: number }>> = {
  'AAPL': {
    '2023-01-10': { h: 131.26, l: 128.12, c: 130.73 }, // Entry
    '2023-01-11': { h: 133.51, l: 130.46, c: 133.49 },
    '2023-01-12': { h: 134.26, l: 131.44, c: 133.41 },
    '2023-01-13': { h: 134.92, l: 131.66, c: 134.76 },
    '2023-01-14': { h: 134.92, l: 131.66, c: 134.76 }, // Weekend
    '2023-01-15': { h: 136.00, l: 133.50, c: 135.20 }, // Exit
    '2023-01-16': { h: 136.00, l: 133.50, c: 135.20 },
    '2023-01-17': { h: 137.29, l: 135.03, c: 135.94 },
    '2023-01-18': { h: 138.61, l: 135.03, c: 135.21 },
  },
  'TSLA': {
    '2023-02-01': { h: 183.80, l: 169.90, c: 181.41 },
    '2023-02-02': { h: 196.75, l: 182.61, c: 188.27 },
    '2023-02-03': { h: 199.00, l: 183.69, c: 189.98 },
    '2023-02-06': { h: 198.17, l: 189.92, c: 194.76 },
  },
  'GME': {
    '2021-01-27': { h: 380.00, l: 249.00, c: 347.51 },
    '2021-01-28': { h: 483.00, l: 112.25, c: 193.60 },
    '2021-01-29': { h: 398.99, l: 250.00, c: 325.00 },
  }
};

// --- FIFO ENGINE (Fallback) ---

const processFIFO = (rows: RawCsvRow[]): RawCsvRow[] => {
  const sorted = [...rows].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  const trades: RawCsvRow[] = [];
  const inventory: Record<string, RawCsvRow[]> = {};

  sorted.forEach(row => {
    const ticker = row.ticker;
    if (!inventory[ticker]) inventory[ticker] = [];

    const action = row.action ? row.action.toUpperCase() : 'BUY';

    if (action === 'BUY') {
      inventory[ticker].push({ ...row });
    } else if (action === 'SELL') {
      let qtyToSell = row.qty;
      while (qtyToSell > 0.000001 && inventory[ticker].length > 0) {
        const lot = inventory[ticker][0];
        const matchQty = Math.min(lot.qty, qtyToSell);

        trades.push({
          ticker: ticker,
          date: lot.date,
          price: lot.price,
          qty: matchQty,
          exitDate: row.date,
          exitPrice: row.price,
          action: 'BUY'
        } as RawCsvRow);

        qtyToSell -= matchQty;
        lot.qty -= matchQty;
        if (lot.qty <= 0.000001) inventory[ticker].shift();
      }
    }
  });
  return trades;
};

// --- DATA ENRICHMENT (Local Fallback) ---

const getLocalMarketData = (ticker: string, date: string) => {
  const dateKey = date.split(' ')[0];
  return LOCAL_MARKET_DB[ticker]?.[dateKey] || null;
};

const enrichTradeLocal = (trade: RawCsvRow): EnrichedTrade => {
    const entryDate = trade.date;
    const entryPrice = trade.price;
    const exitDate = trade.exitDate!;
    const exitPrice = trade.exitPrice!;
    const qty = trade.qty;

    const entryData = getLocalMarketData(trade.ticker, entryDate);
    const exitData = getLocalMarketData(trade.ticker, exitDate);

    if (!entryData || !exitData) {
        return {
            id: `local-${Math.random()}`,
            ticker: trade.ticker,
            entryDate, entryPrice, exitDate, exitPrice, qty,
            pnl: (exitPrice - entryPrice) * qty,
            returnPct: (exitPrice - entryPrice) / entryPrice,
            durationDays: Math.max(0, (new Date(exitDate).getTime() - new Date(entryDate).getTime()) / (86400000)),
            entryDayHigh: entryPrice, entryDayLow: entryPrice,
            exitDayHigh: exitPrice, exitDayLow: exitPrice,
            postExitHigh3Day: exitPrice,
            fomoScore: -1, panicScore: -1, mae: 0, mfe: 0, efficiency: 0, regret: 0,
            marketRegime: 'UNKNOWN',
            isRevenge: false
        };
    }

    const rangeE = entryData.h - entryData.l || 1;
    const fomoScore = (entryPrice - entryData.l) / rangeE;

    const rangeX = exitData.h - exitData.l || 1;
    const panicScore = (exitPrice - exitData.l) / rangeX;

    let maxFuture = exitData.h;
    // Fallback doesn't have rigorous date arithmetic for future, stick to simple max
    const regret = 0;

    return {
        id: `local-${Math.random()}`,
        ticker: trade.ticker,
        entryDate, entryPrice, exitDate, exitPrice, qty,
        pnl: (exitPrice - entryPrice) * qty,
        returnPct: (exitPrice - entryPrice) / entryPrice,
        durationDays: Math.max(0.1, (new Date(exitDate).getTime() - new Date(entryDate).getTime()) / 86400000),
        entryDayHigh: entryData.h, entryDayLow: entryData.l,
        exitDayHigh: exitData.h, exitDayLow: exitData.l,
        postExitHigh3Day: maxFuture,
        fomoScore, panicScore,
        mae: (Math.min(entryData.l, exitData.l) - entryPrice) / entryPrice,
        mfe: (Math.max(entryData.h, exitData.h) - entryPrice) / entryPrice,
        efficiency: 0.5,
        regret,
        marketRegime: 'UNKNOWN',
        isRevenge: false
    };
};

// --- MAIN ENTRY POINT ---

const convertToCSVBlob = (rows: RawCsvRow[]): Blob => {
    const header = "Ticker,Entry Date,Entry Price,Exit Date,Exit Price,Qty\n";
    const body = rows.map(r => 
        `${r.ticker},${r.date},${r.price},${r.exitDate},${r.exitPrice},${r.qty || 1}`
    ).join('\n');
    return new Blob([header + body], { type: 'text/csv' });
};

export const analyzeTrades = async (rawRows: RawCsvRow[]): Promise<AnalysisResult> => {
    let enrichedTrades: EnrichedTrade[] = [];
    let dataSource: 'BACKEND_TRUTH' | 'CLIENT_DEMO' = 'CLIENT_DEMO';

    try {
        const csvBlob = convertToCSVBlob(rawRows);
        const formData = new FormData();
        formData.append('file', csvBlob, 'trades.csv');

        const response = await fetch('http://localhost:8000/analyze', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const json = await response.json();
            // 백엔드 snake_case를 프론트엔드 camelCase로 변환
            enrichedTrades = json.trades.map((t: any) => ({
                id: t.id,
                ticker: t.ticker,
                entryDate: t.entry_date,
                entryPrice: t.entry_price,
                exitDate: t.exit_date,
                exitPrice: t.exit_price,
                qty: t.qty,
                pnl: t.pnl,
                returnPct: t.return_pct,
                durationDays: t.duration_days,
                marketRegime: t.market_regime,
                isRevenge: t.is_revenge,
                strategyTag: t.strategy_tag,
                userAcknowledged: t.user_acknowledged,
                fomoScore: t.fomo_score,
                panicScore: t.panic_score,
                mae: t.mae,
                mfe: t.mfe,
                efficiency: t.efficiency,
                regret: t.regret,
                entryDayHigh: t.entry_day_high,
                entryDayLow: t.entry_day_low,
                exitDayHigh: t.exit_day_high,
                exitDayLow: t.exit_day_low,
                // Contextual Score 분해 필드
                baseScore: t.base_score,
                volumeWeight: t.volume_weight,
                regimeWeight: t.regime_weight,
                contextualScore: t.contextual_score
            }));
            const backendMetrics = json.metrics;
            return {
                trades: enrichedTrades,
                metrics: {
                    totalTrades: backendMetrics.total_trades,
                    winRate: backendMetrics.win_rate,
                    avgWin: 0, 
                    avgLoss: 0, 
                    profitFactor: backendMetrics.profit_factor,
                    fomoIndex: backendMetrics.fomo_score,
                    panicIndex: backendMetrics.panic_score,
                    dispositionRatio: backendMetrics.disposition_ratio,
                    revengeTradingCount: backendMetrics.revenge_trading_count,
                    sharpeRatio: backendMetrics.sharpe_ratio || 0,
                    sortinoRatio: backendMetrics.sortino_ratio || 0,
                    alpha: backendMetrics.alpha || 0,
                    luckPercentile: backendMetrics.luck_percentile || 50,
                    totalRegret: json.trades.reduce((sum: number, t: any) => sum + (t.regret || 0), 0),
                    truthScore: backendMetrics.truth_score
                },
                isLowSample: json.is_low_sample,
                revengeTrades: enrichedTrades.filter((t: any) => t.isRevenge),
                dataSource: 'BACKEND_TRUTH',
                personalBaseline: json.personal_baseline ? {
                    avgFomo: json.personal_baseline.avg_fomo,
                    avgPanic: json.personal_baseline.avg_panic,
                    avgMae: json.personal_baseline.avg_mae,
                    avgDispositionRatio: json.personal_baseline.avg_disposition_ratio,
                    avgRevengeCount: json.personal_baseline.avg_revenge_count
                } : undefined,
                biasLossMapping: json.bias_loss_mapping ? {
                    fomoLoss: json.bias_loss_mapping.fomo_loss,
                    panicLoss: json.bias_loss_mapping.panic_loss,
                    revengeLoss: json.bias_loss_mapping.revenge_loss,
                    dispositionLoss: json.bias_loss_mapping.disposition_loss
                } : undefined,
                biasPriority: json.bias_priority ? json.bias_priority.map((p: any) => ({
                    bias: p.bias,
                    priority: p.priority,
                    financialLoss: p.financial_loss,
                    frequency: p.frequency,
                    severity: p.severity
                })) : undefined,
                behaviorShift: json.behavior_shift ? json.behavior_shift.map((s: any) => ({
                    bias: s.bias,
                    recentValue: s.recent_value,
                    baselineValue: s.baseline_value,
                    changePercent: s.change_percent,
                    trend: s.trend
                })) : undefined,
                equityCurve: json.equity_curve ? json.equity_curve.map((p: any) => ({
                    date: p.date,
                    cumulative_pnl: p.cumulative_pnl,
                    fomo_score: p.fomo_score,
                    panic_score: p.panic_score,
                    is_revenge: p.is_revenge,
                    ticker: p.ticker,
                    pnl: p.pnl,
                    trade_id: p.trade_id,
                    base_score: p.base_score,
                    volume_weight: p.volume_weight,
                    regime_weight: p.regime_weight,
                    contextual_score: p.contextual_score,
                    market_regime: p.market_regime
                })) : undefined,
                patterns: json.patterns ? json.patterns.map((p: any) => ({
                    pattern: p.pattern,
                    description: p.description,
                    count: p.count,
                    total: p.total,
                    percentage: p.percentage,
                    significance: p.significance
                })) : undefined,
                deepPatterns: json.deep_patterns ? json.deep_patterns.map((dp: any) => ({
                    type: dp.type,
                    description: dp.description,
                    significance: dp.significance,
                    metadata: dp.metadata || {}
                })) : undefined
            };

        } else {
            console.warn("Backend error:", await response.text());
            throw new Error("Backend returned error");
        }
    } catch (e) {
        console.warn("Backend unavailable. Using Local Truth Engine (Safe Mode).", e);
        const tradesToAnalyze = rawRows;
        enrichedTrades = tradesToAnalyze.map(enrichTradeLocal);
    }

    // --- LOCAL FALLBACK CALCULATION (Legacy) ---
    
    let revengeTradingCount = 0;
    const revengeTrades: EnrichedTrade[] = [];
    
    enrichedTrades.sort((a, b) => new Date(a.entryDate).getTime() - new Date(b.entryDate).getTime());

    for (let i = 1; i < enrichedTrades.length; i++) {
        const current = enrichedTrades[i];
        const entryTime = new Date(current.entryDate).getTime();
        
        const prevLoss = enrichedTrades.slice(0, i).find(prev => {
            if (prev.ticker !== current.ticker) return false;
            if (prev.pnl >= 0) return false; 
            const prevExitTime = new Date(prev.exitDate).getTime();
            const diffMs = entryTime - prevExitTime;
            return diffMs >= 0 && diffMs < (24 * 60 * 60 * 1000);
        });

        if (prevLoss) {
            current.isRevenge = true;
            revengeTradingCount++;
            revengeTrades.push(current);
        }
    }

    const totalTrades = enrichedTrades.length;
    const isLowSample = totalTrades < 5;
    const validTrades = enrichedTrades.filter(t => t.fomoScore !== -1); 
    
    const winners = enrichedTrades.filter(t => t.pnl > 0);
    const losers = enrichedTrades.filter(t => t.pnl <= 0);
    
    const winRate = totalTrades > 0 ? winners.length / totalTrades : 0;
    const avgWin = winners.length > 0 ? winners.reduce((a, b) => a + b.pnl, 0) / winners.length : 0;
    const avgLoss = losers.length > 0 ? Math.abs(losers.reduce((a, b) => a + b.pnl, 0) / losers.length) : 0;
    const profitFactor = avgLoss > 0 ? (avgWin * winners.length) / (avgLoss * losers.length) : 0;

    const fomoIndex = validTrades.length > 0 ? validTrades.reduce((acc, t) => acc + t.fomoScore, 0) / validTrades.length : 0;
    const avgPanic = validTrades.length > 0 ? validTrades.reduce((acc, t) => acc + t.panicScore, 0) / validTrades.length : 0;
    const panicIndex = 1 - avgPanic;

    const avgWinHold = winners.length > 0 ? winners.reduce((a, b) => a + b.durationDays, 0) / winners.length : 0;
    const avgLossHold = losers.length > 0 ? losers.reduce((a, b) => a + b.durationDays, 0) / losers.length : 0;
    const dispositionRatio = avgWinHold > 0 ? avgLossHold / avgWinHold : 0;

    const returns = enrichedTrades.map(t => t.returnPct);
    const avgReturn = returns.reduce((a, b) => a + b, 0) / (totalTrades || 1);
    const stdDev = Math.sqrt(returns.reduce((a, b) => a + Math.pow(b - avgReturn, 2), 0) / (totalTrades || 1));
    const sharpeRatio = stdDev > 0 ? (avgReturn - 0.02/252) / stdDev : 0; 
    const downsideDev = Math.sqrt(returns.filter(r => r < 0).reduce((a, b) => a + Math.pow(b, 2), 0) / (totalTrades || 1));
    const sortinoRatio = downsideDev > 0 ? avgReturn / downsideDev : 0;

    let luckPercentile = 50;
    if (!isLowSample && validTrades.length > 0) {
        const simulations = 1000;
        const realizedTotalPnl = enrichedTrades.reduce((a, b) => a + b.pnl, 0);
        
        // 실제 통계 계산
        const winners = enrichedTrades.filter(t => t.pnl > 0);
        const losers = enrichedTrades.filter(t => t.pnl <= 0);
        const winRate = winners.length / enrichedTrades.length;
        
        // 실제 PnL 분포 (시뮬레이션에 사용)
        const winPnls = winners.map(t => t.pnl);
        const lossPnls = losers.map(t => Math.abs(t.pnl));
        
        let betterOutcomes = 0;
        const simulationResults: number[] = [];
        
        for (let i = 0; i < simulations; i++) {
            let simTotal = 0;
            
            // 실제 승률을 유지하면서 실제 PnL 분포에서 샘플링
            for (let j = 0; j < totalTrades; j++) {
                if (Math.random() < winRate) {
                    // 승리: 실제 승리 PnL 중 랜덤 선택
                    if (winPnls.length > 0) {
                        simTotal += winPnls[Math.floor(Math.random() * winPnls.length)];
                    }
                } else {
                    // 패배: 실제 손실 PnL 중 랜덤 선택
                    if (lossPnls.length > 0) {
                        simTotal -= lossPnls[Math.floor(Math.random() * lossPnls.length)];
                    }
                }
            }
            
            simulationResults.push(simTotal);
            if (simTotal > realizedTotalPnl) betterOutcomes++;
        }
        
        // Percentile 계산
        luckPercentile = (betterOutcomes / simulations) * 100;
        
        // 추가: 시뮬레이션 결과의 분포를 보고 해석 개선
        if (simulationResults.length > 0) {
            simulationResults.sort((a, b) => a - b);
            const median = simulationResults[Math.floor(simulations / 2)];
            const p25 = simulationResults[Math.floor(simulations * 0.25)];
            const p75 = simulationResults[Math.floor(simulations * 0.75)];
            
            // 실제 성과가 중앙값보다 얼마나 다른지
            if (realizedTotalPnl > p75) {
                // 상위 25%에 속함 = 운이 좋음
                luckPercentile = Math.max(0, luckPercentile - 5);
            } else if (realizedTotalPnl < p25) {
                // 하위 25%에 속함 = 운이 나쁨
                luckPercentile = Math.min(100, luckPercentile + 5);
            }
        }
    }

    const totalRegret = enrichedTrades.reduce((a, b) => a + b.regret, 0);

    let baseScore = 50;
    baseScore += (winRate * 20);
    baseScore -= (fomoIndex * 25);
    baseScore -= (panicIndex * 25);
    baseScore -= (Math.max(0, dispositionRatio - 1) * 15);
    baseScore -= (revengeTradingCount * 10);
    if (!isLowSample) baseScore += (sharpeRatio * 5);
    else baseScore += 5;

    let personalBaseline = undefined;
    if (totalTrades >= 3) {
        const validMae = enrichedTrades.filter(t => t.mae !== 0);
        const avgMae = validMae.length > 0 ? Math.abs(validMae.reduce((a, b) => a + b.mae, 0) / validMae.length) : 0;
        personalBaseline = {
            avgFomo: fomoIndex,
            avgPanic: panicIndex,
            avgMae: avgMae,
            avgDispositionRatio: dispositionRatio,
            avgRevengeCount: revengeTradingCount / totalTrades
        };
    }

    let biasLossMapping = undefined;
    if (totalTrades > 0) {
        const highFomoTrades = enrichedTrades.filter(t => t.fomoScore > 0.7 && t.fomoScore !== -1);
        const fomoLoss = Math.abs(highFomoTrades.filter(t => t.pnl < 0).reduce((a, b) => a + b.pnl, 0));
        const lowPanicTrades = enrichedTrades.filter(t => t.panicScore < 0.3 && t.panicScore !== -1);
        const panicLoss = Math.abs(lowPanicTrades.filter(t => t.pnl < 0).reduce((a, b) => a + b.pnl, 0));
        const revengeLossTrades = revengeTrades.filter(t => t.pnl < 0);
        const revengeLoss = Math.abs(revengeLossTrades.reduce((a, b) => a + b.pnl, 0));
        const winnersWithRegret = enrichedTrades.filter(t => t.pnl > 0 && t.regret > 0);
        const dispositionLoss = winnersWithRegret.reduce((a, b) => a + b.regret, 0);
        
        biasLossMapping = { fomoLoss, panicLoss, revengeLoss, dispositionLoss };
    }

    return {
        trades: enrichedTrades,
        isLowSample,
        revengeTrades,
        dataSource,
        metrics: {
            totalTrades, winRate, avgWin, avgLoss, profitFactor,
            fomoIndex, panicIndex, dispositionRatio, revengeTradingCount,
            sharpeRatio, sortinoRatio, alpha: avgReturn, luckPercentile,
            totalRegret, truthScore: Math.max(0, Math.min(100, Math.round(baseScore)))
        },
        personalBaseline,
        biasLossMapping,
        biasPriority: undefined, 
        behaviorShift: undefined
    };
};

export const parseCSV = (text: string): RawCsvRow[] => {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];

  const headerLine = lines[0].toLowerCase();
  const isExecutionLog = headerLine.includes('action') || headerLine.includes('side');

  const parsedRows = lines.slice(1).map(line => {
    const cleanLine = line.replace('\r', '').replace(/"/g, '');
    const vals = cleanLine.split(',');
    
    if (vals.length < 5) return null;
    
    if (isExecutionLog) {
        return {
            ticker: vals[0]?.trim(),
            date: vals[1]?.trim(),
            action: vals[2]?.trim().toUpperCase(),
            price: parseFloat(vals[3]),
            qty: parseFloat(vals[4]),
        } as RawCsvRow;
    } else {
        return {
            ticker: vals[0]?.trim(),
            date: vals[1]?.trim(),
            price: parseFloat(vals[2]),
            exitDate: vals[3]?.trim(),
            exitPrice: parseFloat(vals[4]),
            qty: parseFloat(vals[5] || '1'),
            action: 'BUY' 
        } as RawCsvRow;
    }
  }).filter(Boolean) as RawCsvRow[];

  if (isExecutionLog) {
      return processFIFO(parsedRows);
  }

  return parsedRows;
};