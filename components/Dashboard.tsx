import React, { useEffect, useState } from 'react';
import { AnalysisResult, AIAnalysis, EnrichedTrade, BehavioralMetrics } from '../types';
import { getAIInterpretation } from '../services/openaiService';
import { BiasDNARadar, RegretChart, EquityCurveChart } from './Charts';
import { AICoach } from './AICoach';
import { StrategyTagModal } from './StrategyTagModal';
import { AIJudgeModal } from './AIJudgeModal';
import { ToastContainer, ToastType } from './Toast';
import { SummaryView } from './SummaryView'; // 새로 만든 요약 컴포넌트
import { 
  ArrowLeft, 
  Sun, 
  Moon, 
  TrendingUp, 
  Award, 
  Brain, 
  DollarSign, 
  BarChart2, 
  RefreshCcw, 
  Skull, 
  HelpCircle, 
  TrendingDown,
  MessageSquare
} from 'lucide-react';

interface DashboardProps {
  data: AnalysisResult;
  onReset: () => void;
}

// 화면 모드 타입 정의
type ViewMode = 'SUMMARY' | 'FULL' | 'SCORE' | 'BIAS' | 'SIMULATION';

export const Dashboard: React.FC<DashboardProps> = ({ data, onReset }) => {
  // --- State 정의 ---
  const [viewMode, setViewMode] = useState<ViewMode>('SUMMARY');
  
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [loadingAI, setLoadingAI] = useState(false);
  const [showDeepDive, setShowDeepDive] = useState(false);
  const [showBiasFreeSimulation, setShowBiasFreeSimulation] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  
  // Strategy Tagging State
  const [selectedTrade, setSelectedTrade] = useState<EnrichedTrade | null>(null);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [trades, setTrades] = useState<EnrichedTrade[]>(data.trades);
  
  // AI Judge Modal State
  const [selectedTradeForJudge, setSelectedTradeForJudge] = useState<EnrichedTrade | null>(null);
  const [showAIJudgeModal, setShowAIJudgeModal] = useState(false);
  
  // 3중 분석 구조 State
  const [narrativeData, setNarrativeData] = useState<Array<{ ticker: string; narrative: string; source: string }>>([]);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  
  // Chart Interaction State
  const [selectedTradeFromChart, setSelectedTradeFromChart] = useState<EnrichedTrade | null>(null);
  
  // Truth Score 애니메이션 & Display State
  const [isScoreVisible, setIsScoreVisible] = useState(false);
  const [displayMetrics, setDisplayMetrics] = useState(data.metrics);
  const [displayScore, setDisplayScore] = useState(data.metrics.truthScore);
  
  // Toast State
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type?: ToastType }>>([]);
  
  // --- Helper Functions ---

  const showToast = (message: string, type: ToastType = 'info') => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, message, type }]);
  };
  
  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // 테마 토글
  const toggleTheme = () => {
    const newMode = !isDarkMode;
    setIsDarkMode(newMode);
    if (newMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  // --- 초기화 Effects ---

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
      setIsDarkMode(false);
      document.documentElement.classList.remove('dark');
    } else {
      setIsDarkMode(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  useEffect(() => {
    setTrades(data.trades);
  }, [data.trades]);

  useEffect(() => {
    setIsScoreVisible(false);
    setDisplayMetrics(data.metrics);
    setDisplayScore(data.metrics.truthScore);
    const timer = setTimeout(() => setIsScoreVisible(true), 300);
    return () => clearTimeout(timer);
  }, [data.metrics.truthScore]);

  useEffect(() => {
    if (data.benchmarkLoadFailed) {
      showToast('⚠️ 시장 데이터 연동 실패로 인해 벤치마크(SPY) 비교가 제한됩니다.', 'warning');
    }
  }, [data.benchmarkLoadFailed]);

  // --- Narrative 로직 ---
  const getSampleTradesForNarrative = (tradesList: EnrichedTrade[]) => {
    const highFomo = [...tradesList].filter(t => t.fomoScore > 0.7 && t.fomoScore !== -1).sort((a, b) => b.fomoScore - a.fomoScore).slice(0, 3);
    const bigLosses = [...tradesList].filter(t => t.pnl < 0).sort((a, b) => a.pnl - b.pnl).slice(0, 2);
    const unique = [...new Map([...highFomo, ...bigLosses].map(t => [t.id, t])).values()];
    return unique.slice(0, 5);
  };

  const generateFallbackNarrative = (trade: EnrichedTrade) => {
    const fomo = trade.fomoScore;
    const panic = trade.panicScore;
    const regime = trade.marketRegime || 'UNKNOWN';
    const narratives = [];
    if (fomo > 0.7) {
      if (regime === 'BEAR') narratives.push("하락장 반등 추격 매수로 판단됩니다");
      else narratives.push("상승 추세 후반부 고점 진입으로 보입니다");
    }
    if (panic < 0.3 && panic !== -1) {
      if (regime === 'BULL') narratives.push("상승장에서 공포 매도는 기회 비용이 큽니다");
      else narratives.push("급락 구간에서의 저점 매도 패턴입니다");
    }
    if (narratives.length === 0) return "수식 기반 분석: 행동 편향이 감지되었으나 뉴스 맥락은 확인되지 않았습니다";
    return narratives.join(" | ");
  };

  useEffect(() => {
    const sampleTrades = getSampleTradesForNarrative(data.trades);
    if (sampleTrades.length === 0) return;

    setNarrativeLoading(true);
    Promise.all(
      sampleTrades.map(async (trade) => {
        try {
          const response = await fetch('http://localhost:8000/verify-news', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: trade.ticker, date: trade.entryDate, fomo_score: trade.fomoScore })
          });
          if (response.ok) {
            const verification = await response.json();
            return { ticker: trade.ticker, narrative: verification.reasoning || generateFallbackNarrative(trade), source: verification.source || 'none' };
          } else {
            return { ticker: trade.ticker, narrative: generateFallbackNarrative(trade), source: 'none' };
          }
        } catch {
          return { ticker: trade.ticker, narrative: generateFallbackNarrative(trade), source: 'none' };
        }
      })
    ).then(results => {
      setNarrativeData(results);
      setNarrativeLoading(false);
    });
  }, [data.trades]);

  // --- 메트릭 재계산 로직 ---

  const recalculateFOMO = (tradesList: EnrichedTrade[]) => {
    const excludedFromFOMO = tradesList.filter(t => t.strategyTag === 'BREAKOUT' || t.strategyTag === 'AGGRESSIVE_ENTRY');
    const fomoEligibleTrades = tradesList.filter(t => t.fomoScore !== -1 && t.strategyTag !== 'BREAKOUT' && t.strategyTag !== 'AGGRESSIVE_ENTRY');
    const adjustedFomoIndex = fomoEligibleTrades.length > 0
      ? fomoEligibleTrades.reduce((sum, t) => sum + t.fomoScore, 0) / fomoEligibleTrades.length
      : data.metrics.fomoIndex;
    return { adjustedFomoIndex, excludedCount: excludedFromFOMO.length };
  };
  
  const recalculatePanicScore = (tradesList: EnrichedTrade[]) => {
    const excludedFromPanic = tradesList.filter(t => t.strategyTag === 'PLANNED_CUT');
    const panicEligibleTrades = tradesList.filter(t => t.panicScore !== -1 && t.strategyTag !== 'PLANNED_CUT');
    if (panicEligibleTrades.length === 0) return { adjustedPanicIndex: data.metrics.panicIndex, excludedCount: excludedFromPanic.length };
    const avgPanicScore = panicEligibleTrades.reduce((sum, t) => sum + t.panicScore, 0) / panicEligibleTrades.length;
    return { adjustedPanicIndex: 1 - avgPanicScore, excludedCount: excludedFromPanic.length };
  };
  
  const recalculateTruthScore = (tradesList: EnrichedTrade[], currentMetrics: BehavioralMetrics) => {
    const fomoMetrics = recalculateFOMO(tradesList);
    const panicMetrics = recalculatePanicScore(tradesList);
    let baseScore = 50;
    baseScore += (currentMetrics.winRate * 20);
    baseScore -= (fomoMetrics.adjustedFomoIndex * 20);
    baseScore -= ((1 - panicMetrics.adjustedPanicIndex) * 20);
    baseScore -= Math.max(0, (currentMetrics.dispositionRatio - 1) * 10);
    baseScore -= (currentMetrics.revengeTradingCount * 5);
    if (!data.isLowSample) baseScore += (currentMetrics.sharpeRatio * 5);
    else baseScore += 5;
    return Math.max(0, Math.min(100, Math.round(baseScore)));
  };

  // --- AI 데이터 Fetching ---
  useEffect(() => {
    const fetchAI = async () => {
        setLoadingAI(true);
        const fomoMetrics = recalculateFOMO(trades);
        const panicMetrics = recalculatePanicScore(trades);
        const newTruthScore = recalculateTruthScore(trades, {
          ...data.metrics,
          fomoIndex: fomoMetrics.adjustedFomoIndex,
          panicIndex: panicMetrics.adjustedPanicIndex
        });
        const updatedData = { 
          ...data, trades,
          metrics: { ...data.metrics, fomoIndex: fomoMetrics.adjustedFomoIndex, panicIndex: panicMetrics.adjustedPanicIndex, truthScore: newTruthScore }
        };
        const result = await getAIInterpretation(updatedData);
        setAiAnalysis(result);
        setLoadingAI(false);
    };
    const timer = setTimeout(fetchAI, 500);
    return () => clearTimeout(timer);
  }, [data, trades]);

  // --- 핸들러 ---

  const handleStrategyTag = async (trade: EnrichedTrade, tag: 'BREAKOUT' | 'AGGRESSIVE_ENTRY' | 'FOMO' | 'PLANNED_CUT') => {
    const updatedTrades = trades.map(t => t.id === trade.id ? { ...t, strategyTag: tag, userAcknowledged: true } : t);
    setTrades(updatedTrades);
    try {
      await fetch('http://localhost:8000/strategy-tag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trade_id: trade.id, strategy_tag: tag })
      });
    } catch (error) { console.error('Failed to save strategy tag:', error); }
    
    if (tag !== 'FOMO') {
      const fomoMetrics = recalculateFOMO(updatedTrades);
      const panicMetrics = recalculatePanicScore(updatedTrades);
      const newTruthScore = recalculateTruthScore(updatedTrades, { ...data.metrics, fomoIndex: fomoMetrics.adjustedFomoIndex, panicIndex: panicMetrics.adjustedPanicIndex });
      setDisplayMetrics({ ...data.metrics, fomoIndex: fomoMetrics.adjustedFomoIndex, panicIndex: panicMetrics.adjustedPanicIndex, truthScore: newTruthScore });
      setDisplayScore(newTruthScore);
      setIsScoreVisible(false);
      setTimeout(() => setIsScoreVisible(true), 100);
      showToast(`✅ ${tag} 전략이 반영되었습니다.`, 'success');
    } else {
      showToast('인정하셨습니다. 솔직한 인정이 발전의 시작입니다.', 'info');
    }
    setShowStrategyModal(false);
    setSelectedTrade(null);
  };

  const handleSummaryClick = (section: string) => {
    if (section === 'score-card') setViewMode('SCORE');
    else if (section === 'bias-analysis') setViewMode('BIAS');
    else if (section === 'simulator') setViewMode('SIMULATION');
    else setViewMode('FULL');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // --- 렌더링 컴포넌트 분리 ---

  const renderHeader = () => (
    <div className={`sticky top-0 z-20 backdrop-blur-md border-b mb-6 ${isDarkMode ? 'bg-[#09090b]/90 border-zinc-800' : 'bg-white/90 border-zinc-200'}`}>
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {viewMode === 'SUMMARY' ? (
            <button onClick={onReset} className={`p-2 rounded-full transition-colors ${isDarkMode ? 'hover:bg-zinc-800' : 'hover:bg-zinc-100'}`}>
              <ArrowLeft className={`w-5 h-5 ${isDarkMode ? 'text-zinc-400' : 'text-zinc-600'}`} />
            </button>
          ) : (
            <button onClick={() => setViewMode('SUMMARY')} className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-colors text-sm font-medium ${isDarkMode ? 'bg-zinc-800 hover:bg-zinc-700 text-zinc-200' : 'bg-zinc-100 hover:bg-zinc-200 text-zinc-800'}`}>
              <ArrowLeft className="w-4 h-4" /> 요약으로
            </button>
          )}
          <h1 className={`text-lg font-bold tracking-tight ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}>
            Truth Pipeline {viewMode !== 'SUMMARY' && <span className="opacity-50 font-normal text-sm ml-2">/ {viewMode}</span>}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={toggleTheme} className={`p-2 rounded-full transition-colors ${isDarkMode ? 'hover:bg-zinc-800 text-zinc-400' : 'hover:bg-zinc-100 text-zinc-600'}`}>
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );

  const ScoreSection = () => {
    const scoreColor = displayScore >= 75 ? 'text-emerald-400' : displayScore >= 50 ? 'text-yellow-400' : 'text-red-400';
    const scoreRing = displayScore >= 75 ? 'border-emerald-500' : displayScore >= 50 ? 'border-yellow-500' : 'border-red-500';
    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className={`lg:col-span-1 rounded-2xl p-8 flex flex-col items-center justify-center text-center relative overflow-hidden shadow-2xl border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
             <div className={`absolute top-0 w-full h-1.5 bg-gradient-to-r from-transparent via-current to-transparent opacity-70 ${scoreColor}`}></div>
             <span className={`text-xs font-bold uppercase tracking-widest mb-8 ${isDarkMode ? 'text-zinc-500' : 'text-zinc-600'}`}>Truth Score</span>
             <div className={`w-48 h-48 rounded-full border-8 ${scoreRing} flex items-center justify-center mb-8 shadow-[0_0_30px_rgba(0,0,0,0.5)] relative ${isDarkMode ? 'bg-[#0c0c0e]' : 'bg-white'}`}>
                <span className={`text-7xl font-bold tracking-tighter ${scoreColor} transition-all duration-500 ${isScoreVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-150'}`}>{displayScore}</span>
             </div>
             <div className={`w-full grid grid-cols-2 gap-px rounded-xl overflow-hidden border ${isDarkMode ? 'bg-zinc-800/50 border-zinc-800' : 'bg-zinc-200/50 border-zinc-200'}`}>
                <div className={`p-3 ${isDarkMode ? 'bg-zinc-900' : 'bg-white'}`}>
                    <div className="text-xs text-zinc-500">Win Rate</div>
                    <div className="font-mono font-semibold text-zinc-200">{(data.metrics.winRate * 100).toFixed(0)}%</div>
                </div>
                <div className={`p-3 ${isDarkMode ? 'bg-zinc-900' : 'bg-white'}`}>
                    <div className="text-xs text-zinc-500">Profit Factor</div>
                    <div className="font-mono font-semibold text-zinc-200">{data.metrics.profitFactor.toFixed(2)}</div>
                </div>
             </div>
          </div>
          <div className={`lg:col-span-2 rounded-xl p-6 border flex flex-col ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
            <h3 className="text-sm font-bold uppercase tracking-wider mb-6 flex items-center gap-2 text-zinc-400"><Award className="w-4 h-4"/> 세부 지표 분석</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
               <div className={`p-4 rounded-lg border ${isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                  <div className="flex items-center gap-2 mb-2 text-zinc-500"><TrendingUp className="w-3 h-3"/> FOMO Index</div>
                  <div className={`text-2xl font-mono ${(displayMetrics.fomoIndex || 0) > 0.7 ? 'text-red-400' : 'text-zinc-200'}`}>{((displayMetrics.fomoIndex || 0) * 100).toFixed(0)}%</div>
               </div>
               <div className={`p-4 rounded-lg border ${isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                  <div className="flex items-center gap-2 mb-2 text-zinc-500"><TrendingDown className="w-3 h-3"/> Panic Sell</div>
                  <div className={`text-2xl font-mono ${(data.metrics.panicIndex || 0) < 0.3 ? 'text-orange-400' : 'text-zinc-200'}`}>{((data.metrics.panicIndex || 0) * 100).toFixed(0)}%</div>
               </div>
               <div className={`p-4 rounded-lg border ${isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                  <div className="flex items-center gap-2 mb-2 text-zinc-500"><Skull className="w-3 h-3"/> Revenge Count</div>
                  <div className={`text-2xl font-mono ${data.metrics.revengeTradingCount > 0 ? 'text-red-500' : 'text-zinc-200'}`}>{data.metrics.revengeTradingCount}회</div>
               </div>
               <div className={`p-4 rounded-lg border ${isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                  <div className="flex items-center gap-2 mb-2 text-zinc-500"><RefreshCcw className="w-3 h-3"/> Disposition</div>
                  <div className={`text-2xl font-mono ${data.metrics.dispositionRatio > 1.5 ? 'text-orange-400' : 'text-zinc-200'}`}>{data.metrics.dispositionRatio.toFixed(1)}x</div>
               </div>
               <div className={`p-4 rounded-lg border ${isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                  <div className="flex items-center gap-2 mb-2 text-zinc-500"><HelpCircle className="w-3 h-3"/> Luck/Skill</div>
                  <div className="text-2xl font-mono text-zinc-200">{data.metrics.luckPercentile.toFixed(0)}%</div>
               </div>
               <div className={`p-4 rounded-lg border ${isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                  <div className="flex items-center gap-2 mb-2 text-zinc-500"><TrendingDown className="w-3 h-3"/> Max DD</div>
                  <div className="text-2xl font-mono text-zinc-200">{data.metrics.maxDrawdown.toFixed(1)}%</div>
               </div>
            </div>
          </div>
        </div>
        {(data.personalBaseline || data.behaviorShift) && (
           <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {data.personalBaseline && (
                  <div className={`rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
                      <h3 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2 text-zinc-400"><TrendingUp className="w-4 h-4"/> 개인 기준선 (평균)</h3>
                      <div className="space-y-3">
                          <div className="flex justify-between p-3 rounded bg-zinc-950/50 border border-zinc-800">
                              <span className="text-zinc-400">Avg FOMO</span>
                              <span className="text-zinc-200 font-mono">{(data.personalBaseline.avgFomo * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex justify-between p-3 rounded bg-zinc-950/50 border border-zinc-800">
                              <span className="text-zinc-400">Avg Panic</span>
                              <span className="text-zinc-200 font-mono">{(data.personalBaseline.avgPanic * 100).toFixed(0)}%</span>
                          </div>
                      </div>
                  </div>
              )}
              {data.behaviorShift && (
                  <div className={`rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
                      <h3 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2 text-zinc-400"><RefreshCcw className="w-4 h-4"/> 최근 변화 (vs 기준선)</h3>
                      <div className="space-y-2">
                          {data.behaviorShift.map((shift, i) => (
                              <div key={i} className="flex justify-between items-center p-3 rounded bg-zinc-950/50 border border-zinc-800">
                                  <span className="text-sm text-zinc-300">{shift.bias}</span>
                                  <span className={`text-xs font-bold px-2 py-1 rounded ${shift.trend === 'IMPROVING' ? 'bg-emerald-500/20 text-emerald-400' : shift.trend === 'WORSENING' ? 'bg-red-500/20 text-red-400' : 'bg-zinc-700 text-zinc-400'}`}>
                                      {shift.trend} ({shift.changePercent > 0 ? '+' : ''}{shift.changePercent.toFixed(1)}%)
                                  </span>
                              </div>
                          ))}
                      </div>
                  </div>
              )}
           </div>
        )}
      </div>
    );
  };

  const BiasSection = () => (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
         <div className={`lg:col-span-4 rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
            <h3 className="text-sm font-bold uppercase tracking-wider mb-4 text-zinc-400 flex items-center gap-2"><Brain className="w-4 h-4"/> 심리 DNA</h3>
            <BiasDNARadar metrics={displayMetrics} />
         </div>
         <div className="lg:col-span-8">
            <AICoach analysis={aiAnalysis} loading={loadingAI} truthScore={displayMetrics.truthScore} />
         </div>
      </div>
      <div className={`rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
          <h3 className="text-lg font-bold text-zinc-200 mb-4 flex items-center gap-2"><BarChart2 className="w-5 h-5 text-purple-500"/> 3중 분석 (Behavior → Regime → Narrative)</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
             <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800">
                <div className="text-sm font-bold text-blue-400 mb-2">1단계: 팩트 (Behavior)</div>
                <div className="text-xs space-y-1 text-zinc-400">
                   <div>FOMO: {((displayMetrics.fomoIndex || 0) * 100).toFixed(0)}%</div>
                   <div>Panic: {((data.metrics.panicIndex || 0) * 100).toFixed(0)}%</div>
                </div>
             </div>
             <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800">
                <div className="text-sm font-bold text-yellow-400 mb-2">2단계: 맥락 (Regime)</div>
                <div className="text-xs text-zinc-400">
                   {trades.length > 0 && trades[0].marketRegime} 시장 가중치 적용
                </div>
             </div>
             <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800">
                <div className="text-sm font-bold text-purple-400 mb-2">3단계: 해석 (Narrative)</div>
                <div className="text-xs text-zinc-400 max-h-20 overflow-y-auto">
                   {narrativeLoading ? "분석 중..." : narrativeData[0]?.narrative || "뉴스 데이터 없음"}
                </div>
             </div>
          </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
         {data.patterns && data.patterns.length > 0 && (
            <div className={`rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
               <h3 className="text-sm font-bold text-purple-400 mb-4">반복 패턴 (과정 평가)</h3>
               <div className="space-y-2">
                  {data.patterns.map((p, i) => (
                     <div key={i} className="text-xs p-3 rounded bg-zinc-950 border border-zinc-800 text-zinc-300">
                        {p.description}
                     </div>
                  ))}
               </div>
            </div>
         )}
         {data.deepPatterns && data.deepPatterns.length > 0 && (
            <div className={`rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
               <h3 className="text-sm font-bold text-indigo-400 mb-4">AI 심층 패턴 (Cluster)</h3>
               <div className="space-y-2">
                  {data.deepPatterns.map((p, i) => (
                     <div key={i} className="text-xs p-3 rounded bg-zinc-950 border border-zinc-800 text-zinc-300">
                        <span className="text-indigo-400 font-bold">[{p.type}]</span> {p.description}
                     </div>
                  ))}
               </div>
            </div>
         )}
      </div>
    </div>
  );

  const SimulationSection = () => {
    const biasFree = data.biasFreeMetrics || (data.biasLossMapping ? {
       currentPnL: trades.reduce((sum, t) => sum + t.pnl, 0),
       potentialPnL: trades.reduce((sum, t) => sum + t.pnl, 0) + (data.biasLossMapping.fomoLoss + data.biasLossMapping.panicLoss + data.biasLossMapping.revengeLoss + data.biasLossMapping.dispositionLoss),
       biasLoss: (data.biasLossMapping.fomoLoss + data.biasLossMapping.panicLoss + data.biasLossMapping.revengeLoss + data.biasLossMapping.dispositionLoss),
       opportunityCost: 0,
       adjustedImprovement: (data.biasLossMapping.fomoLoss + data.biasLossMapping.panicLoss + data.biasLossMapping.revengeLoss + data.biasLossMapping.dispositionLoss)
    } : null);

    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
         <div className={`rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
            <div className="flex justify-between mb-4">
               <h3 className="text-sm font-bold text-zinc-400 flex items-center gap-2"><TrendingUp className="w-4 h-4"/> 누적 수익 곡선 (Equity Curve)</h3>
               <label className="flex items-center gap-2 cursor-pointer text-xs text-purple-400">
                  <input type="checkbox" checked={showBiasFreeSimulation} onChange={e => setShowBiasFreeSimulation(e.target.checked)} className="rounded bg-zinc-800 border-zinc-700"/>
                  편향 제거 시뮬레이션 보기
               </label>
            </div>
            <EquityCurveChart 
               equityCurve={data.equityCurve || []} 
               biasFreeMetrics={biasFree ? { improvement: biasFree.adjustedImprovement } : null}
               showBiasFree={showBiasFreeSimulation}
               onTradeClick={(id) => { 
                  const t = trades.find(tr => tr.id === id); 
                  if (t) setSelectedTradeFromChart(t);
               }}
               demoMode={data.dataSource === 'CLIENT_DEMO'}
            />
         </div>
         {biasFree && (
            <div className={`rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
               <h3 className="text-sm font-bold text-emerald-400 mb-6 flex items-center gap-2"><DollarSign className="w-4 h-4"/> What-If Simulator</h3>
               <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded bg-zinc-950 border border-zinc-800 text-center">
                     <div className="text-xs text-zinc-500 mb-1">현재 수익</div>
                     <div className={`text-2xl font-mono font-bold ${biasFree.currentPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${biasFree.currentPnL.toFixed(0)}</div>
                  </div>
                  <div className="p-4 rounded bg-purple-900/10 border border-purple-500/30 text-center">
                     <div className="text-xs text-purple-400 mb-1">잠재 수익 (편향 제거 시)</div>
                     <div className="text-2xl font-mono font-bold text-purple-300">${biasFree.potentialPnL.toFixed(0)}</div>
                  </div>
                  <div className="p-4 rounded bg-zinc-950 border border-zinc-800 text-center flex flex-col justify-center">
                     <div className="text-xs text-zinc-500 mb-1">놓친 돈 (수업료)</div>
                     <div className="text-xl font-mono font-bold text-zinc-300 flex items-center justify-center gap-2">
                        <span>${biasFree.biasLoss.toFixed(0)}</span>
                        <span className="text-[10px] px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded-full">손실</span>
                     </div>
                  </div>
               </div>
               <div className="mt-4 text-center text-sm text-zinc-400">
                  습관만 고쳤어도 <span className="text-emerald-400 font-bold">+${biasFree.adjustedImprovement.toFixed(0)}</span>의 추가 수익이 가능했습니다.
               </div>
            </div>
         )}
         <div className={`rounded-xl p-6 border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
            <h3 className="text-sm font-bold text-orange-400 mb-4">가장 아쉬운 종목 (Regret Top 5)</h3>
            <RegretChart trades={trades} />
         </div>
      </div>
    );
  };

  const TradeLogSection = () => (
    <div className={`mt-12 rounded-xl overflow-hidden border ${isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
       <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-950/30">
          <h3 className="font-bold text-sm text-zinc-400">모든 거래 기록 (Trade Log)</h3>
          <button onClick={() => setShowDeepDive(!showDeepDive)} className="text-xs text-zinc-500 hover:text-zinc-300">
             {showDeepDive ? '접기' : '펼치기'}
          </button>
       </div>
       {showDeepDive && (
          <div className="overflow-x-auto p-4">
             <table className="w-full text-sm text-left text-zinc-400">
                <thead className="text-xs text-zinc-500 uppercase bg-zinc-950">
                    <tr>
                        <th className="px-6 py-3">Ticker</th>
                        <th className="px-6 py-3">Entry / Exit</th>
                        <th className="px-6 py-3 text-right">PnL</th>
                        <th className="px-6 py-3 text-center">FOMO</th>
                        <th className="px-6 py-3 text-center">Panic</th>
                        <th className="px-6 py-3 text-center">Tag</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                    {trades.map(trade => (
                        <React.Fragment key={trade.id}>
                        <tr className="hover:bg-zinc-900">
                            <td className="px-6 py-4 font-medium text-zinc-300">{trade.ticker}</td>
                            <td className="px-6 py-4">
                                <div className="flex flex-col text-xs">
                                    <span className="text-emerald-500">Buy: {trade.entryDate} @ {trade.entryPrice}</span>
                                    <span className="text-red-500">Sell: {trade.exitDate} @ {trade.exitPrice}</span>
                                </div>
                            </td>
                            <td className={`px-6 py-4 text-right font-mono ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${trade.pnl.toFixed(0)}</td>
                            <td className="px-6 py-4 text-center font-mono">{trade.fomoScore !== -1 ? `${(trade.fomoScore * 100).toFixed(0)}%` : '-'}</td>
                            <td className="px-6 py-4 text-center font-mono">{trade.panicScore !== -1 ? `${(trade.panicScore * 100).toFixed(0)}%` : '-'}</td>
                            <td className="px-6 py-4 text-center">
                                {trade.fomoScore > 0.7 && !trade.userAcknowledged && (
                                    <button onClick={() => { setSelectedTrade(trade); setShowStrategyModal(true); }} className="text-xs px-2 py-1 bg-orange-900/30 text-orange-400 rounded border border-orange-800 hover:bg-orange-900/50">소명</button>
                                )}
                                {trade.strategyTag && <span className="text-xs text-blue-400">{trade.strategyTag}</span>}
                            </td>
                        </tr>
                        {/* Contextual Score Breakdown Row */}
                        {trade.baseScore !== null && trade.baseScore !== undefined && (
                            <tr className="bg-zinc-950/30">
                                <td colSpan={6} className="px-6 py-2">
                                    <div className="text-xs text-zinc-500 flex gap-4">
                                        <span>Base Score: {trade.baseScore.toFixed(1)}</span>
                                        <span>× Volume: {trade.volumeWeight?.toFixed(1)}</span>
                                        <span>× Regime: {trade.regimeWeight?.toFixed(1)}</span>
                                        <span className="text-purple-400 font-bold">= Contextual: {trade.contextualScore?.toFixed(1)}</span>
                                    </div>
                                </td>
                            </tr>
                        )}
                        </React.Fragment>
                    ))}
                </tbody>
             </table>
          </div>
       )}
    </div>
  );

  // --- 메인 렌더링 ---
  if (viewMode === 'SUMMARY') {
    return <SummaryView data={data} onDetailsClick={handleSummaryClick} />;
  }

  return (
    <div className={`min-h-screen font-sans selection:bg-emerald-900/30 ${isDarkMode ? 'bg-[#09090b] text-zinc-200' : 'bg-white text-zinc-900'}`}>
      {renderHeader()}
      <div className="max-w-7xl mx-auto p-4 md:p-8 pb-20">
        {viewMode === 'SCORE' && <ScoreSection />}
        {viewMode === 'BIAS' && <BiasSection />}
        {viewMode === 'SIMULATION' && <SimulationSection />}
        {viewMode === 'FULL' && (
           <div className="space-y-12">
              <ScoreSection />
              <BiasSection />
              <SimulationSection />
           </div>
        )}
        <TradeLogSection />
      </div>
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      {selectedTrade && (
        <StrategyTagModal
          trade={selectedTrade}
          isOpen={showStrategyModal}
          onClose={() => { setShowStrategyModal(false); setSelectedTrade(null); }}
          onConfirm={(tag) => handleStrategyTag(selectedTrade, tag)}
          isDarkMode={isDarkMode}
        />
      )}
      {selectedTradeForJudge && (
        <AIJudgeModal
          trade={selectedTradeForJudge}
          isOpen={showAIJudgeModal}
          onClose={() => { setShowAIJudgeModal(false); setSelectedTradeForJudge(null); }}
          onAppeal={() => { setShowAIJudgeModal(false); setSelectedTrade(selectedTradeForJudge); setShowStrategyModal(true); setSelectedTradeForJudge(null); }}
          isDarkMode={isDarkMode}
        />
      )}
    </div>
  );
};