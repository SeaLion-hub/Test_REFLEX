import React from 'react';
import { TrendingUp, ArrowRight, Brain, AlertTriangle, Target, DollarSign } from 'lucide-react';
import { AnalysisResult } from '../types';

interface SummaryViewProps {
  data: AnalysisResult;
  onDetailsClick: (section: string) => void;
}

export const SummaryView: React.FC<SummaryViewProps> = ({ data, onDetailsClick }) => {
  const { metrics, biasPriority, biasFreeMetrics, biasLossMapping } = data;

  // 1. 등급 산정 로직
  const getGrade = (score: number) => {
    if (score >= 90) return { grade: 'S', title: '기계적 트레이더', desc: '감정에 휘둘리지 않는 완벽한 매매', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' };
    if (score >= 80) return { grade: 'A', title: '냉철한 독수리', desc: '대부분 원칙을 지키며 수익을 냅니다', color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30' };
    if (score >= 70) return { grade: 'B', title: '눈치 빠른 여우', desc: '잘하지만 가끔 뇌동매매를 합니다', color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' };
    if (score >= 60) return { grade: 'C', title: '성격 급한 햄스터', desc: '조금만 흔들려도 사고팔고를 반복합니다', color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' };
    return { grade: 'F', title: '도파민 중독자', desc: '도박에 가까운 매매를 하고 있습니다', color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' };
  };

  const gradeInfo = getGrade(metrics.truthScore);

  // 2. 주된 편향 (Primary Bias)
  const primaryBias = biasPriority && biasPriority.length > 0 ? biasPriority[0] : null;

  // 3. 놓친 수익 (What-If)
  const missedMoney = biasFreeMetrics 
    ? biasFreeMetrics.biasLoss + (biasFreeMetrics.opportunityCost < 0 ? Math.abs(biasFreeMetrics.opportunityCost) : 0)
    : (biasLossMapping 
        ? (biasLossMapping.fomoLoss + biasLossMapping.panicLoss + biasLossMapping.revengeLoss + biasLossMapping.dispositionLoss)
        : 0);

  // 아이폰 가격 기준 (예: $1000)
  const iphoneCount = (missedMoney / 1000).toFixed(1);

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-200 flex flex-col items-center justify-center p-6 animate-in fade-in duration-700">
      
      <div className="text-center mb-12">
        <h1 className="text-3xl md:text-4xl font-bold text-white mb-3 tracking-tight">분석이 완료되었습니다</h1>
        <p className="text-zinc-400">당신의 투자 패턴을 3가지 핵심 키워드로 요약했습니다.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-6xl">

        {/* CARD 1: 투자 등급 */}
        <div 
          onClick={() => onDetailsClick('score-card')}
          className="group relative bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8 flex flex-col items-center text-center cursor-pointer hover:-translate-y-1 hover:border-zinc-600 transition-all duration-300 overflow-hidden"
        >
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-yellow-500 via-orange-500 to-red-500"></div>
          
          <div className="mb-6 relative">
            <div className={`w-24 h-24 rounded-full border-4 ${gradeInfo.border} ${gradeInfo.bg} flex items-center justify-center shadow-lg`}>
              <span className={`text-5xl font-black ${gradeInfo.color}`}>{gradeInfo.grade}</span>
            </div>
            <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 bg-zinc-800 border border-zinc-700 px-3 py-1 rounded-full text-xs text-zinc-300 font-mono whitespace-nowrap">
              Truth Score: {metrics.truthScore}
            </div>
          </div>

          <h3 className="text-xl font-bold text-white mb-2">{gradeInfo.title}</h3>
          <p className="text-sm text-zinc-400 mb-8 leading-relaxed">
            "{gradeInfo.desc}"
          </p>

          <div className="mt-auto w-full pt-4 border-t border-zinc-800">
            <span className="text-xs text-zinc-500 group-hover:text-yellow-400 transition-colors flex items-center justify-center gap-1 font-medium">
              상세 성적표 확인하기 <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* CARD 2: 핵심 문제 (Bias) */}
        <div 
          onClick={() => onDetailsClick('bias-analysis')}
          className="group relative bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8 flex flex-col items-center text-center cursor-pointer hover:-translate-y-1 hover:border-zinc-600 transition-all duration-300 overflow-hidden"
        >
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 via-pink-500 to-purple-500"></div>
          
          <div className="mb-6 relative">
            <div className="w-24 h-24 rounded-full border-4 border-red-500/30 bg-red-500/10 flex items-center justify-center">
              <AlertTriangle className="w-10 h-10 text-red-400" />
            </div>
            <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 bg-red-900/80 border border-red-800 px-3 py-1 rounded-full text-xs text-red-100 font-bold whitespace-nowrap">
              주의 요망
            </div>
          </div>

          <h3 className="text-xl font-bold text-white mb-2">
            {primaryBias ? primaryBias.bias : "특이 사항 없음"}
          </h3>
          <p className="text-sm text-zinc-400 mb-8 leading-relaxed">
            {primaryBias 
              ? `이 편향으로 인해 약 $${primaryBias.financialLoss.toFixed(0)}의 손실이 발생했습니다.`
              : "치명적인 행동 편향이 발견되지 않았습니다. 훌륭합니다!"}
          </p>

          <div className="mt-auto w-full pt-4 border-t border-zinc-800">
            <span className="text-xs text-zinc-500 group-hover:text-red-400 transition-colors flex items-center justify-center gap-1 font-medium">
              원인 분석 보기 <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* CARD 3: 기회 비용 (What-If) */}
        <div 
          onClick={() => onDetailsClick('simulator')}
          className="group relative bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8 flex flex-col items-center text-center cursor-pointer hover:-translate-y-1 hover:border-zinc-600 transition-all duration-300 overflow-hidden"
        >
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500"></div>
          
          <div className="mb-6 relative">
            <div className="w-24 h-24 rounded-full border-4 border-emerald-500/30 bg-emerald-500/10 flex items-center justify-center">
              <DollarSign className="w-10 h-10 text-emerald-400" />
            </div>
            <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 bg-emerald-900/80 border border-emerald-800 px-3 py-1 rounded-full text-xs text-emerald-100 font-bold animate-pulse whitespace-nowrap">
              +${missedMoney.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
          </div>

          <h3 className="text-xl font-bold text-white mb-2">숨겨진 수익 발견</h3>
          <p className="text-sm text-zinc-400 mb-8 leading-relaxed">
            나쁜 습관만 없었어도<br/>
            <strong className="text-emerald-400">최신 아이폰 {iphoneCount}대</strong>를 더 살 수 있었습니다.
          </p>

          <div className="mt-auto w-full pt-4 border-t border-zinc-800">
            <span className="text-xs text-zinc-500 group-hover:text-emerald-400 transition-colors flex items-center justify-center gap-1 font-medium">
              시뮬레이션 보기 <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

      </div>

      <button 
        onClick={() => onDetailsClick('top')}
        className="mt-12 px-8 py-4 bg-white text-black font-bold rounded-full hover:bg-zinc-200 transition-all flex items-center gap-2 shadow-lg hover:scale-105"
      >
        전체 상세 리포트 열기
        <TrendingUp className="w-5 h-5" />
      </button>

    </div>
  );
};