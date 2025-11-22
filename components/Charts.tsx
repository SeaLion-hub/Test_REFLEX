
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
  ReferenceLine
} from 'recharts';
import { AnalysisResult, EnrichedTrade } from '../types';

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
