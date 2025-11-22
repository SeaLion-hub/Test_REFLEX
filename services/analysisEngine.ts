
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

    if (row.action === 'BUY') {
      inventory[ticker].push({ ...row });
    } else if (row.action === 'SELL') {
      let qtyToSell = row.qty;
      while (qtyToSell > 0 && inventory[ticker].length > 0) {
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
        if (lot.qty <= 0.00001) inventory[ticker].shift();
      }
    }
  });
  return trades;
};

// --- DATA ENRICHMENT (Local Fallback) ---

const getLocalMarketData = (ticker: string, date: string) => {
  return LOCAL_MARKET_DB[ticker]?.[date] || null;
};

const enrichTradeLocal = (trade: RawCsvRow): EnrichedTrade => {
    const entryDate = trade.date;
    const entryPrice = trade.price;
    const exitDate = trade.exitDate!;
    const exitPrice = trade.exitPrice!;
    const qty = trade.qty;

    const entryData = getLocalMarketData(trade.ticker, entryDate);
    const exitData = getLocalMarketData(trade.ticker, exitDate);

    // Strict Truth: If no data, return N/A. No random gen.
    if (!entryData || !exitData) {
        return {
            id: `local-${Math.random()}`,
            ticker: trade.ticker,
            entryDate, entryPrice, exitDate, exitPrice, qty,
            pnl: (exitPrice - entryPrice) * qty,
            returnPct: (exitPrice - entryPrice) / entryPrice,
            durationDays: (new Date(exitDate).getTime() - new Date(entryDate).getTime()) / (86400000),
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
    const exitTime = new Date(exitDate).getTime();
    for (let i=1; i<=3; i++) {
       const nextDay = new Date(exitTime + (i * 86400000)).toISOString().split('T')[0];
       const nextData = getLocalMarketData(trade.ticker, nextDay);
       if (nextData) maxFuture = Math.max(maxFuture, nextData.h);
    }
    const regret = Math.max(0, maxFuture - exitPrice) * qty;

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
    // Convert strict 6 columns to CSV string
    const header = "Ticker,Entry Date,Entry Price,Exit Date,Exit Price,Qty\n";
    const body = rows.map(r => 
        `${r.ticker},${r.date},${r.price},${r.exitDate},${r.exitPrice},${r.qty || 1}`
    ).join('\n');
    return new Blob([header + body], { type: 'text/csv' });
};

export const analyzeTrades = async (rawRows: RawCsvRow[]): Promise<AnalysisResult> => {
    // Filter out rows that don't meet the strict 6-column Paired Trade format (or convert them if needed)
    // For now, we enforce that parseCSV returns the correct structure.
    
    let enrichedTrades: EnrichedTrade[] = [];
    let dataSource: 'BACKEND_TRUTH' | 'CLIENT_DEMO' = 'CLIENT_DEMO';

    // 1. Try Backend (The Truth)
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
            enrichedTrades = json.trades;
            // Backend returns full metrics object, let's use it directly if possible,
            // but our frontend expects some enriched logic.
            // Actually, the backend now returns exactly what we need in `json.metrics`.
            
            // We need to map the backend response to our frontend types fully if they differ.
            // The backend `EnrichedTrade` matches frontend `EnrichedTrade`.
            // The backend `metrics` matches frontend `metrics` mostly.
            
            // Map backend metrics (snake_case) to frontend format (camelCase)
            const backendMetrics = json.metrics;
            return {
                trades: json.trades,
                metrics: {
                    totalTrades: backendMetrics.total_trades,
                    winRate: backendMetrics.win_rate,
                    avgWin: 0, // Not in backend response, will be calculated if needed
                    avgLoss: 0, // Not in backend response, will be calculated if needed
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
                revengeTrades: json.trades.filter((t: any) => t.is_revenge),
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
                    pnl: p.pnl
                })) : undefined,
                // 패턴은 프론트엔드에서 계산 (또는 백엔드에서 오면 사용)
                patterns: json.patterns ? json.patterns.map((p: any) => ({
                    pattern: p.pattern,
                    description: p.description,
                    count: p.count,
                    total: p.total,
                    percentage: p.percentage,
                    significance: p.significance
                })) : undefined
            };

        } else {
            console.warn("Backend error:", await response.text());
            throw new Error("Backend returned error");
        }
    } catch (e) {
        console.warn("Backend unavailable. Using Local Truth Engine (Safe Mode).", e);
        // Fallback to local logic
        const tradesToAnalyze = rawRows; // We assume paired format for now in fallback
        enrichedTrades = tradesToAnalyze.map(enrichTradeLocal);
    }

    // ... (Local Fallback Logic if Backend Fails - Existing Code below) ...
    
    // 2. Revenge Trading Logic (Post-Process) -> Only runs if Backend Failed and we are in local mode
    // If we returned above, this code is unreachable, which is correct.
    
    // --- LOCAL FALLBACK CALCULATION (Legacy) ---
    
    let revengeTradingCount = 0;
    const revengeTrades: EnrichedTrade[] = [];
    
    enrichedTrades.sort((a, b) => new Date(a.entryDate).getTime() - new Date(b.entryDate).getTime());

    for (let i = 1; i < enrichedTrades.length; i++) {
        const current = enrichedTrades[i];
        const entryTime = new Date(current.entryDate).getTime();
        
        // Look for ANY loss on SAME ticker in previous 24h
        const prevLoss = enrichedTrades.slice(0, i).find(prev => {
            if (prev.ticker !== current.ticker) return false;
            if (prev.pnl >= 0) return false; // Must be a loss
            const prevExitTime = new Date(prev.exitDate).getTime();
            const diffMs = entryTime - prevExitTime;
            // Between 0 and 24 hours
            return diffMs >= 0 && diffMs < (24 * 60 * 60 * 1000);
        });

        if (prevLoss) {
            current.isRevenge = true;
            revengeTradingCount++;
            revengeTrades.push(current);
        }
    }

    // 3. Aggregates & Metrics (Local)
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

    // Monte Carlo (Skip if Low Sample)
    let luckPercentile = 50;
    if (!isLowSample && validTrades.length > 0) {
        const simulations = 1000;
        const realizedTotalPnl = enrichedTrades.reduce((a, b) => a + b.pnl, 0);
        let betterOutcomes = 0;
        const allPnls = enrichedTrades.map(t => t.pnl);
        
        for (let i = 0; i < simulations; i++) {
            let simTotal = 0;
            for (let j = 0; j < totalTrades; j++) {
                simTotal += allPnls[Math.floor(Math.random() * totalTrades)];
            }
            if (simTotal > realizedTotalPnl) betterOutcomes++;
        }
        luckPercentile = (betterOutcomes / simulations) * 100;
    }

    const totalRegret = enrichedTrades.reduce((a, b) => a + b.regret, 0);

    // Truth Score Calculation
    let baseScore = 50;
    baseScore += (winRate * 20);
    baseScore -= (fomoIndex * 25);
    baseScore -= (panicIndex * 25);
    baseScore -= (Math.max(0, dispositionRatio - 1) * 15);
    baseScore -= (revengeTradingCount * 10);
    if (!isLowSample) baseScore += (sharpeRatio * 5);
    else baseScore += 5;

    // --- PERFECT EDITION CALCULATIONS (Fallback) ---
    
    // 1. Personal Baseline
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
    
    // 2. Bias Loss Mapping
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
        
        biasLossMapping = {
            fomoLoss,
            panicLoss,
            revengeLoss,
            dispositionLoss
        };
    }
    
    // 3. Bias Prioritization
    let biasPriority = undefined;
    if (biasLossMapping) {
        const priorities: Array<{bias: string, priority: number, financialLoss: number, frequency: number, severity: number}> = [];
        
        const highFomoCount = enrichedTrades.filter(t => t.fomoScore > 0.7 && t.fomoScore !== -1).length;
        const fomoFrequency = highFomoCount / totalTrades;
        const fomoSeverity = Math.min(1.0, fomoIndex / 0.8);
        if (biasLossMapping.fomoLoss > 0 || fomoFrequency > 0.3) {
            priorities.push({
                bias: 'FOMO',
                priority: 0,
                financialLoss: biasLossMapping.fomoLoss,
                frequency: fomoFrequency,
                severity: fomoSeverity
            });
        }
        
        const lowPanicCount = enrichedTrades.filter(t => t.panicScore < 0.3 && t.panicScore !== -1).length;
        const panicFrequency = lowPanicCount / totalTrades;
        const panicSeverity = Math.min(1.0, (1 - panicIndex) / 0.8);
        if (biasLossMapping.panicLoss > 0 || panicFrequency > 0.3) {
            priorities.push({
                bias: 'Panic Sell',
                priority: 0,
                financialLoss: biasLossMapping.panicLoss,
                frequency: panicFrequency,
                severity: panicSeverity
            });
        }
        
        const revengeFrequency = revengeTradingCount / totalTrades;
        const revengeSeverity = Math.min(1.0, revengeTradingCount / 3.0);
        if (biasLossMapping.revengeLoss > 0 || revengeTradingCount > 0) {
            priorities.push({
                bias: 'Revenge Trading',
                priority: 0,
                financialLoss: biasLossMapping.revengeLoss,
                frequency: revengeFrequency,
                severity: revengeSeverity
            });
        }
        
        const winnersWithRegretCount = enrichedTrades.filter(t => t.pnl > 0 && t.regret > 0).length;
        const dispositionFrequency = winners.length > 0 ? winnersWithRegretCount / winners.length : 0;
        const dispositionSeverity = Math.min(1.0, (dispositionRatio - 1) / 1.5);
        if (biasLossMapping.dispositionLoss > 0 || dispositionRatio > 1.2) {
            priorities.push({
                bias: 'Disposition Effect',
                priority: 0,
                financialLoss: biasLossMapping.dispositionLoss,
                frequency: dispositionFrequency,
                severity: dispositionSeverity
            });
        }
        
        // Sort by composite score and assign priority
        priorities.sort((a, b) => {
            const scoreA = (a.financialLoss * 0.5) + (a.frequency * 10000 * 0.2) + (a.severity * 10000 * 0.3);
            const scoreB = (b.financialLoss * 0.5) + (b.frequency * 10000 * 0.2) + (b.severity * 10000 * 0.3);
            return scoreB - scoreA;
        });
        
        biasPriority = priorities.map((p, i) => ({
            ...p,
            priority: i + 1
        }));
    }
    
    // 4. Behavior Shift Detection
    let behaviorShift = undefined;
    if (totalTrades >= 6) {
        const sortedTrades = [...enrichedTrades].sort((a, b) => 
            new Date(a.entryDate).getTime() - new Date(b.entryDate).getTime()
        );
        const recentTrades = sortedTrades.slice(-3);
        const baselineTrades = sortedTrades.slice(0, Math.max(1, sortedTrades.length - 3));
        
        const shifts: Array<{bias: string, recentValue: number, baselineValue: number, changePercent: number, trend: string}> = [];
        
        // FOMO Shift
        const recentFomo = recentTrades.filter(t => t.fomoScore !== -1);
        const baselineFomo = baselineTrades.filter(t => t.fomoScore !== -1);
        if (recentFomo.length > 0 && baselineFomo.length > 0) {
            const recentFomoAvg = recentFomo.reduce((a, b) => a + b.fomoScore, 0) / recentFomo.length;
            const baselineFomoAvg = baselineFomo.reduce((a, b) => a + b.fomoScore, 0) / baselineFomo.length;
            if (baselineFomoAvg > 0) {
                const fomoChange = ((recentFomoAvg - baselineFomoAvg) / baselineFomoAvg) * 100;
                const fomoTrend = fomoChange < -5 ? 'IMPROVING' : fomoChange > 5 ? 'WORSENING' : 'STABLE';
                shifts.push({
                    bias: 'FOMO',
                    recentValue: recentFomoAvg,
                    baselineValue: baselineFomoAvg,
                    changePercent: fomoChange,
                    trend: fomoTrend
                });
            }
        }
        
        // Panic Shift
        const recentPanic = recentTrades.filter(t => t.panicScore !== -1);
        const baselinePanic = baselineTrades.filter(t => t.panicScore !== -1);
        if (recentPanic.length > 0 && baselinePanic.length > 0) {
            const recentPanicAvg = recentPanic.reduce((a, b) => a + b.panicScore, 0) / recentPanic.length;
            const baselinePanicAvg = baselinePanic.reduce((a, b) => a + b.panicScore, 0) / baselinePanic.length;
            if (baselinePanicAvg > 0) {
                const panicChange = ((recentPanicAvg - baselinePanicAvg) / baselinePanicAvg) * 100;
                const panicTrend = panicChange > 5 ? 'IMPROVING' : panicChange < -5 ? 'WORSENING' : 'STABLE';
                shifts.push({
                    bias: 'Panic Sell',
                    recentValue: recentPanicAvg,
                    baselineValue: baselinePanicAvg,
                    changePercent: panicChange,
                    trend: panicTrend
                });
            }
        }
        
        // Revenge Shift
        const recentRevenge = recentTrades.filter(t => t.isRevenge).length;
        const baselineRevenge = baselineTrades.filter(t => t.isRevenge).length;
        const recentRevengeRate = recentRevenge / recentTrades.length;
        const baselineRevengeRate = baselineRevenge / baselineTrades.length;
        if (baselineRevengeRate > 0 || recentRevengeRate > 0) {
            const revengeChange = ((recentRevengeRate - baselineRevengeRate) / (baselineRevengeRate + 0.01)) * 100;
            const revengeTrend = revengeChange < -10 ? 'IMPROVING' : revengeChange > 10 ? 'WORSENING' : 'STABLE';
            shifts.push({
                bias: 'Revenge Trading',
                recentValue: recentRevengeRate,
                baselineValue: baselineRevengeRate,
                changePercent: revengeChange,
                trend: revengeTrend
            });
        }
        
        // Disposition Shift
        const recentWinners = recentTrades.filter(t => t.pnl > 0);
        const recentLosers = recentTrades.filter(t => t.pnl <= 0);
        const baselineWinners = baselineTrades.filter(t => t.pnl > 0);
        const baselineLosers = baselineTrades.filter(t => t.pnl <= 0);
        
        if (recentWinners.length > 0 && recentLosers.length > 0 && baselineWinners.length > 0 && baselineLosers.length > 0) {
            const recentWinHold = recentWinners.reduce((a, b) => a + b.durationDays, 0) / recentWinners.length;
            const recentLossHold = recentLosers.reduce((a, b) => a + b.durationDays, 0) / recentLosers.length;
            const baselineWinHold = baselineWinners.reduce((a, b) => a + b.durationDays, 0) / baselineWinners.length;
            const baselineLossHold = baselineLosers.reduce((a, b) => a + b.durationDays, 0) / baselineLosers.length;
            
            if (recentWinHold > 0 && baselineWinHold > 0) {
                const recentDisposition = recentLossHold / recentWinHold;
                const baselineDisposition = baselineLossHold / baselineWinHold;
                if (baselineDisposition > 0 && recentDisposition > 0) {
                    const dispositionChange = ((recentDisposition - baselineDisposition) / baselineDisposition) * 100;
                    const dispositionTrend = dispositionChange < -10 ? 'IMPROVING' : dispositionChange > 10 ? 'WORSENING' : 'STABLE';
                    shifts.push({
                        bias: 'Disposition Effect',
                        recentValue: recentDisposition,
                        baselineValue: baselineDisposition,
                        changePercent: dispositionChange,
                        trend: dispositionTrend
                    });
                }
            }
        }
        
        behaviorShift = shifts.length > 0 ? shifts : undefined;
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
        biasPriority,
        behaviorShift
    };
};

export const parseCSV = (text: string): RawCsvRow[] => {
  const lines = text.trim().split('\n');
  // Helper to handle potential CRLF
  const headers = lines[0].replace('\r','').split(',').map(h => h.trim().toLowerCase());
  
  // STRICT MODE: Only accept Paired Trade Format
  // Expected: Ticker, Entry Date, Entry Price, Exit Date, Exit Price, Qty
  
  return lines.slice(1).map(line => {
    const vals = line.replace('\r','').split(',');
    if (vals.length < 5) return null;
    
    // Mapping based on standard format
    // 0: Ticker, 1: Entry Date, 2: Entry Price, 3: Exit Date, 4: Exit Price, 5: Qty
    
    return {
        ticker: vals[0]?.trim(),
        date: vals[1]?.trim(),
        price: parseFloat(vals[2]),
        exitDate: vals[3]?.trim(),
        exitPrice: parseFloat(vals[4]),
        qty: parseFloat(vals[5] || '1'),
        action: 'BUY' // Mock action for type compatibility
    } as RawCsvRow;
  }).filter(Boolean) as RawCsvRow[];
};
