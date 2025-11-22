
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
            
            return {
                trades: json.trades,
                metrics: json.metrics,
                isLowSample: json.is_low_sample,
                revengeTrades: json.trades.filter((t: any) => t.is_revenge),
                dataSource: 'BACKEND_TRUTH'
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
        }
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
