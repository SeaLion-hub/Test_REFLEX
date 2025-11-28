
import React, { useState } from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ReferenceLine,
  LineChart,
  Line,
  ComposedChart,
  Scatter,
  ReferenceArea
} from 'recharts';
import { HelpCircle } from 'lucide-react';
import { AnalysisResult, EnrichedTrade, EquityCurvePoint } from '../types';

export const BehavioralRadar: React.FC<{ metrics: AnalysisResult['metrics'] }> = ({ metrics }) => {
  const data = [
    { subject: 'Discipline (FOMO)', A: Math.max(0, (1 - metrics.fomoIndex) * 100), fullMark: 100 },
    { subject: 'Nerves (Panic)', A: Math.max(0, (1 - metrics.panicIndex) * 100), fullMark: 100 },
    { subject: 'Patience', A: Math.min(100, Math.max(0, 200 - (metrics.dispositionRatio * 100))), fullMark: 100 },
    { subject: 'Resilience', A: Math.max(0, 100 - (metrics.revengeTradingCount * 25)), fullMark: 100 },
    { subject: 'Efficiency', A: Math.min(100, metrics.profitFactor * 33), fullMark: 100 },
    { subject: 'Win Rate', A: metrics.winRate * 100, fullMark: 100 },
  ];

  return (
    <div className="h-[250px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="#27272a" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#71717a', fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
          <Radar
            name="Behavior"
            dataKey="A"
            stroke="#10b981"
            strokeWidth={2}
            fill="#10b981"
            fillOpacity={0.2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export const classifyPersona = (data: Array<{ subject: string; value: number }>) => {
  const impulse = data.find(d => d.subject.includes('Impulse'))?.value || 0;
  const fear = data.find(d => d.subject.includes('Fear'))?.value || 0;
  const greed = data.find(d => d.subject.includes('Greed'))?.value || 0;
  const resilience = data.find(d => d.subject.includes('Resilience'))?.value || 0;
  
  if (impulse > 70 && fear > 60) return "유리멘탈 스캘퍼";
  if (greed > 70 && resilience < 40) return "FOMO 중독자";
  if (fear > 70 && resilience > 60) return "과도한 신중파";
  if (impulse < 30 && fear < 30 && greed < 50) return "균형잡힌 트레이더";
  if (greed > 60 && impulse > 50) return "추격 매수형";
  if (fear > 60 && resilience < 50) return "공포 주도형";
  
  return "일반 트레이더";
};

export const BiasDNARadar: React.FC<{ metrics: AnalysisResult['metrics'] }> = ({ metrics }) => {
  const [hoveredAxis, setHoveredAxis] = useState<string | null>(null);
  
  const data = [
    { subject: 'Impulse (충동)', value: Math.max(0, (1 - metrics.fomoIndex) * 100) },
    { subject: 'Fear (공포)', value: metrics.panicIndex * 100 },
    { subject: 'Greed (탐욕)', value: metrics.fomoIndex * 100 },
    { subject: 'Resilience (회복력)', value: Math.max(0, 100 - (metrics.revengeTradingCount * 25)) },
    { subject: 'Discipline (절제)', value: Math.min(100, Math.max(0, (1 - 0.3*metrics.dispositionRatio) * 50)) },
  ];

  const persona = classifyPersona(data);

  const axisExplanations: Record<string, string> = {
    'Impulse (충동)': `(1 - FOMO Index) × 100. 낮을수록 충동적 매수 경향이 큽니다.`,
    'Fear (공포)': `Panic Index × 100. 높을수록 공포 매도 경향이 큽니다.`,
    'Greed (탐욕)': `FOMO Index × 100. 높을수록 탐욕적 매수 경향이 큽니다.`,
    'Resilience (회복력)': `100 - (Revenge Trading Count × 25). 낮을수록 손실 후 즉시 재진입하는 경향이 큽니다.`,
    'Discipline (절제)': `(1 - Disposition Ratio) × 50. 낮을수록 손실 종목을 오래 보유하는 경향이 큽니다.`,
  };

  return (
    <div className="w-full">
      <div className="mb-4">
        <h3 className="text-lg font-bold mb-2 text-zinc-200">Bias DNA Signature</h3>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <p className="text-emerald-400 font-semibold text-center">
            당신은 <span className="text-2xl">{persona}</span> 유형입니다
          </p>
        </div>
      </div>
      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data.map(d => ({ ...d, A: d.value, fullMark: 100 }))}>
            <PolarGrid stroke="#27272a" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: '#71717a', fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
            <Radar
              name="Bias DNA"
              dataKey="A"
              stroke="#10b981"
              strokeWidth={2}
              fill="#10b981"
              fillOpacity={0.2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      {/* 축 설명 */}
      <div className="mt-4 space-y-2">
        {data.map((item) => (
          <div
            key={item.subject}
            className="flex items-center gap-2 text-xs text-zinc-400"
            onMouseEnter={() => setHoveredAxis(item.subject)}
            onMouseLeave={() => setHoveredAxis(null)}
          >
            <HelpCircle className="w-3 h-3 text-zinc-500" />
            <span className="font-medium">{item.subject}:</span>
            <span className="text-zinc-500">
              {hoveredAxis === item.subject ? axisExplanations[item.subject] : `${item.value.toFixed(0)}%`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export const RegretChart: React.FC<{ trades: EnrichedTrade[] }> = ({ trades }) => {
  const data = trades
    .map(t => ({
      ticker: t.ticker,
      regret: t.regret,
      realized: t.pnl,
      // We want to stack Realized + Regret to show "Total Potential"
      // Regret is always positive (missed profit). Realized can be negative.
    }))
    .sort((a, b) => b.regret - a.regret)
    .slice(0, 5);

  return (
    <div className="h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 5 }} barSize={20}>
          <XAxis type="number" stroke="#3f3f46" fontSize={10} tickFormatter={(val) => `$${val}`} hide />
          <YAxis dataKey="ticker" type="category" stroke="#a1a1aa" width={50} fontSize={12} fontWeight={500} tickLine={false} axisLine={false} />
          <Tooltip 
            cursor={{fill: '#18181b'}}
            contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', color: '#e4e4e7', borderRadius: '8px' }}
            formatter={(value: number, name: string) => [`$${value.toFixed(0)}`, name === 'realized' ? 'Banked Profit' : 'Missed (Ghost Money)']}
          />
          {/* Realized PnL (Solid) */}
          <Bar dataKey="realized" stackId="a" name="realized" radius={[4, 0, 0, 4]}>
             {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.realized >= 0 ? '#10b981' : '#ef4444'} />
              ))}
          </Bar>
          {/* Regret (Transparent/Dashed visual equivalent) */}
          <Bar dataKey="regret" stackId="a" name="regret" fill="#f59e0b" fillOpacity={0.15} stroke="#f59e0b" strokeWidth={1} strokeDasharray="2 2" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

interface EquityCurveChartProps {
  equityCurve: EquityCurvePoint[];
  biasFreeMetrics?: { improvement: number } | null;
  showBiasFree?: boolean;
  onTradeClick?: (tradeId: string) => void;  // 2A: 차트 마커 클릭 인터랙션
  demoMode?: boolean;  // 2A: 데모 모드 필터 해제
}

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({ 
  equityCurve, 
  biasFreeMetrics,
  showBiasFree = false,
  onTradeClick,
  demoMode = false
}) => {
  if (!equityCurve || equityCurve.length === 0) {
    return (
      <div className="h-[300px] w-full flex items-center justify-center text-zinc-500">
        No equity curve data available
      </div>
    );
  }

  // 차트 데이터 준비 (날짜를 인덱스로 변환)
  // 2A: 데모 모드일 때는 필터 없이 모든 거래 표시
  const chartData = equityCurve.map((point, idx) => ({
    index: idx,
    date: point.date,
    cumulativePnl: point.cumulative_pnl,
    benchmarkPnl: point.benchmark_cumulative_pnl,
    pnl: point.pnl,
    fomoScore: point.fomo_score,
    panicScore: point.panic_score,
    isRevenge: point.is_revenge,
    ticker: point.ticker,
    tradeId: point.trade_id,
    baseScore: point.base_score,
    volumeWeight: point.volume_weight,
    regimeWeight: point.regime_weight,
    contextualScore: point.contextual_score,
    marketRegime: point.market_regime,
    // FOMO 시점 강조를 위한 플래그 (데모 모드에서는 필터 없음)
    isHighFomo: demoMode ? (point.fomo_score !== null && point.fomo_score !== undefined && point.fomo_score >= 0.7) : 
                          (point.fomo_score !== null && point.fomo_score !== undefined && point.fomo_score > 0.7),
    // Panic 시점 강조 (데모 모드에서는 필터 없음)
    isHighPanic: demoMode ? (point.panic_score !== null && point.panic_score !== undefined && point.panic_score <= 0.3) :
                           (point.panic_score !== null && point.panic_score !== undefined && point.panic_score < 0.3)
  }));

  // What-If 점선 데이터 생성
  const biasFreeData = showBiasFree && biasFreeMetrics 
    ? chartData.map(point => ({
        ...point,
        cumulativePnl: point.cumulativePnl + biasFreeMetrics.improvement
      }))
    : null;

  // FOMO 시점 찾기 (ReferenceArea용)
  const fomoAreas: Array<{ x1: number; x2: number }> = [];
  chartData.forEach((point, idx) => {
    if (point.isHighFomo) {
      // 이전 영역과 겹치지 않으면 새 영역 추가
      const lastArea = fomoAreas[fomoAreas.length - 1];
      if (!lastArea || lastArea.x2 < idx - 1) {
        fomoAreas.push({ x1: idx, x2: idx });
      } else {
        // 기존 영역 확장
        lastArea.x2 = idx;
      }
    }
  });

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          {/* FOMO 시점 배경 강조 */}
          {fomoAreas.map((area, idx) => (
            <ReferenceArea
              key={`fomo-${idx}`}
              x1={area.x1}
              x2={area.x2}
              fill="#ef4444"
              fillOpacity={0.15}
              stroke="#ef4444"
              strokeOpacity={0.3}
            />
          ))}
          
          {/* X축 (날짜) */}
          <XAxis
            dataKey="index"
            stroke="#71717a"
            fontSize={10}
            tickFormatter={(value) => {
              const point = chartData[value];
              return point ? new Date(point.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }) : '';
            }}
          />
          
          {/* Y축 (PnL) */}
          <YAxis
            stroke="#71717a"
            fontSize={10}
            tickFormatter={(val) => `$${val >= 1000 ? (val/1000).toFixed(1)+'k' : val.toFixed(0)}`}
          />
          
          {/* 커스텀 툴팁 (2A: volume_weight, regime_weight 표시 추가) */}
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload || !payload.length) return null;
              
              const point = chartData[parseInt(label as string)];
              if (!point) return null;
              
              const isFomo = point.isHighFomo;
              const isPanic = point.isHighPanic;
              const isRevenge = point.isRevenge;
              
              return (
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 shadow-xl max-w-xs">
                  <div className="text-xs font-semibold text-zinc-300 mb-2">
                    {point.ticker} - {new Date(point.date).toLocaleDateString('ko-KR')}
                  </div>
                  <div className="text-sm text-emerald-400 font-mono mb-2">
                    누적 손익: ${point.cumulativePnl.toFixed(0)}
                  </div>
                  {point.benchmarkPnl !== null && point.benchmarkPnl !== undefined && (
                    <div className="text-sm text-blue-400 font-mono mb-2">
                      SPY 누적 수익: ${point.benchmarkPnl.toFixed(0)}
                      <span className={`text-xs ml-2 ${point.cumulativePnl > point.benchmarkPnl ? 'text-emerald-400' : 'text-red-400'}`}>
                        ({point.cumulativePnl > point.benchmarkPnl ? '+' : ''}${(point.cumulativePnl - point.benchmarkPnl).toFixed(0)})
                      </span>
                    </div>
                  )}
                  <div className="text-xs text-zinc-400 mb-2">
                    거래 손익: ${point.pnl.toFixed(0)}
                  </div>
                  
                  {/* 2A: 분해 필드 표시 (있는 경우) */}
                  {point.baseScore !== null && point.baseScore !== undefined && (
                    <div className="text-xs text-purple-300 mt-2 p-2 bg-purple-950/30 rounded border border-purple-900/50">
                      <div className="font-semibold mb-1">Contextual Score 분해:</div>
                      <div>Base: {point.baseScore.toFixed(1)}</div>
                      <div>× Volume: {point.volumeWeight?.toFixed(1) || '1.0'}</div>
                      <div>× Regime: {point.regimeWeight?.toFixed(1) || '1.0'}</div>
                      <div className="mt-1 pt-1 border-t border-purple-900/50">
                        = {point.contextualScore?.toFixed(1) || 'N/A'}
                      </div>
                    </div>
                  )}
                  
                  {/* 2A: volume_weight, regime_weight 표시 (분해 필드가 없어도) */}
                  {point.volumeWeight !== null && point.volumeWeight !== undefined && (
                    <div className="text-xs text-blue-300 mt-1">
                      거래량 가중치: {point.volumeWeight.toFixed(1)}
                    </div>
                  )}
                  {point.regimeWeight !== null && point.regimeWeight !== undefined && (
                    <div className="text-xs text-blue-300">
                      시장 국면 가중치: {point.regimeWeight.toFixed(1)} ({point.marketRegime || 'UNKNOWN'})
                    </div>
                  )}
                  
                  {isFomo && (
                    <div className="text-xs text-red-400 mt-2 p-2 bg-red-950/30 rounded border border-red-900/50">
                      🔥 FOMO Zone: 고점 대비 {((point.fomoScore || 0) * 100).toFixed(0)}% 구간 진입
                      <br />
                      <span className="text-red-300/80">전형적인 뇌동매매 패턴입니다.</span>
                    </div>
                  )}
                  {isPanic && !isFomo && (
                    <div className="text-xs text-orange-400 mt-2 p-2 bg-orange-950/30 rounded border border-orange-900/50">
                      😱 Panic Sell: 저점 대비 {((point.panicScore || 0) * 100).toFixed(0)}% 구간 청산
                    </div>
                  )}
                  {isRevenge && !isFomo && !isPanic && (
                    <div className="text-xs text-orange-400 mt-2 p-2 bg-orange-950/30 rounded border border-orange-900/50">
                      ⚔️ Revenge Trading: 손실 후 24시간 내 재진입
                    </div>
                  )}
                  
                  {/* 2A: 클릭 가능 표시 */}
                  {onTradeClick && point.tradeId && (
                    <div className="text-xs text-zinc-500 mt-2 italic">
                      클릭하여 상세 정보 보기
                    </div>
                  )}
                </div>
              );
            }}
          />
          
          {/* 누적 손익 라인 */}
          <Line
            type="monotone"
            dataKey="cumulativePnl"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
            name="cumulativePnl"
          />
          
          {/* 벤치마크(SPY) 라인 */}
          {chartData.some(p => p.benchmarkPnl !== null && p.benchmarkPnl !== undefined) && (
            <Line
              type="monotone"
              dataKey="benchmarkPnl"
              stroke="#3b82f6"
              strokeWidth={2}
              strokeDasharray="3 3"
              dot={false}
              name="benchmarkPnl"
            />
          )}
          
          {/* What-If 점선 (토글 시 표시) */}
          {biasFreeData && (
            <Line
              type="monotone"
              dataKey="cumulativePnl"
              data={biasFreeData}
              stroke="#a855f7"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="biasFreePnl"
            />
          )}
          
          {/* FOMO 시점 마커 (빨간 점) - 2A: 클릭 가능 */}
          <Scatter
            dataKey="cumulativePnl"
            fill="#ef4444"
            shape={(props: any) => {
              const { payload } = props;
              if (payload.isHighFomo) {
                return (
                  <circle 
                    cx={props.cx} 
                    cy={props.cy} 
                    r={demoMode ? 6 : 4} 
                    fill="#ef4444" 
                    stroke="#fff" 
                    strokeWidth={demoMode ? 2 : 1}
                    style={{ cursor: onTradeClick ? 'pointer' : 'default' }}
                    onClick={() => {
                      if (onTradeClick && payload.tradeId) {
                        onTradeClick(payload.tradeId);
                      }
                    }}
                  />
                );
              }
              return null;
            }}
          />
          
          {/* Panic Sell 마커 (주황 점) - 2A: 클릭 가능 */}
          <Scatter
            dataKey="cumulativePnl"
            fill="#f59e0b"
            shape={(props: any) => {
              const { payload } = props;
              if (payload.isHighPanic && !payload.isHighFomo) {
                return (
                  <circle 
                    cx={props.cx} 
                    cy={props.cy} 
                    r={demoMode ? 5 : 3} 
                    fill="#f59e0b" 
                    stroke="#fff" 
                    strokeWidth={demoMode ? 2 : 1}
                    style={{ cursor: onTradeClick ? 'pointer' : 'default' }}
                    onClick={() => {
                      if (onTradeClick && payload.tradeId) {
                        onTradeClick(payload.tradeId);
                      }
                    }}
                  />
                );
              }
              return null;
            }}
          />
          
          {/* Revenge Trading 마커 (주황 점) - 2A: 클릭 가능 */}
          <Scatter
            dataKey="cumulativePnl"
            fill="#f59e0b"
            shape={(props: any) => {
              const { payload } = props;
              if (payload.isRevenge && !payload.isHighFomo && !payload.isHighPanic) {
                return (
                  <circle 
                    cx={props.cx} 
                    cy={props.cy} 
                    r={demoMode ? 5 : 3} 
                    fill="#f59e0b" 
                    stroke="#fff" 
                    strokeWidth={demoMode ? 2 : 1}
                    style={{ cursor: onTradeClick ? 'pointer' : 'default' }}
                    onClick={() => {
                      if (onTradeClick && payload.tradeId) {
                        onTradeClick(payload.tradeId);
                      }
                    }}
                  />
                );
              }
              return null;
            }}
          />
          
          {/* 0선 참조선 */}
          <ReferenceLine y={0} stroke="#71717a" strokeDasharray="2 2" />
        </ComposedChart>
      </ResponsiveContainer>
      
      {/* 범례 */}
      <div className="flex items-center justify-center gap-4 mt-2 text-xs text-zinc-500 flex-wrap">
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 bg-emerald-500"></div>
          <span>사용자 수익률</span>
        </div>
        {chartData.some(p => p.benchmarkPnl !== null && p.benchmarkPnl !== undefined) && (
          <div className="flex items-center gap-1">
            <div className="w-4 h-0.5 bg-blue-500 border-dashed border-t-2"></div>
            <span>SPY (벤치마크)</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-500/30 border border-red-500/50 rounded"></div>
          <span>FOMO 시점</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
          <span>Panic Sell</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
          <span>Revenge Trading</span>
        </div>
      </div>
    </div>
  );
};
