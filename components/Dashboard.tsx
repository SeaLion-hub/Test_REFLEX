
import React, { useEffect, useState } from 'react';
import { AnalysisResult, AIAnalysis, EnrichedTrade } from '../types';
import { getAIInterpretation } from '../services/openaiService';
import { BehavioralRadar, RegretChart, EquityCurveChart } from './Charts';
import { AICoach } from './AICoach';
import { StrategyTagModal } from './StrategyTagModal';
import { ShieldAlert, TrendingUp, RefreshCcw, Award, BarChart2, HelpCircle, ArrowLeft, ChevronDown, ChevronUp, Database, ServerCrash, Skull, TrendingDown, DollarSign, AlertCircle, CheckCircle2, XCircle, Moon, Sun, BookOpen, MessageSquare } from 'lucide-react';

interface DashboardProps {
  data: AnalysisResult;
  onReset: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ data, onReset }) => {
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [loadingAI, setLoadingAI] = useState(false);
  const [showDeepDive, setShowDeepDive] = useState(false);
  const [showBiasFreeSimulation, setShowBiasFreeSimulation] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  
  // Strategy Tagging State
  const [selectedTrade, setSelectedTrade] = useState<EnrichedTrade | null>(null);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [trades, setTrades] = useState<EnrichedTrade[]>(data.trades);

  useEffect(() => {
    // Load theme preference from localStorage
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
      setIsDarkMode(false);
      document.documentElement.classList.remove('dark');
    } else {
      setIsDarkMode(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

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

  // Sync trades when data changes
  useEffect(() => {
    setTrades(data.trades);
  }, [data.trades]);

  useEffect(() => {
    const fetchAI = async () => {
        setLoadingAI(true);
        // Update data with tagged trades
        const updatedData = { ...data, trades };
        const result = await getAIInterpretation(updatedData);
        setAiAnalysis(result);
        setLoadingAI(false);
    };
    fetchAI();
  }, [data, trades]);
  
  // Recalculate FOMO metrics excluding strategic trades
  const recalculateFOMO = (tradesList: EnrichedTrade[]) => {
    // FOMO 계산에서 제외할 거래: BREAKOUT 또는 AGGRESSIVE_ENTRY 태그가 있는 거래
    const excludedFromFOMO = tradesList.filter(t => 
      t.strategyTag === 'BREAKOUT' || t.strategyTag === 'AGGRESSIVE_ENTRY'
    );
    
    // FOMO 계산 대상 거래 (유효하고 전략 태그가 없는 거래)
    const fomoEligibleTrades = tradesList.filter(t => 
      t.fomoScore !== -1 && 
      t.strategyTag !== 'BREAKOUT' && 
      t.strategyTag !== 'AGGRESSIVE_ENTRY'
    );
    
    const adjustedFomoIndex = fomoEligibleTrades.length > 0
      ? fomoEligibleTrades.reduce((sum, t) => sum + t.fomoScore, 0) / fomoEligibleTrades.length
      : data.metrics.fomoIndex; // 기본값 사용
    
    return {
      adjustedFomoIndex,
      excludedCount: excludedFromFOMO.length,
      eligibleCount: fomoEligibleTrades.length
    };
  };
  
  // Handle Strategy Tagging
  const handleStrategyTag = async (trade: EnrichedTrade, tag: 'BREAKOUT' | 'AGGRESSIVE_ENTRY' | 'FOMO') => {
    // Update trade strategy tag
    const updatedTrades = trades.map(t => 
      t.id === trade.id 
        ? { ...t, strategyTag: tag, userAcknowledged: true }
        : t
    );
    setTrades(updatedTrades);
    
    // Send to backend to persist
    try {
      await fetch('http://localhost:8000/strategy-tag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trade_id: trade.id,
          strategy_tag: tag
        })
      });
    } catch (error) {
      console.error('Failed to save strategy tag:', error);
      // Continue anyway - local state is updated
    }
    
    // Recalculate metrics if strategic tag added
    if (tag === 'BREAKOUT' || tag === 'AGGRESSIVE_ENTRY') {
      const fomoMetrics = recalculateFOMO(updatedTrades);
      // Update metrics display (optional - could show adjusted FOMO)
      console.log('Adjusted FOMO Index:', fomoMetrics.adjustedFomoIndex);
      console.log(`Excluded ${fomoMetrics.excludedCount} strategic trades from FOMO calculation`);
    }
    
    setShowStrategyModal(false);
    setSelectedTrade(null);
  };
  
  const openStrategyModal = (trade: EnrichedTrade) => {
    setSelectedTrade(trade);
    setShowStrategyModal(true);
  };

  const { metrics, isLowSample } = data;
  // Ensure types are safe for display
  const totalPnL = trades.reduce((a, b) => a + (b.pnl || 0), 0);
  
  // Calculate adjusted FOMO metrics (excluding strategic trades)
  const fomoMetrics = recalculateFOMO(trades);
  const adjustedMetrics = {
    ...metrics,
    fomoIndex: fomoMetrics.excludedCount > 0 
      ? fomoMetrics.adjustedFomoIndex 
      : metrics.fomoIndex
  };
  
  // Color logic (use adjusted metrics)
  const scoreColor = adjustedMetrics.truthScore >= 75 ? 'text-emerald-400' : adjustedMetrics.truthScore >= 50 ? 'text-yellow-400' : 'text-red-400';
  const scoreRing = adjustedMetrics.truthScore >= 75 ? 'border-emerald-500' : adjustedMetrics.truthScore >= 50 ? 'border-yellow-500' : 'border-red-500';

  // Identify Top Issues (use adjusted metrics)
  const issues = [
    { label: 'FOMO', value: (adjustedMetrics.fomoIndex * 100).toFixed(0) + '%', severity: adjustedMetrics.fomoIndex > 0.6 },
    { label: 'Panic Sell', value: (metrics.panicIndex * 100).toFixed(0) + '%', severity: metrics.panicIndex > 0.6 },
    { label: 'Revenge', value: metrics.revengeTradingCount + 'x', severity: metrics.revengeTradingCount > 0 },
    { label: 'Holding Losers', value: metrics.dispositionRatio.toFixed(1) + 'x', severity: metrics.dispositionRatio > 1.2 }
  ];
  const topIssues = issues.filter(i => i.severity).slice(0, 3);

  // Prepare Evidence items for checklist display
  const evidenceItems = [
    {
      label: 'FOMO Score' + (fomoMetrics.excludedCount > 0 ? ` (${fomoMetrics.excludedCount}건 제외)` : ''),
      value: (adjustedMetrics.fomoIndex * 100).toFixed(0) + '%',
      threshold: '>70%',
      status: adjustedMetrics.fomoIndex > 0.7 ? 'warning' : 'normal',
      description: fomoMetrics.excludedCount > 0 
        ? `Entry vs Daily High - 전략 태그된 ${fomoMetrics.excludedCount}건 제외 후 계산`
        : 'Entry vs Daily High - Clinical FOMO threshold: >70%',
      aiTransmitted: true
    },
    {
      label: 'Exit Efficiency',
      value: (metrics.panicIndex * 100).toFixed(0) + '%',
      threshold: '<30%',
      status: metrics.panicIndex < 0.3 ? 'warning' : 'normal',
      description: 'Exit vs Daily Low - Low efficiency (<30%) indicates inefficient exit timing',
      aiTransmitted: true
    },
    {
      label: 'Disposition Ratio',
      value: metrics.dispositionRatio.toFixed(1) + 'x',
      threshold: '>1.5x',
      status: metrics.dispositionRatio > 1.5 ? 'warning' : 'normal',
      description: 'Hold losers vs winners - Clinical threshold: >1.5x',
      aiTransmitted: true
    },
    {
      label: 'Revenge Trading',
      value: metrics.revengeTradingCount + ' trades',
      threshold: '>0',
      status: metrics.revengeTradingCount > 0 ? 'warning' : 'normal',
      description: 'Re-entry <24h after loss',
      aiTransmitted: true
    },
    {
      label: 'Total Regret',
      value: '$' + metrics.totalRegret.toFixed(0),
      threshold: 'Any amount',
      status: metrics.totalRegret > 0 ? 'info' : 'normal',
      description: 'Money left on table',
      aiTransmitted: true
    },
    {
      label: 'Profit Factor',
      value: metrics.profitFactor.toFixed(2),
      threshold: '>1.0',
      status: metrics.profitFactor > 1.0 ? 'normal' : 'warning',
      description: 'Win vs Loss ratio',
      aiTransmitted: true
    },
    {
      label: 'Win Rate',
      value: (metrics.winRate * 100).toFixed(0) + '%',
      threshold: '>50%',
      status: metrics.winRate > 0.5 ? 'normal' : 'warning',
      description: 'Percentage of winning trades',
      aiTransmitted: true
    }
  ];

  // 편향 제거 시뮬레이션 계산
  const biasFreeMetrics = React.useMemo(() => {
    if (!data.biasLossMapping) return null;
    
    const totalBiasLoss = 
      data.biasLossMapping.fomoLoss +
      data.biasLossMapping.panicLoss +
      data.biasLossMapping.revengeLoss +
      data.biasLossMapping.dispositionLoss;
    
    const currentTotalPnL = data.trades.reduce((sum, t) => sum + t.pnl, 0);
    const potentialPnL = currentTotalPnL + totalBiasLoss;
    
    // 환산 (예: 아이폰 가격 대비)
    const iphonePrice = 1200; // $1200 가정
    const equivalentItems = Math.abs(totalBiasLoss) / iphonePrice;
    
    return {
      currentPnL: currentTotalPnL,
      potentialPnL,
      biasLoss: totalBiasLoss,
      improvement: potentialPnL - currentTotalPnL,
      equivalentItems,
      itemName: 'iPhone'
    };
  }, [data.biasLossMapping, data.trades]);

  return (
    <div className={`min-h-screen font-sans selection:bg-emerald-900/30 ${
      isDarkMode 
        ? 'bg-[#09090b] text-zinc-200' 
        : 'bg-white text-zinc-900'
    }`}>
      
      {/* LEVEL 1: HEADER & CONTEXT */}
      <div className={`sticky top-0 z-20 backdrop-blur-md border-b ${
        isDarkMode 
          ? 'bg-[#09090b]/90 border-zinc-800' 
          : 'bg-white/90 border-zinc-200'
      }`}>
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
                <button onClick={onReset} className={`p-2 rounded-full transition-colors ${
                  isDarkMode ? 'hover:bg-zinc-800' : 'hover:bg-zinc-100'
                }`}>
                    <ArrowLeft className={`w-5 h-5 ${isDarkMode ? 'text-zinc-400' : 'text-zinc-600'}`} />
                </button>
                <div>
                    <h1 className={`text-lg font-bold tracking-tight ${
                      isDarkMode ? 'text-white' : 'text-zinc-900'
                    }`}>Truth Pipeline</h1>
                </div>
            </div>
            <div className="flex items-center gap-3">
                {/* Theme Toggle */}
                <button
                  onClick={toggleTheme}
                  className={`p-2 rounded-full transition-colors ${
                    isDarkMode 
                      ? 'hover:bg-zinc-800 text-zinc-400' 
                      : 'hover:bg-zinc-100 text-zinc-600'
                  }`}
                  title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                >
                  {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                </button>
                {/* Backend Status Indicator */}
                {data.dataSource === 'BACKEND_TRUTH' ? (
                    <div className={`flex items-center gap-2 px-3 py-1 text-xs rounded-full border shadow-[0_0_10px_rgba(16,185,129,0.1)] ${
                      isDarkMode
                        ? 'bg-emerald-950/50 text-emerald-400 border-emerald-900/30'
                        : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                    }`}>
                        <Database className="w-3 h-3" />
                        <span className="font-medium">Truth Engine Live</span>
                    </div>
                ) : (
                    <div className={`flex items-center gap-2 px-3 py-1 text-xs rounded-full border ${
                      isDarkMode
                        ? 'bg-orange-950/50 text-orange-400 border-orange-900/30'
                        : 'bg-orange-50 text-orange-600 border-orange-200'
                    }`}>
                        <ServerCrash className="w-3 h-3" />
                        <span className="font-medium">Demo Data (Offline)</span>
                    </div>
                )}
            </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-8">
        
        {/* LEVEL 2: THE VERDICT (HERO SECTION) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Truth Score Card */}
            <div className={`lg:col-span-4 rounded-2xl p-8 flex flex-col items-center justify-center text-center relative overflow-hidden shadow-2xl ${
              isDarkMode 
                ? 'bg-zinc-900 border-zinc-800' 
                : 'bg-zinc-50 border-zinc-200'
            } border`}>
                 <div className={`absolute top-0 w-full h-1.5 bg-gradient-to-r from-transparent via-current to-transparent opacity-70 ${scoreColor}`}></div>
                 
                 <span className={`text-xs font-bold uppercase tracking-widest mb-8 ${
                   isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                 }`}>Behavioral Integrity Score</span>
                 
                 <div className={`w-48 h-48 rounded-full border-8 ${scoreRing} flex items-center justify-center mb-8 shadow-[0_0_30px_rgba(0,0,0,0.5)] relative ${
                   isDarkMode ? 'bg-[#0c0c0e]' : 'bg-white'
                 }`}>
                    <span className={`text-7xl font-bold tracking-tighter ${scoreColor}`}>{adjustedMetrics.truthScore}</span>
                    {isLowSample && (
                        <div className={`absolute bottom-8 text-xs px-2 py-1 rounded ${
                          isDarkMode 
                            ? 'bg-zinc-800 text-zinc-400' 
                            : 'bg-zinc-200 text-zinc-600'
                        }`}>Low Sample</div>
                    )}
                 </div>
                 
                 {/* Top Issues Badges */}
                 {topIssues.length > 0 && (
                     <div className="flex flex-wrap justify-center gap-2 mb-8 max-w-[80%]">
                         {topIssues.map((issue, idx) => (
                             <div key={idx} className="flex items-center gap-2 px-3 py-1.5 bg-red-950/30 border border-red-900/40 rounded-full">
                                 <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
                                 <span className="text-xs font-bold text-red-400 uppercase tracking-wide">{issue.label}: {issue.value}</span>
                             </div>
                         ))}
                     </div>
                 )}

                 <div className={`w-full grid grid-cols-3 gap-px rounded-xl overflow-hidden border ${
                   isDarkMode 
                     ? 'bg-zinc-800/50 border-zinc-800' 
                     : 'bg-zinc-200/50 border-zinc-200'
                 }`}>
                    <div className={`p-3 ${isDarkMode ? 'bg-zinc-900' : 'bg-white'}`}>
                        <div className={`text-xs uppercase ${
                          isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                        }`}>Win Rate</div>
                        <div className={`font-mono font-semibold ${
                          isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                        }`}>{(adjustedMetrics.winRate * 100).toFixed(0)}%</div>
                    </div>
                    <div className={`p-3 ${isDarkMode ? 'bg-zinc-900' : 'bg-white'}`}>
                        <div className={`text-xs uppercase ${
                          isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                        }`}>Profit F.</div>
                        <div className={`font-mono font-semibold ${
                          isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                        }`}>{adjustedMetrics.profitFactor.toFixed(2)}</div>
                    </div>
                    <div className={`p-3 ${isDarkMode ? 'bg-zinc-900' : 'bg-white'}`}>
                        <div className={`text-xs uppercase ${
                          isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                        }`}>Total PnL</div>
                        <div className={`font-mono font-semibold ${totalPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            ${Math.abs(totalPnL) >= 1000 ? (Math.abs(totalPnL)/1000).toFixed(1)+'k' : Math.abs(totalPnL).toFixed(0)}
                        </div>
                    </div>
                 </div>
            </div>

            {/* AI Coach */}
            <div className="lg:col-span-8 h-full">
                 <AICoach analysis={aiAnalysis} loading={loadingAI} />
            </div>
        </div>

        {/* CLINICAL THRESHOLDS INFO */}
        <div className={`rounded-xl p-4 border ${
          isDarkMode 
            ? 'bg-blue-950/20 border-blue-900/30' 
            : 'bg-blue-50 border-blue-200'
        }`}>
          <div className="flex items-start gap-3">
            <HelpCircle className={`w-5 h-5 mt-0.5 ${
              isDarkMode ? 'text-blue-400' : 'text-blue-600'
            }`} />
            <div className="flex-1">
              <h4 className={`text-sm font-semibold mb-2 ${
                isDarkMode ? 'text-blue-300' : 'text-blue-900'
              }`}>Clinical Thresholds (보수적 기준)</h4>
              <div className={`text-xs space-y-1 ${
                isDarkMode ? 'text-blue-200/80' : 'text-blue-800'
              }`}>
                <p>• <strong>FOMO:</strong> Entry &gt;70% of day's range = Clinical FOMO (행동경제학 연구 기반)</p>
                <p>• <strong>Exit Efficiency:</strong> Exit &lt;30% of day's range = Low Efficiency (행동경제학 연구 기반)</p>
                <p>• <strong>Disposition Effect:</strong> Hold losers &gt;1.5x longer = Clinical Disposition (Shefrin & Statman 연구)</p>
                <p className={`mt-2 pt-2 border-t ${
                  isDarkMode ? 'border-blue-900/30' : 'border-blue-200'
                }`}>
                  <strong>중요:</strong> 이 지표는 <strong>행동 편향</strong>을 탐지합니다. 기술적 돌파매매나 모멘텀 전략과는 다릅니다. 
                  높은 FOMO 점수는 "돌파 전략"이 아니라 "놓칠까봐 두려워서 고가에 매수"를 의미합니다.
                </p>
                <p className={`mt-2 pt-2 border-t ${
                  isDarkMode ? 'border-blue-900/30' : 'border-blue-200'
                }`}>
                  <strong>과정 평가 (Process Evaluation):</strong> 단일 거래의 결과가 아니라 <strong>반복되는 패턴</strong>에 집중합니다. 
                  "한두 번은 운 탓일 수 있지만, 10번 반복되면 실력(편향)입니다."
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* LEVEL 3: BEHAVIORAL EVIDENCE & PSYCHOLOGY */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
             
             {/* Left: Radar Chart */}
             <div className={`rounded-xl p-6 flex flex-col justify-between shadow-lg border ${
               isDarkMode 
                 ? 'bg-zinc-900 border-zinc-800' 
                 : 'bg-zinc-50 border-zinc-200'
             }`}>
                <div className="flex items-center gap-2 mb-4">
                    <BarChart2 className={`w-4 h-4 ${isDarkMode ? 'text-emerald-500' : 'text-emerald-600'}`} />
                    <h3 className={`text-sm font-bold uppercase tracking-wider ${
                      isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                    }`}>Psychology Map</h3>
                </div>
                <div className="flex-grow flex items-center justify-center">
                    <BehavioralRadar metrics={metrics} />
                </div>
             </div>

             {/* Right: Detailed Metrics Grid */}
             <div className={`lg:col-span-2 rounded-xl p-6 shadow-lg flex flex-col border ${
               isDarkMode 
                 ? 'bg-zinc-900 border-zinc-800' 
                 : 'bg-zinc-50 border-zinc-200'
             }`}>
                <h3 className={`text-sm font-bold uppercase tracking-wider mb-6 flex items-center gap-2 ${
                  isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                }`}>
                    <Award className={`w-4 h-4 ${isDarkMode ? 'text-yellow-500' : 'text-yellow-600'}`} />
                    Key Performance Indicators
                </h3>
                
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
                     <div className={`p-4 rounded-lg border hover:border-zinc-700 transition-colors ${
                       isDarkMode 
                         ? 'bg-zinc-950 border-zinc-800' 
                         : 'bg-zinc-100 border-zinc-300'
                     }`}>
                        <div className={`flex items-center gap-2 mb-2 ${
                          isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                        }`}>
                            <TrendingUp className="w-3 h-3" />
                            <span className="text-xs uppercase font-bold">FOMO Index</span>
                        </div>
                        <div className={`text-2xl font-mono ${
                          adjustedMetrics.fomoIndex > 0.7 
                            ? 'text-red-400' 
                            : isDarkMode ? 'text-white' : 'text-zinc-900'
                        }`}>
                            {(adjustedMetrics.fomoIndex * 100).toFixed(0)}%
                            {fomoMetrics.excludedCount > 0 && (
                              <div className="text-xs text-blue-400 mt-1">
                                ({fomoMetrics.excludedCount}건 제외)
                              </div>
                            )}
                        </div>
                        <div className={`text-xs mt-1 ${
                          isDarkMode ? 'text-zinc-600' : 'text-zinc-500'
                        }`}>
                          Entry vs Daily High
                          <div className="text-[10px] mt-0.5 italic">
                            Clinical threshold: &gt;70% = FOMO
                          </div>
                        </div>
                     </div>

                     <div className={`p-4 rounded-lg border hover:border-zinc-700 transition-colors ${
                       isDarkMode 
                         ? 'bg-zinc-950 border-zinc-800' 
                         : 'bg-zinc-100 border-zinc-300'
                     }`}>
                        <div className={`flex items-center gap-2 mb-2 ${
                          isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                        }`}>
                            <Skull className="w-3 h-3" />
                            <span className="text-xs uppercase font-bold">Revenge Trades</span>
                        </div>
                        <div className={`text-2xl font-mono ${
                          metrics.revengeTradingCount > 0 
                            ? 'text-red-500' 
                            : isDarkMode ? 'text-white' : 'text-zinc-900'
                        }`}>
                            {metrics.revengeTradingCount}
                        </div>
                        <div className={`text-xs mt-1 ${
                          isDarkMode ? 'text-zinc-600' : 'text-zinc-500'
                        }`}>Re-entry &lt; 24h after loss</div>
                     </div>

                     <div className={`p-4 rounded-lg border hover:border-zinc-700 transition-colors ${
                       isDarkMode 
                         ? 'bg-zinc-950 border-zinc-800' 
                         : 'bg-zinc-100 border-zinc-300'
                     }`}>
                        <div className={`flex items-center gap-2 mb-2 ${
                          isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                        }`}>
                            <RefreshCcw className="w-3 h-3" />
                            <span className="text-xs uppercase font-bold">Disposition</span>
                        </div>
                        <div className={`text-2xl font-mono ${
                          metrics.dispositionRatio > 1.5 
                            ? 'text-orange-400' 
                            : isDarkMode ? 'text-white' : 'text-zinc-900'
                        }`}>
                            {metrics.dispositionRatio.toFixed(1)}x
                        </div>
                        <div className={`text-xs mt-1 ${
                          isDarkMode ? 'text-zinc-600' : 'text-zinc-500'
                        }`}>Hold time: Losers vs Winners</div>
                     </div>

                     <div className={`p-4 rounded-lg border hover:border-zinc-700 transition-colors ${
                       isDarkMode 
                         ? 'bg-zinc-950 border-zinc-800' 
                         : 'bg-zinc-100 border-zinc-300'
                     }`}>
                        <div className={`flex items-center gap-2 mb-2 ${
                          isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                        }`}>
                            <HelpCircle className="w-3 h-3" />
                            <span className="text-xs uppercase font-bold">Skill/Luck</span>
                        </div>
                        {isLowSample ? (
                            <div className={`text-xs italic mt-1 ${
                              isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                            }`}>Need 5+ trades</div>
                        ) : (
                             <div className={`text-2xl font-mono ${
                               isDarkMode ? 'text-white' : 'text-zinc-900'
                             }`}>
                                {metrics.luckPercentile.toFixed(0)}%
                            </div>
                        )}
                        {!isLowSample && <div className={`text-xs mt-1 ${
                          isDarkMode ? 'text-zinc-600' : 'text-zinc-500'
                        }`}>Monte Carlo Pctl</div>}
                     </div>
                </div>

                {/* Regret Chart Section */}
                <div className={`mt-auto pt-6 border-t ${
                  isDarkMode ? 'border-zinc-800/50' : 'border-zinc-200/50'
                }`}>
                     <div className="flex items-center justify-between mb-4">
                        <h4 className={`text-xs font-bold uppercase tracking-wide ${
                          isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
                        }`}>Regret Zone: 누적 패턴 분석</h4>
                        <div className="flex items-center gap-2 text-xs">
                            <span className="w-2 h-2 rounded-full bg-orange-500/50"></span>
                            <span className={isDarkMode ? 'text-zinc-500' : 'text-zinc-600'}>
                              총 ${data.trades.reduce((sum, t) => sum + (t.regret || 0), 0).toFixed(0)} 놓침 (누적)
                            </span>
                        </div>
                     </div>
                     <RegretChart trades={data.trades} />
                </div>
             </div>
        </div>

        {/* PERFECT EDITION: PERSONAL BASELINE & BEHAVIOR SHIFT */}
        {(data.personalBaseline || data.behaviorShift) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Personal Baseline */}
                {data.personalBaseline && (
                    <div className={`rounded-xl p-6 border ${
                      isDarkMode 
                        ? 'bg-zinc-900 border-zinc-800' 
                        : 'bg-zinc-50 border-zinc-200'
                    }`}>
                        <div className="flex items-center gap-2 mb-6">
                            <TrendingUp className={`w-5 h-5 ${isDarkMode ? 'text-blue-500' : 'text-blue-600'}`} />
                            <h3 className={`text-sm font-bold uppercase tracking-wider ${
                              isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                            }`}>Personal Baseline</h3>
                        </div>
                        <div className="space-y-4">
                            <div className={`p-3 rounded-lg border ${
                              isDarkMode 
                                ? 'bg-zinc-950 border-zinc-800' 
                                : 'bg-white border-zinc-200'
                            }`}>
                                <div className={`text-xs mb-1 ${
                                  isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                                }`}>FOMO Score</div>
                                <div className="flex items-center justify-between">
                                    <span className={isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}>Your Average: {(data.personalBaseline.avgFomo * 100).toFixed(0)}%</span>
                                    <span className={`text-sm font-mono ${metrics.fomoIndex > data.personalBaseline.avgFomo ? 'text-red-400' : 'text-emerald-400'}`}>
                                        Current: {(metrics.fomoIndex * 100).toFixed(0)}%
                                    </span>
                                </div>
                            </div>
                            <div className={`p-3 rounded-lg border ${
                              isDarkMode 
                                ? 'bg-zinc-950 border-zinc-800' 
                                : 'bg-white border-zinc-200'
                            }`}>
                                <div className={`text-xs mb-1 ${
                                  isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                                }`}>Panic Score</div>
                                <div className="flex items-center justify-between">
                                    <span className={isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}>Your Average: {(data.personalBaseline.avgPanic * 100).toFixed(0)}%</span>
                                    <span className={`text-sm font-mono ${metrics.panicIndex < data.personalBaseline.avgPanic ? 'text-red-400' : 'text-emerald-400'}`}>
                                        Current: {(metrics.panicIndex * 100).toFixed(0)}%
                                    </span>
                                </div>
                            </div>
                            <div className={`p-3 rounded-lg border ${
                              isDarkMode 
                                ? 'bg-zinc-950 border-zinc-800' 
                                : 'bg-white border-zinc-200'
                            }`}>
                                <div className={`text-xs mb-1 ${
                                  isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                                }`}>Disposition Ratio</div>
                                <div className="flex items-center justify-between">
                                    <span className={isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}>Your Average: {data.personalBaseline.avgDispositionRatio.toFixed(1)}x</span>
                                    <span className={`text-sm font-mono ${metrics.dispositionRatio > data.personalBaseline.avgDispositionRatio ? 'text-red-400' : 'text-emerald-400'}`}>
                                        Current: {metrics.dispositionRatio.toFixed(1)}x
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Behavior Shift Detection */}
                {data.behaviorShift && data.behaviorShift.length > 0 && (
                    <div className={`rounded-xl p-6 border ${
                      isDarkMode 
                        ? 'bg-zinc-900 border-zinc-800' 
                        : 'bg-zinc-50 border-zinc-200'
                    }`}>
                        <div className="flex items-center gap-2 mb-6">
                            <RefreshCcw className={`w-5 h-5 ${isDarkMode ? 'text-purple-500' : 'text-purple-600'}`} />
                            <h3 className={`text-sm font-bold uppercase tracking-wider ${
                              isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                            }`}>Behavior Shift (Recent 3 vs Baseline)</h3>
                        </div>
                        <div className="space-y-3">
                            {data.behaviorShift.map((shift, idx) => (
                                <div key={idx} className={`p-4 rounded-lg border ${
                                  shift.trend === 'IMPROVING' ? (isDarkMode ? 'bg-emerald-950/20 border-emerald-900/30' : 'bg-emerald-50 border-emerald-200') :
                                  shift.trend === 'WORSENING' ? (isDarkMode ? 'bg-red-950/20 border-red-900/30' : 'bg-red-50 border-red-200') :
                                  (isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200')
                                }`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className={`text-sm font-medium ${
                                          isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                                        }`}>{shift.bias}</span>
                                        {shift.trend === 'IMPROVING' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                                        {shift.trend === 'WORSENING' && <XCircle className="w-4 h-4 text-red-400" />}
                                        {shift.trend === 'STABLE' && <AlertCircle className={`w-4 h-4 ${isDarkMode ? 'text-zinc-500' : 'text-zinc-600'}`} />}
                                    </div>
                                    <div className={`text-xs ${
                                      isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
                                    }`}>
                                        {shift.trend === 'IMPROVING' ? '↓' : shift.trend === 'WORSENING' ? '↑' : '→'} 
                                        {' '}{Math.abs(shift.changePercent).toFixed(1)}% 
                                        {' '}({shift.trend === 'IMPROVING' ? '개선' : shift.trend === 'WORSENING' ? '악화' : '안정'})
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        )}

        {/* PATTERN RECOGNITION (과정 평가) */}
        {data.patterns && data.patterns.length > 0 && (
            <div className={`rounded-xl p-6 border ${
              isDarkMode 
                ? 'bg-purple-950/20 border-purple-900/30' 
                : 'bg-purple-50 border-purple-200'
            }`}>
                <div className="flex items-center gap-2 mb-6">
                    <BarChart2 className={`w-5 h-5 ${isDarkMode ? 'text-purple-400' : 'text-purple-600'}`} />
                    <h3 className={`text-sm font-bold uppercase tracking-wider ${
                      isDarkMode ? 'text-purple-300' : 'text-purple-900'
                    }`}>Pattern Recognition (반복되는 패턴 - 과정 평가)</h3>
                </div>
                <div className={`mb-4 p-3 rounded-lg border ${
                  isDarkMode 
                    ? 'bg-purple-950/30 border-purple-900/40' 
                    : 'bg-white border-purple-200'
                }`}>
                    <p className={`text-xs leading-relaxed ${
                      isDarkMode ? 'text-purple-200/80' : 'text-purple-800'
                    }`}>
                        <strong>💡 중요:</strong> 단일 거래의 결과가 아니라 <strong>반복되는 패턴</strong>에 집중합니다. 
                        "한두 번은 운 탓일 수 있지만, 10번 반복되면 실력(편향)입니다."
                    </p>
                </div>
                <div className="space-y-3">
                    {data.patterns.map((pattern, idx) => (
                        <div key={idx} className={`p-4 rounded-lg border ${
                          pattern.significance === 'HIGH' 
                            ? (isDarkMode ? 'bg-red-950/20 border-red-900/30' : 'bg-red-50 border-red-200')
                            : pattern.significance === 'MEDIUM'
                            ? (isDarkMode ? 'bg-orange-950/20 border-orange-900/30' : 'bg-orange-50 border-orange-200')
                            : (isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200')
                        }`}>
                            <div className="flex items-start justify-between mb-2">
                                <span className={`text-sm font-semibold ${
                                  isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                                }`}>
                                    {pattern.description}
                                </span>
                                <span className={`text-xs px-2 py-1 rounded-full ${
                                  pattern.significance === 'HIGH'
                                    ? (isDarkMode ? 'bg-red-900/40 text-red-300 border border-red-800' : 'bg-red-100 text-red-700 border border-red-300')
                                    : pattern.significance === 'MEDIUM'
                                    ? (isDarkMode ? 'bg-orange-900/40 text-orange-300 border border-orange-800' : 'bg-orange-100 text-orange-700 border border-orange-300')
                                    : (isDarkMode ? 'bg-zinc-800 text-zinc-400 border border-zinc-700' : 'bg-zinc-100 text-zinc-600 border border-zinc-300')
                                }`}>
                                    {pattern.significance}
                                </span>
                            </div>
                            <div className={`text-xs ${
                              isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
                            }`}>
                                발생률: {pattern.percentage.toFixed(0)}% ({pattern.count}/{pattern.total}건)
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )}

        {/* PERFECT EDITION: BIAS LOSS MAPPING & PRIORITY */}
        {(data.biasLossMapping || data.biasPriority) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Bias Loss Mapping */}
                {data.biasLossMapping && (
                    <div className={`rounded-xl p-6 border ${
                      isDarkMode 
                        ? 'bg-zinc-900 border-zinc-800' 
                        : 'bg-zinc-50 border-zinc-200'
                    }`}>
                        <div className="flex items-center gap-2 mb-6">
                            <DollarSign className={`w-5 h-5 ${isDarkMode ? 'text-red-500' : 'text-red-600'}`} />
                            <h3 className={`text-sm font-bold uppercase tracking-wider ${
                              isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                            }`}>Bias Loss Mapping</h3>
                        </div>
                        <div className="space-y-3">
                            {data.biasLossMapping.fomoLoss > 0 && (
                                <div className={`p-3 rounded-lg border ${
                                  isDarkMode 
                                    ? 'bg-zinc-950 border-zinc-800' 
                                    : 'bg-white border-zinc-200'
                                }`}>
                                    <div className="flex items-center justify-between">
                                        <span className={`text-sm ${
                                          isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
                                        }`}>FOMO Loss</span>
                                        <span className="text-red-400 font-mono font-bold">-${data.biasLossMapping.fomoLoss.toFixed(0)}</span>
                                    </div>
                                </div>
                            )}
                            {data.biasLossMapping.panicLoss > 0 && (
                                <div className={`p-3 rounded-lg border ${
                                  isDarkMode 
                                    ? 'bg-zinc-950 border-zinc-800' 
                                    : 'bg-white border-zinc-200'
                                }`}>
                                    <div className="flex items-center justify-between">
                                        <span className={`text-sm ${
                                          isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
                                        }`}>Panic Sell Loss</span>
                                        <span className="text-red-400 font-mono font-bold">-${data.biasLossMapping.panicLoss.toFixed(0)}</span>
                                    </div>
                                </div>
                            )}
                            {data.biasLossMapping.revengeLoss > 0 && (
                                <div className={`p-3 rounded-lg border ${
                                  isDarkMode 
                                    ? 'bg-zinc-950 border-zinc-800' 
                                    : 'bg-white border-zinc-200'
                                }`}>
                                    <div className="flex items-center justify-between">
                                        <span className={`text-sm ${
                                          isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
                                        }`}>Revenge Trading Loss</span>
                                        <span className="text-red-400 font-mono font-bold">-${data.biasLossMapping.revengeLoss.toFixed(0)}</span>
                                    </div>
                                </div>
                            )}
                            {data.biasLossMapping.dispositionLoss > 0 && (
                                <div className={`p-3 rounded-lg border ${
                                  isDarkMode 
                                    ? 'bg-zinc-950 border-zinc-800' 
                                    : 'bg-white border-zinc-200'
                                }`}>
                                    <div className="flex items-center justify-between">
                                        <span className={`text-sm ${
                                          isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
                                        }`}>Disposition Effect (Missed)</span>
                                        <span className="text-orange-400 font-mono font-bold">-${data.biasLossMapping.dispositionLoss.toFixed(0)}</span>
                                    </div>
                                </div>
                            )}
                            {data.biasLossMapping.fomoLoss === 0 && data.biasLossMapping.panicLoss === 0 && 
                             data.biasLossMapping.revengeLoss === 0 && data.biasLossMapping.dispositionLoss === 0 && (
                                <div className={`text-xs text-center py-4 ${
                                  isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                                }`}>No significant bias losses detected</div>
                            )}
                        </div>
                    </div>
                )}

                {/* Bias Priority */}
                {data.biasPriority && data.biasPriority.length > 0 && (
                    <div className={`rounded-xl p-6 border ${
                      isDarkMode 
                        ? 'bg-zinc-900 border-zinc-800' 
                        : 'bg-zinc-50 border-zinc-200'
                    }`}>
                        <div className="flex items-center gap-2 mb-6">
                            <Award className={`w-5 h-5 ${isDarkMode ? 'text-yellow-500' : 'text-yellow-600'}`} />
                            <h3 className={`text-sm font-bold uppercase tracking-wider ${
                              isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                            }`}>Fix Priority</h3>
                        </div>
                        <div className="space-y-3">
                            {data.biasPriority.map((priority) => (
                                <div key={priority.bias} className={`p-4 rounded-lg border ${
                                  isDarkMode 
                                    ? 'bg-zinc-950 border-zinc-800' 
                                    : 'bg-white border-zinc-200'
                                }`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            <span className="w-6 h-6 rounded-full bg-red-500/20 text-red-400 text-xs font-bold flex items-center justify-center">
                                                {priority.priority}
                                            </span>
                                            <span className={`text-sm font-medium ${
                                              isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                                            }`}>{priority.bias}</span>
                                        </div>
                                        <span className="text-red-400 font-mono font-bold text-sm">
                                            -${priority.financialLoss.toFixed(0)}
                                        </span>
                                    </div>
                                    <div className={`text-xs mt-2 ${
                                      isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                                    }`}>
                                        Frequency: {(priority.frequency * 100).toFixed(0)}% | 
                                        Severity: {(priority.severity * 100).toFixed(0)}%
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        )}

        {/* EQUITY CURVE & WHAT-IF SIMULATOR */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Equity Curve Chart */}
            {data.equityCurve && data.equityCurve.length > 0 && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <TrendingUp className="w-4 h-4 text-emerald-500" />
                        <h3 className="text-zinc-200 text-sm font-bold uppercase tracking-wider">Equity Curve (누적 수익 곡선)</h3>
                    </div>
                    <div className="mb-4 flex flex-wrap gap-3 text-xs text-zinc-400">
                        <div className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-red-500"></span>
                            <span>💀 FOMO (80%+)</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                            <span>😱 Panic (&lt;20%)</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-red-600"></span>
                            <span>⚔️ Revenge</span>
                        </div>
                    </div>
                    <EquityCurveChart equityCurve={data.equityCurve} />
                </div>
            )}

            {/* What-If Simulator */}
            {data.biasLossMapping && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-zinc-200 text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-purple-500" />
                            What-If Simulator: 편향 제거 시뮬레이션
                        </h3>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={showBiasFreeSimulation}
                                onChange={(e) => setShowBiasFreeSimulation(e.target.checked)}
                                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-purple-500 focus:ring-purple-500"
                            />
                            <span className="text-xs text-zinc-400">편향 제거 모드</span>
                        </label>
                    </div>
                    
                    {biasFreeMetrics && (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 bg-zinc-950 rounded-lg border border-zinc-800">
                                    <div className="text-xs text-zinc-500 mb-2">현재 총 PnL</div>
                                    <div className={`text-2xl font-mono font-bold ${biasFreeMetrics.currentPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                        ${biasFreeMetrics.currentPnL.toFixed(0)}
                                    </div>
                                </div>
                                
                                <div className={`p-4 rounded-lg border ${showBiasFreeSimulation ? 'bg-purple-950/30 border-purple-900/30' : 'bg-zinc-950 border-zinc-800'}`}>
                                    <div className={`text-xs mb-2 ${showBiasFreeSimulation ? 'text-purple-400' : 'text-zinc-500'}`}>
                                        {showBiasFreeSimulation ? '보정된 PnL (편향 제거)' : '잠재적 PnL'}
                                    </div>
                                    <div className={`text-2xl font-mono font-bold ${biasFreeMetrics.potentialPnL >= 0 ? 'text-purple-400' : 'text-red-400'}`}>
                                        ${biasFreeMetrics.potentialPnL.toFixed(0)}
                                    </div>
                                </div>
                            </div>
                            
                            <div className="p-4 bg-orange-950/20 rounded-lg border border-orange-900/30">
                                <div className="text-sm text-zinc-300 mb-2">
                                    💡 편향 비용: <span className="text-red-400 font-bold">-${biasFreeMetrics.biasLoss.toFixed(0)}</span>
                                </div>
                                <div className="text-xs text-zinc-500">
                                    이는 약 <span className="text-orange-400 font-semibold">{biasFreeMetrics.equivalentItems.toFixed(1)}대의 {biasFreeMetrics.itemName}</span> 가격과 같습니다.
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>

        {/* LEVEL 4: DEEP DIVE (COLLAPSIBLE) */}
        <div className="flex flex-col items-center pt-8 pb-20">
            <button 
                onClick={() => setShowDeepDive(!showDeepDive)}
                className="group flex items-center gap-3 px-6 py-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-full transition-all text-sm text-zinc-400 hover:text-zinc-200"
            >
                {showDeepDive ? 'Collapse Data' : 'Inspect Execution Quality'}
                {showDeepDive ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />}
            </button>

            {showDeepDive && (
                <div className="w-full mt-8 space-y-8 animate-in fade-in slide-in-from-top-4 duration-300">
                    
                    {/* EVIDENCE INSPECTOR - 체크리스트 UI로 개선 */}
                    <div className={`rounded-xl p-6 border ${
                      isDarkMode 
                        ? 'bg-zinc-950 border-zinc-800' 
                        : 'bg-zinc-100 border-zinc-300'
                    }`}>
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <Database className={`w-4 h-4 ${isDarkMode ? 'text-purple-400' : 'text-purple-600'}`} />
                                <h3 className={`font-medium text-sm ${
                                  isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                                }`}>AI가 분석한 핵심 근거</h3>
                            </div>
                            <span className={`text-xs uppercase px-2 py-1 rounded ${
                              isDarkMode 
                                ? 'text-emerald-500 bg-emerald-950/30 border border-emerald-900/30' 
                                : 'text-emerald-600 bg-emerald-50 border border-emerald-200'
                            }`}>AI 전달됨</span>
                        </div>
                        <div className="space-y-3 mb-4">
                            {evidenceItems.map((item, idx) => (
                                <div key={idx} className={`p-4 rounded-lg border flex items-start justify-between gap-4 ${
                                  item.status === 'warning' 
                                    ? (isDarkMode 
                                        ? 'bg-orange-950/20 border-orange-900/30' 
                                        : 'bg-orange-50 border-orange-200')
                                    : item.status === 'info'
                                    ? (isDarkMode 
                                        ? 'bg-blue-950/20 border-blue-900/30' 
                                        : 'bg-blue-50 border-blue-200')
                                    : (isDarkMode 
                                        ? 'bg-zinc-900/50 border-zinc-800' 
                                        : 'bg-white border-zinc-200')
                                }`}>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <CheckCircle2 className={`w-4 h-4 ${
                                              item.aiTransmitted 
                                                ? (isDarkMode ? 'text-emerald-400' : 'text-emerald-600')
                                                : (isDarkMode ? 'text-zinc-600' : 'text-zinc-400')
                                            }`} />
                                            <span className={`font-semibold text-sm ${
                                              isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                                            }`}>{item.label}</span>
                                            {item.aiTransmitted && (
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                                  isDarkMode 
                                                    ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-800/50' 
                                                    : 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                                                }`}>AI 전달됨</span>
                                            )}
                                        </div>
                                        <div className={`text-xs mt-1 ${
                                          isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
                                        }`}>
                                            {item.description}
                                        </div>
                                        <div className={`text-[10px] mt-1 ${
                                          isDarkMode ? 'text-zinc-500' : 'text-zinc-500'
                                        }`}>
                                            Clinical threshold: {item.threshold}
                                        </div>
                                    </div>
                                    <div className={`text-lg font-mono font-bold ${
                                      item.status === 'warning'
                                        ? 'text-orange-400'
                                        : item.status === 'info'
                                        ? 'text-blue-400'
                                        : (isDarkMode ? 'text-zinc-300' : 'text-zinc-700')
                                    }`}>
                                        {item.value}
                                    </div>
                                </div>
                            ))}
                        </div>
                        <div className={`p-3 rounded-lg border ${
                          isDarkMode 
                            ? 'bg-purple-950/20 border-purple-900/30' 
                            : 'bg-purple-50 border-purple-200'
                        }`}>
                            <p className={`text-xs leading-relaxed ${
                              isDarkMode ? 'text-purple-200/80' : 'text-purple-800'
                            }`}>
                                <span className={`font-bold ${
                                  isDarkMode ? 'text-emerald-400' : 'text-emerald-600'
                                }`}>AI는 계산하지 않습니다.</span> 위의 수치들만 해석합니다. 
                                엔진이 결정적으로 계산한 메트릭(FOMO, Panic 등)을 AI가 읽어 행동을 진단합니다. 
                                이를 통해 수학적 사실에 대한 <span className={isDarkMode ? 'text-zinc-300' : 'text-zinc-800'}>Zero Hallucination</span>이 보장됩니다.
                            </p>
                        </div>
                    </div>

                    {/* RAG REFERENCES (심화 근거) */}
                    {aiAnalysis?.references && aiAnalysis.references.length > 0 && (
                        <div className={`rounded-xl p-6 border ${
                          isDarkMode 
                            ? 'bg-purple-950/20 border-purple-900/30' 
                            : 'bg-purple-50 border-purple-200'
                        }`}>
                            <div className="flex items-center gap-2 mb-4">
                                <BookOpen className={`w-4 h-4 ${isDarkMode ? 'text-purple-400' : 'text-purple-600'}`} />
                                <h3 className={`text-sm font-bold uppercase tracking-wider ${
                                  isDarkMode ? 'text-purple-300' : 'text-purple-900'
                                }`}>
                                    AI가 참고한 행동경제학/트레이딩 원칙 (심화)
                                </h3>
                            </div>
                            <div className={`text-xs mb-4 ${
                              isDarkMode ? 'text-purple-200/80' : 'text-purple-800'
                            }`}>
                                다음 원칙들은 Evidence 기반 진단을 <strong>설명하고 보완</strong>하기 위해 검색되었습니다. 
                                Evidence와 충돌 시 Evidence가 우선합니다.
                            </div>
                            <div className="space-y-4">
                                {aiAnalysis.references.map((ref, idx) => (
                                    <div key={idx} className={`p-4 rounded-lg border ${
                                      isDarkMode 
                                        ? 'bg-purple-950/10 border-purple-900/20' 
                                        : 'bg-white border-purple-200'
                                    }`}>
                                        <h4 className={`font-semibold mb-2 ${
                                          isDarkMode ? 'text-purple-200' : 'text-purple-900'
                                        }`}>{ref.title}</h4>
                                        <p className={`text-sm mb-3 ${
                                          isDarkMode ? 'text-purple-200/80' : 'text-purple-800'
                                        }`}>{ref.content}</p>
                                        <div className={`text-xs italic p-2 rounded ${
                                          isDarkMode 
                                            ? 'bg-purple-900/20 text-purple-300' 
                                            : 'bg-purple-100 text-purple-700'
                                        }`}>
                                            💡 {ref.action}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className={`rounded-xl overflow-hidden shadow-2xl border ${
                      isDarkMode 
                        ? 'bg-zinc-900 border-zinc-800' 
                        : 'bg-zinc-50 border-zinc-200'
                    }`}>
                    <div className={`px-6 py-4 border-b flex justify-between items-center ${
                      isDarkMode 
                        ? 'border-zinc-800 bg-zinc-950/30' 
                        : 'border-zinc-200 bg-zinc-100/50'
                    }`}>
                        <h3 className={`font-medium text-sm ${
                          isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
                        }`}>Trade Log (FIFO)</h3>
                        <span className={`text-xs uppercase ${
                          isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
                        }`}>Determinisitc Analysis</span>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left text-zinc-400">
                            <thead className="text-xs text-zinc-500 uppercase bg-zinc-950">
                                <tr>
                                    <th className="px-6 py-3 font-semibold">Ticker</th>
                                    <th className="px-6 py-3 font-semibold">Market Regime</th>
                                    <th className="px-6 py-3 font-semibold">Entry / Exit</th>
                                    <th className="px-6 py-3 text-right font-semibold">Realized PnL</th>
                                    <th className="px-6 py-3 text-center font-semibold">FOMO (Entry) / 소명</th>
                                    <th className="px-6 py-3 text-center font-semibold">Panic (Exit)</th>
                                    <th className="px-6 py-3 text-right font-semibold text-orange-400/80">Regret ($)</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-zinc-800/50">
                                {trades.map((trade) => (
                                    <tr key={trade.id} className="hover:bg-zinc-800/20 transition-colors">
                                        <td className="px-6 py-4 font-medium text-zinc-200">
                                            <div className="flex items-center gap-2">
                                                {trade.ticker}
                                                {trade.isRevenge && (
                                                    <span className="px-1.5 py-0.5 bg-red-500/10 text-red-500 text-[9px] font-bold rounded uppercase border border-red-500/20">
                                                        REVENGE
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold border ${
                                                trade.marketRegime === 'BULL' ? (isDarkMode ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-emerald-100 text-emerald-700 border-emerald-300') : 
                                                trade.marketRegime === 'BEAR' ? (isDarkMode ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-red-100 text-red-700 border-red-300') : 
                                                (isDarkMode ? 'bg-zinc-800/50 text-zinc-500 border-zinc-700' : 'bg-zinc-200 text-zinc-600 border-zinc-300')
                                            }`}>
                                                {trade.marketRegime}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col text-xs font-mono">
                                                <span className={isDarkMode ? 'text-emerald-500/80' : 'text-emerald-600'}>BUY : {trade.entryDate} @ {trade.entryPrice}</span>
                                                <span className={isDarkMode ? 'text-red-500/80' : 'text-red-600'}>SELL: {trade.exitDate} @ {trade.exitPrice}</span>
                                            </div>
                                        </td>
                                        <td className={`px-6 py-4 text-right font-mono font-medium ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                            ${trade.pnl.toFixed(0)}
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            {trade.fomoScore === -1 ? (
                                                <span className={`text-xs ${isDarkMode ? 'text-zinc-700' : 'text-zinc-400'}`}>-</span>
                                            ) : (
                                                <div className="flex flex-col items-center gap-2">
                                                    <span className={`text-xs font-mono ${(trade.fomoScore > 0.8) ? 'text-red-400 font-bold' : (isDarkMode ? 'text-zinc-400' : 'text-zinc-600')}`}>
                                                        {(trade.fomoScore * 100).toFixed(0)}%
                                                    </span>
                                                    {/* Strategy Tag Badge */}
                                                    {trade.strategyTag && (
                                                        <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
                                                            trade.strategyTag === 'BREAKOUT' || trade.strategyTag === 'AGGRESSIVE_ENTRY'
                                                                ? (isDarkMode ? 'bg-blue-950/50 text-blue-400 border-blue-900/50' : 'bg-blue-100 text-blue-700 border-blue-300')
                                                                : (isDarkMode ? 'bg-red-950/50 text-red-400 border-red-900/50' : 'bg-red-100 text-red-700 border-red-300')
                                                        }`}>
                                                            {trade.strategyTag === 'BREAKOUT' ? '돌파' : 
                                                             trade.strategyTag === 'AGGRESSIVE_ENTRY' ? '공격적 진입' : 'FOMO'}
                                                        </span>
                                                    )}
                                                    {/* 소명하기 버튼 (FOMO > 0.7이고 아직 소명 안 했을 때) */}
                                                    {trade.fomoScore > 0.7 && !trade.userAcknowledged && (
                                                        <button
                                                            onClick={() => openStrategyModal(trade)}
                                                            className={`px-2 py-1 text-[10px] font-medium rounded transition-colors flex items-center gap-1 ${
                                                                isDarkMode
                                                                    ? 'bg-orange-950/50 text-orange-400 border border-orange-900/50 hover:bg-orange-900/50'
                                                                    : 'bg-orange-50 text-orange-600 border border-orange-200 hover:bg-orange-100'
                                                            }`}
                                                        >
                                                            <MessageSquare className="w-3 h-3" />
                                                            소명하기
                                                        </button>
                                                    )}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            {trade.panicScore === -1 ? (
                                                 <span className={`text-xs ${isDarkMode ? 'text-zinc-700' : 'text-zinc-400'}`}>-</span>
                                            ) : (
                                                <span className={`text-xs font-mono ${(trade.panicScore < 0.2) ? 'text-red-400 font-bold' : (isDarkMode ? 'text-zinc-400' : 'text-zinc-600')}`}>
                                                    {(trade.panicScore * 100).toFixed(0)}%
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-orange-400/80">
                                            {trade.regret > 0 ? `$${trade.regret.toFixed(0)}` : <span className={isDarkMode ? 'text-zinc-800' : 'text-zinc-300'}>-</span>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
              </div>
            )}
        </div>
      </div>
      
      {/* Strategy Tag Modal */}
      {selectedTrade && (
        <StrategyTagModal
          trade={selectedTrade}
          isOpen={showStrategyModal}
          onClose={() => {
            setShowStrategyModal(false);
            setSelectedTrade(null);
          }}
          onConfirm={(tag) => handleStrategyTag(selectedTrade, tag)}
          isDarkMode={isDarkMode}
        />
      )}
    </div>
  );
};
