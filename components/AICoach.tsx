import React from 'react';
import { Brain, AlertTriangle, CheckCircle2, Zap, Award, TrendingUp, TrendingDown, Target, BookOpen } from 'lucide-react';
import { AIAnalysis } from '../types';

interface AICoachProps {
  analysis: AIAnalysis | null;
  loading: boolean;
}

export const AICoach: React.FC<AICoachProps> = ({ analysis, loading }) => {
  if (loading) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 animate-pulse space-y-4">
        <div className="h-6 bg-zinc-800 w-1/3 rounded"></div>
        <div className="space-y-2">
          <div className="h-4 bg-zinc-800 rounded w-full"></div>
          <div className="h-4 bg-zinc-800 rounded w-5/6"></div>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="bg-gradient-to-b from-zinc-900 to-zinc-950 border border-zinc-800 rounded-xl p-6 lg:p-8 space-y-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-purple-900/30 rounded-lg text-purple-400">
          <Brain className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-zinc-100">AI Interpretation</h2>
      </div>

      {/* 이달의 명장면 (Best Executions) */}
      {analysis.strengths && analysis.strengths.length > 0 && (
        <div className="bg-gradient-to-br from-emerald-950/20 to-emerald-900/10 border border-emerald-900/30 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Award className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">
              이달의 명장면 (Best Execution)
            </h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-1 lg:grid-cols-2">
            {analysis.strengths.map((strength, idx) => (
              <div
                key={idx}
                className="bg-emerald-950/30 border border-emerald-900/40 rounded-lg p-4 space-y-2"
              >
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-emerald-400" />
                  <span className="font-semibold text-emerald-300">{strength.ticker}</span>
                  <span className="text-xs px-2 py-0.5 bg-emerald-900/40 text-emerald-200 rounded-full">
                    {strength.execution}
                  </span>
                </div>
                <p className="text-sm text-emerald-100/90 leading-relaxed">
                  {strength.lesson}
                </p>
                <p className="text-xs text-emerald-200/70 italic">
                  💡 {strength.reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-2">Diagnosis</h3>
            <p className="text-lg text-zinc-200 leading-relaxed border-l-2 border-purple-500/50 pl-4">
              {analysis.diagnosis}
            </p>
          </div>
          
          <div>
             <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-2">Primary Bias</h3>
             <div className="flex items-center gap-2 text-red-400 bg-red-950/10 p-3 rounded-lg border border-red-900/20 w-fit">
                <AlertTriangle className="w-5 h-5" />
                <span className="font-semibold">{analysis.bias}</span>
             </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-emerald-950/10 border border-emerald-900/20 p-4 rounded-xl">
            <h3 className="text-sm font-medium text-emerald-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                The Rule
            </h3>
            <p className="text-xl font-serif italic text-emerald-100">
              "{analysis.rule}"
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-2">Priority Fix</h3>
            <div className="flex items-start gap-3">
                <div className="mt-1 p-1 bg-blue-900/30 rounded text-blue-400">
                    <Zap className="w-4 h-4" />
                </div>
                <p className="text-zinc-300">{analysis.fix}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Personal Playbook */}
      {analysis.playbook && analysis.playbook.rules.length > 0 && (
        <div className="bg-gradient-to-br from-blue-950/20 to-indigo-900/10 border border-blue-900/30 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-blue-400" />
            <h3 className="text-sm font-bold text-blue-400 uppercase tracking-wider">
              Personal Playbook (나만의 투자 원칙)
            </h3>
          </div>
          <div className="bg-blue-950/30 border border-blue-900/40 rounded-lg p-4 mb-3">
            <p className="text-xs text-blue-200/80 mb-2">
              AI가 당신의 거래 패턴을 분석하여 생성한 개인화된 투자 원칙입니다.
            </p>
            <p className="text-xs text-blue-300/60 italic">
              기반: {analysis.playbook.based_on.patterns}개 패턴, {analysis.playbook.based_on.biases.length > 0 ? analysis.playbook.based_on.biases.join(', ') : '일반'} 편향
            </p>
          </div>
          <ul className="space-y-2">
            {analysis.playbook.rules.map((rule, idx) => (
              <li key={idx} className="flex items-start gap-3 text-zinc-200">
                <span className="text-blue-400 mt-1 font-bold">•</span>
                <span className="flex-1 leading-relaxed">{rule}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
