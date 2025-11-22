
import { GoogleGenAI, Type } from "@google/genai";
import { AnalysisResult, AIAnalysis } from "../types";

export const getAIInterpretation = async (data: AnalysisResult): Promise<AIAnalysis> => {
  if (!process.env.API_KEY) {
    return {
        diagnosis: "API Key missing. Please configure your environment to unlock the Truth.",
        rule: "No rule generated.",
        bias: "N/A",
        fix: "Add API Key"
    };
  }

  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

  // Prepare granular context
  const topRegrets = data.trades
    .sort((a, b) => b.regret - a.regret)
    .slice(0, 3)
    .map(t => `${t.ticker} (Missed $${t.regret.toFixed(0)})`);

  const revengeDetails = data.revengeTrades.map(t => `${t.ticker} (-$${Math.abs(t.pnl).toFixed(0)})`).join(', ');

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

    EVIDENCE STRUCTURE (You MUST reference these numbers in your diagnosis):
    - Evidence #1: FOMO Score ${(data.metrics.fomoIndex * 100).toFixed(0)}% (Threshold > 70% is bad)
    - Evidence #2: Panic Sell Score ${(data.metrics.panicIndex * 100).toFixed(0)}% (Threshold > 70% is bad)
    - Evidence #3: Disposition Ratio ${data.metrics.dispositionRatio.toFixed(1)}x (Threshold > 1.5x is bad)
    - Evidence #4: Revenge Trading Count ${data.metrics.revengeTradingCount} (Threshold > 0 is bad)
    - Evidence #5: Total Regret $${data.metrics.totalRegret.toFixed(0)}

    INSTRUCTIONS:
    1. DIAGNOSIS (3 sentences): 
       - Sentence 1: Direct, slightly harsh observation of their biggest flaw (FOMO, Weak Hands, or Revenge).
       - Sentence 2: EVIDENCE-BASED FACT. You MUST strictly follow this format: "According to Evidence #X, you [specific action] on [Ticker]." Example: "According to Evidence #1, you bought GME at 93% of the day's range."
       - Sentence 3: The financial impact of this behavior.
    2. RULE (1 sentence): A catchy, memorable trading commandment to fix this specific flaw.
    3. BIAS: Name the single dominant psychological bias (e.g. Disposition Effect, Action Bias, Revenge Trading, FOMO).
    4. FIX: One specific, actionable step to take immediately.

    Output valid JSON only.
  `;

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
            type: Type.OBJECT,
            properties: {
                diagnosis: { type: Type.STRING, description: "3 sentences. Must mention a ticker." },
                rule: { type: Type.STRING, description: "1 sentence rule." },
                bias: { type: Type.STRING, description: "Primary bias." },
                fix: { type: Type.STRING, description: "Priority fix." }
            },
            required: ["diagnosis", "rule", "bias", "fix"]
        }
      }
    });

    if (response.text) {
        return JSON.parse(response.text) as AIAnalysis;
    } else {
        throw new Error("No text returned");
    }
  } catch (error) {
    console.error("Gemini Analysis Error:", error);
    return {
        diagnosis: "AI Analysis unavailable. Focus on your Win Rate and Profit Factor manually.",
        rule: "Cut losers faster than you think.",
        bias: "Service Error",
        fix: "Check API Key or Network."
    };
  }
};
