
import OpenAI from "openai";
import { AnalysisResult, AIAnalysis } from "../types";

export const getAIInterpretation = async (data: AnalysisResult): Promise<AIAnalysis> => {
  const apiKey = import.meta.env.VITE_OPENAI_API_KEY || process.env.VITE_OPENAI_API_KEY;
  
  if (!apiKey) {
    return {
        diagnosis: "API Key missing. Please configure your environment to unlock the Truth.",
        rule: "No rule generated.",
        bias: "N/A",
        fix: "Add VITE_OPENAI_API_KEY to your .env.local"
    };
  }

  const openai = new OpenAI({ apiKey, dangerouslyAllowBrowser: true });

  // Prepare granular context
  const topRegrets = data.trades
    .sort((a, b) => b.regret - a.regret)
    .slice(0, 3)
    .map(t => `${t.ticker} (Missed $${t.regret.toFixed(0)})`);

  const revengeDetails = data.revengeTrades.map(t => `${t.ticker} (-$${Math.abs(t.pnl).toFixed(0)})`).join(', ');

  // Perfect Edition Context
  const personalBaselineText = data.personalBaseline ? `
    PERSONAL BASELINE (Your Historical Average):
    - Avg FOMO: ${(data.personalBaseline.avgFomo * 100).toFixed(0)}% (Current: ${(data.metrics.fomoIndex * 100).toFixed(0)}%)
    - Avg Panic: ${(data.personalBaseline.avgPanic * 100).toFixed(0)}% (Current: ${(data.metrics.panicIndex * 100).toFixed(0)}%)
    - Avg Disposition: ${data.personalBaseline.avgDispositionRatio.toFixed(1)}x (Current: ${data.metrics.dispositionRatio.toFixed(1)}x)
  ` : '';

  const biasLossText = data.biasLossMapping ? `
    BIAS LOSS MAPPING (Financial Impact):
    - FOMO Loss: -$${data.biasLossMapping.fomoLoss.toFixed(0)}
    - Panic Sell Loss: -$${data.biasLossMapping.panicLoss.toFixed(0)}
    - Revenge Trading Loss: -$${data.biasLossMapping.revengeLoss.toFixed(0)}
    - Disposition Effect (Missed): -$${data.biasLossMapping.dispositionLoss.toFixed(0)}
  ` : '';

  const biasPriorityText = data.biasPriority && data.biasPriority.length > 0 ? `
    FIX PRIORITY (Ranked by Impact):
    ${data.biasPriority.map((p, i) => `${i + 1}. ${p.bias}: -$${p.financialLoss.toFixed(0)} (Frequency: ${(p.frequency * 100).toFixed(0)}%, Severity: ${(p.severity * 100).toFixed(0)}%)`).join('\n    ')}
  ` : '';

  const behaviorShiftText = data.behaviorShift && data.behaviorShift.length > 0 ? `
    BEHAVIOR SHIFT (Recent 3 vs Baseline):
    ${data.behaviorShift.map(s => `- ${s.bias}: ${s.trend} (${s.changePercent > 0 ? '+' : ''}${s.changePercent.toFixed(1)}%)`).join('\n    ')}
  ` : '';

  const prompt = `
    Act as the "Truth Pipeline" AI. You are an objective, slightly ruthless, data-driven Trading Coach.
    Your goal is to correct behavior, not predict markets.
    
    USER PROFILE:
    - Mode: ${data.isLowSample ? "NOVICE / LOW SAMPLE (Focus on specific mistakes)" : "EXPERIENCED (Focus on statistics)"}
    - Market Data Source: ${data.dataSource === 'BACKEND_TRUTH' ? "Real Market Data" : "Demo Data"}
    
    HARD EVIDENCE:
    1. TRUTH SCORE: ${data.metrics.truthScore}/100
    2. DISCIPLINE (FOMO): You bought at ${(data.metrics.fomoIndex * 100).toFixed(0)}% of the day's range on average. (High = Bad)
    3. NERVES (Panic): You sold at ${(data.metrics.panicIndex * 100).toFixed(0)}% of the day's range on average. (High = Bad)
    4. PATIENCE (Disposition): You hold losers ${data.metrics.dispositionRatio.toFixed(1)}x longer than winners.
    5. EMOTION (Revenge): ${data.metrics.revengeTradingCount} revenge trades detected. Tickers: ${revengeDetails || "None"}.
    6. REGRET: You left $${data.metrics.totalRegret.toFixed(0)} on the table. Top misses: ${topRegrets.join(', ')}.

    ${personalBaselineText}
    ${biasLossText}
    ${biasPriorityText}
    ${behaviorShiftText}

    EVIDENCE STRUCTURE (You MUST reference these numbers in your diagnosis):
    - Evidence #1: FOMO Score ${(data.metrics.fomoIndex * 100).toFixed(0)}% (Threshold > 70% is bad)${data.personalBaseline ? ` vs Your Average ${(data.personalBaseline.avgFomo * 100).toFixed(0)}%` : ''}
    - Evidence #2: Panic Sell Score ${(data.metrics.panicIndex * 100).toFixed(0)}% (Threshold > 70% is bad)${data.personalBaseline ? ` vs Your Average ${(data.personalBaseline.avgPanic * 100).toFixed(0)}%` : ''}
    - Evidence #3: Disposition Ratio ${data.metrics.dispositionRatio.toFixed(1)}x (Threshold > 1.5x is bad)${data.personalBaseline ? ` vs Your Average ${data.personalBaseline.avgDispositionRatio.toFixed(1)}x` : ''}
    - Evidence #4: Revenge Trading Count ${data.metrics.revengeTradingCount} (Threshold > 0 is bad)
    - Evidence #5: Total Regret $${data.metrics.totalRegret.toFixed(0)}
    ${data.biasLossMapping ? `- Evidence #6: Total Bias Loss -$${(data.biasLossMapping.fomoLoss + data.biasLossMapping.panicLoss + data.biasLossMapping.revengeLoss + data.biasLossMapping.dispositionLoss).toFixed(0)}` : ''}
    ${data.biasPriority && data.biasPriority.length > 0 ? `- Evidence #7: Priority Fix #1 is ${data.biasPriority[0].bias} (Loss: -$${data.biasPriority[0].financialLoss.toFixed(0)})` : ''}

    INSTRUCTIONS:
    1. DIAGNOSIS (3 sentences): 
       - Sentence 1: Direct, slightly harsh observation of their biggest flaw. ${data.biasPriority && data.biasPriority.length > 0 ? `Focus on ${data.biasPriority[0].bias} (Priority #1, Loss: -$${data.biasPriority[0].financialLoss.toFixed(0)}).` : ''}
       - Sentence 2: EVIDENCE-BASED FACT. You MUST strictly follow this format: "According to Evidence #X, you [specific action] on [Ticker]." ${data.personalBaseline ? `Compare to your personal baseline when relevant.` : ''} Example: "According to Evidence #1, you bought GME at 93% of the day's range, well above your average of 78%."
       - Sentence 3: The financial impact. ${data.biasLossMapping ? `Mention specific loss amounts from Bias Loss Mapping if significant.` : ''} ${data.behaviorShift && data.behaviorShift.some(s => s.trend === 'WORSENING') ? `Note any worsening trends from Behavior Shift.` : ''}
    2. RULE (1 sentence): A catchy, memorable trading commandment to fix this specific flaw. ${data.biasPriority && data.biasPriority.length > 0 ? `Target ${data.biasPriority[0].bias} specifically.` : ''}
    3. BIAS: Name the single dominant psychological bias. ${data.biasPriority && data.biasPriority.length > 0 ? `Use: ${data.biasPriority[0].bias}` : ''} (e.g. Disposition Effect, Action Bias, Revenge Trading, FOMO).
    4. FIX: One specific, actionable step to take immediately. ${data.biasPriority && data.biasPriority.length > 0 ? `Focus on fixing ${data.biasPriority[0].bias} first (highest financial impact).` : ''}

    Output valid JSON only with this exact structure:
    {
      "diagnosis": "3 sentences. Must mention a ticker.",
      "rule": "1 sentence rule.",
      "bias": "Primary bias.",
      "fix": "Priority fix."
    }
  `;

  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: "You are a data-driven trading coach. Always respond with valid JSON only."
        },
        {
          role: "user",
          content: prompt
        }
      ],
      response_format: { type: "json_object" },
      temperature: 0.7,
    });

    const content = completion.choices[0]?.message?.content;
    if (content) {
        const parsed = JSON.parse(content) as AIAnalysis;
        return parsed;
    } else {
        throw new Error("No content returned");
    }
  } catch (error) {
    console.error("OpenAI Analysis Error:", error);
    return {
        diagnosis: "AI Analysis unavailable. Focus on your Win Rate and Profit Factor manually.",
        rule: "Cut losers faster than you think.",
        bias: "Service Error",
        fix: "Check API Key or Network."
    };
  }
};

