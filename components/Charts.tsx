
import React from 'react';
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

export const EquityCurveChart: React.FC<{ equityCurve: EquityCurvePoint[] }> = ({ equityCurve }) => {
  if (!equityCurve || equityCurve.length === 0) {
    return (
      <div className="h-[300px] w-full flex items-center justify-center text-zinc-500">
        No equity curve data available
      </div>
    );
  }

  // 차트 데이터 준비 (날짜를 인덱스로 변환)
  const chartData = equityCurve.map((point, idx) => ({
    index: idx,
    date: point.date,
    cumulativePnl: point.cumulative_pnl,
    pnl: point.pnl,
    fomoScore: point.fomo_score,
    panicScore: point.panic_score,
    isRevenge: point.is_revenge,
    ticker: point.ticker,
    // FOMO 시점 강조를 위한 플래그
    isHighFomo: point.fomo_score !== null && point.fomo_score !== undefined && point.fomo_score > 0.7
  }));

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
          
          {/* 툴팁 */}
          <Tooltip
            contentStyle={{ 
              backgroundColor: '#09090b', 
              borderColor: '#27272a', 
              color: '#e4e4e7', 
              borderRadius: '8px',
              padding: '8px'
            }}
            formatter={(value: number, name: string, props: any) => {
              if (name === 'cumulativePnl') {
                return [`$${value.toFixed(0)}`, '누적 손익'];
              } else if (name === 'pnl') {
                return [`$${value.toFixed(0)}`, '거래 손익'];
              }
              return [value, name];
            }}
            labelFormatter={(label) => {
              const point = chartData[parseInt(label)];
              if (!point) return '';
              return `${point.ticker} - ${new Date(point.date).toLocaleDateString('ko-KR')}`;
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
          
          {/* FOMO 시점 마커 (빨간 점) */}
          <Scatter
            dataKey="cumulativePnl"
            fill="#ef4444"
            shape={(props: any) => {
              const { payload } = props;
              if (payload.isHighFomo) {
                return <circle cx={props.cx} cy={props.cy} r={4} fill="#ef4444" stroke="#fff" strokeWidth={1} />;
              }
              return null;
            }}
          />
          
          {/* Revenge Trading 마커 (주황 점) */}
          <Scatter
            dataKey="cumulativePnl"
            fill="#f59e0b"
            shape={(props: any) => {
              const { payload } = props;
              if (payload.isRevenge && !payload.isHighFomo) {
                return <circle cx={props.cx} cy={props.cy} r={3} fill="#f59e0b" stroke="#fff" strokeWidth={1} />;
              }
              return null;
            }}
          />
          
          {/* 0선 참조선 */}
          <ReferenceLine y={0} stroke="#71717a" strokeDasharray="2 2" />
        </ComposedChart>
      </ResponsiveContainer>
      
      {/* 범례 */}
      <div className="flex items-center justify-center gap-4 mt-2 text-xs text-zinc-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-500/30 border border-red-500/50 rounded"></div>
          <span>FOMO 시점 (고점 매수)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
          <span>Revenge Trading</span>
        </div>
      </div>
    </div>
  );
};
