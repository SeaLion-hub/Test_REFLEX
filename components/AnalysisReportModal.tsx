import React, { useState } from 'react';
import { X, HelpCircle, AlertCircle, CheckCircle2, TrendingDown, DollarSign } from 'lucide-react';
import { AnalysisResult } from '../types';
import { classifyPersona } from './Charts';

interface AnalysisReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: AnalysisResult;
  currency: 'USD' | 'KRW';
  exchangeRate: number;
  formatCurrency: (amount: number, currency: 'USD' | 'KRW', rate: number) => string;
}

interface EvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  evidence: {
    metric: string;
    value: string | number;
    threshold: string;
    formula?: string;
    description: string;
  };
  isDarkMode: boolean;
}

const EvidenceModal: React.FC<EvidenceModalProps> = ({ isOpen, onClose, title, evidence, isDarkMode }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className={`relative z-10 w-full max-w-md rounded-xl shadow-2xl border ${
        isDarkMode
          ? 'bg-zinc-900 border-zinc-800'
          : 'bg-white border-zinc-200'
      }`}>
        <div className={`flex items-center justify-between p-6 border-b ${
          isDarkMode ? 'border-zinc-800' : 'border-zinc-200'
        }`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              isDarkMode ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-600'
            }`}>
              <HelpCircle className="w-5 h-5" />
            </div>
            <h2 className={`text-lg font-bold ${
              isDarkMode ? 'text-zinc-100' : 'text-zinc-900'
            }`}>
              {title} - 근거 지표
            </h2>
          </div>
          <button
            onClick={onClose}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode
                ? 'hover:bg-zinc-800 text-zinc-400'
                : 'hover:bg-zinc-100 text-zinc-600'
            }`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <h3 className={`text-sm font-semibold mb-2 ${
              isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
            }`}>
              {evidence.metric}
            </h3>
            <div className={`text-2xl font-bold mb-2 ${
              isDarkMode ? 'text-emerald-400' : 'text-emerald-600'
            }`}>
              {evidence.value}
            </div>
            <p className={`text-sm leading-relaxed ${
              isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
            }`}>
              {evidence.description}
            </p>
          </div>

          {evidence.threshold && (
            <div className={`p-3 rounded-lg border ${
              isDarkMode
                ? 'bg-yellow-950/20 border-yellow-900/30'
                : 'bg-yellow-50 border-yellow-200'
            }`}>
              <h4 className={`text-xs font-bold uppercase tracking-wider mb-1 ${
                isDarkMode ? 'text-yellow-400' : 'text-yellow-700'
              }`}>
                임계값
              </h4>
              <p className={`text-sm ${
                isDarkMode ? 'text-yellow-200' : 'text-yellow-800'
              }`}>
                {evidence.threshold}
              </p>
            </div>
          )}

          {evidence.formula && (
            <div className={`p-3 rounded-lg border ${
              isDarkMode
                ? 'bg-blue-950/20 border-blue-900/30'
                : 'bg-blue-50 border-blue-200'
            }`}>
              <h4 className={`text-xs font-bold uppercase tracking-wider mb-1 ${
                isDarkMode ? 'text-blue-400' : 'text-blue-700'
              }`}>
                계산식
              </h4>
              <p className={`text-sm font-mono ${
                isDarkMode ? 'text-blue-200' : 'text-blue-800'
              }`}>
                {evidence.formula}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const AnalysisReportModal: React.FC<AnalysisReportModalProps> = ({
  isOpen,
  onClose,
  data,
  currency,
  exchangeRate,
  formatCurrency
}) => {
  const [selectedEvidence, setSelectedEvidence] = useState<{
    title: string;
    evidence: {
      metric: string;
      value: string | number;
      threshold: string;
      formula?: string;
      description: string;
    };
  } | null>(null);

  if (!isOpen) return null;

  // 페르소나 분류
  const biasDNARadarData = [
    { subject: 'Impulse (충동)', value: Math.max(0, (1 - data.metrics.fomoIndex) * 100) },
    { subject: 'Fear (공포)', value: data.metrics.panicIndex * 100 },
    { subject: 'Greed (탐욕)', value: data.metrics.fomoIndex * 100 },
    { subject: 'Resilience (회복력)', value: Math.max(0, 100 - (data.metrics.revengeTradingCount * 25)) },
    { subject: 'Discipline (절제)', value: Math.min(100, Math.max(0, (1 - data.metrics.dispositionRatio) * 50)) },
  ];
  const persona = classifyPersona(biasDNARadarData);

  // 핵심 증상 추출
  const primaryBias = data.biasPriority?.[0];
  const symptoms: Array<{
    title: string;
    description: string;
    evidence: {
      metric: string;
      value: string | number;
      threshold: string;
      formula?: string;
      description: string;
    };
  }> = [];

  if (primaryBias) {
    if (primaryBias.bias === 'FOMO') {
      symptoms.push({
        title: 'FOMO 패턴',
        description: `오후 2시 이후 급등주 추격 매수(FOMO)로 인한 손실이 전체 손실의 ${((data.biasLossMapping?.fomoLoss || 0) / Math.abs(data.trades.reduce((sum, t) => sum + (t.pnl < 0 ? t.pnl : 0), 0)) * 100).toFixed(0)}%를 차지합니다.`,
        evidence: {
          metric: 'FOMO Index',
          value: `${(data.metrics.fomoIndex * 100).toFixed(0)}%`,
          threshold: '>70% = FOMO',
          formula: '(매수가 - 당일 저가) / (당일 고가 - 당일 저가) × 100',
          description: '매수 시점이 당일 고가 대비 얼마나 높은 위치였는지를 나타내는 지표입니다. 70% 이상이면 임상적 FOMO로 판단됩니다.'
        }
      });
    } else if (primaryBias.bias === 'Panic Sell') {
      symptoms.push({
        title: 'Panic Sell 패턴',
        description: `공포 매도로 인한 손실이 전체 손실의 ${((data.biasLossMapping?.panicLoss || 0) / Math.abs(data.trades.reduce((sum, t) => sum + (t.pnl < 0 ? t.pnl : 0), 0)) * 100).toFixed(0)}%를 차지합니다.`,
        evidence: {
          metric: 'Panic Sell Score',
          value: `${(data.metrics.panicIndex * 100).toFixed(0)}%`,
          threshold: '<30% = Panic Sell',
          formula: '(매도가 - 당일 저가) / (당일 고가 - 당일 저가) × 100',
          description: '매도 시점이 당일 저가 대비 얼마나 낮은 위치였는지를 나타내는 지표입니다. 30% 미만이면 비효율적인 매도 타이밍으로 판단됩니다.'
        }
      });
    }
  }

  // 긴급 처방
  const prescriptions: string[] = [];
  if (data.metrics.fomoIndex > 0.7) {
    prescriptions.push('오후 2시 이후에는 매수 버튼을 비활성화하십시오. 당신의 뇌는 오후 시간대에 충동 조절 능력이 현저히 떨어집니다.');
  }
  if (data.metrics.revengeTradingCount > 0) {
    prescriptions.push('손실 직후 24시간 동안은 거래를 금지하십시오. Revenge Trading 패턴이 감지되었습니다.');
  }
  if (data.metrics.panicIndex < 0.3) {
    prescriptions.push('청산 전 10분 대기하십시오. 저점 매도(Panic)를 피하기 위한 시간입니다.');
  }

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        />
        <div className="relative z-10 w-full max-w-4xl rounded-2xl shadow-2xl border bg-zinc-900 border-zinc-800 overflow-hidden">
          {/* 헤더 */}
          <div className="flex items-center justify-between p-6 border-b border-zinc-800 bg-gradient-to-r from-red-950/30 to-orange-950/30">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-red-900/30 text-red-400">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-zinc-100">Analysis Report</h2>
                <p className="text-sm text-zinc-400">투자 건강 진단서</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg transition-colors hover:bg-zinc-800 text-zinc-400"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 본문 */}
          <div className="p-8 space-y-8 bg-zinc-950">
            {/* 진단서 카드 */}
            <div className="flex justify-center">
              <div className="w-full max-w-2xl bg-gradient-to-br from-zinc-900/95 to-zinc-950/95 rounded-xl p-8 flex flex-col justify-center items-center border border-zinc-800 shadow-lg">
                <div className="text-center space-y-4">
                  <div className="text-4xl mb-4">🏥</div>
                  <h3 className="text-3xl font-bold text-red-400 mb-2">진단명</h3>
                  <p className="text-4xl font-extrabold text-white mb-6">{persona}</p>
                  <div className="text-sm text-zinc-400">
                    당신의 투자 행동 패턴을 분석한 결과입니다
                  </div>
                </div>
              </div>
            </div>

            {/* 핵심 증상 */}
            {symptoms.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-zinc-200 flex items-center gap-2">
                  <TrendingDown className="w-5 h-5 text-red-400" />
                  핵심 증상
                </h3>
                <div className="space-y-3">
                  {symptoms.map((symptom, idx) => (
                    <div
                      key={idx}
                      className="bg-zinc-900 border border-zinc-800 rounded-lg p-4"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-semibold text-red-400">{symptom.title}</span>
                            <button
                              onClick={() => setSelectedEvidence({ title: symptom.title, evidence: symptom.evidence })}
                              className="p-1 rounded-full hover:bg-zinc-800 text-zinc-500 hover:text-blue-400 transition-colors"
                              title="근거 지표 보기"
                            >
                              <HelpCircle className="w-4 h-4" />
                            </button>
                          </div>
                          <p className="text-sm text-zinc-300 leading-relaxed">{symptom.description}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 긴급 처방 */}
            {prescriptions.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-zinc-200 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  긴급 처방
                </h3>
                <div className="space-y-2">
                  {prescriptions.map((prescription, idx) => (
                    <div
                      key={idx}
                      className="bg-emerald-950/20 border border-emerald-900/30 rounded-lg p-4"
                    >
                      <p className="text-sm text-emerald-200 leading-relaxed">
                        {prescription}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 금전적 피해 요약 */}
            {data.biasLossMapping && (
              <div className="bg-red-950/20 border border-red-900/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="w-5 h-5 text-red-400" />
                  <h4 className="text-sm font-semibold text-red-400">총 편향 손실</h4>
                </div>
                <p className="text-2xl font-bold text-red-400">
                  {formatCurrency(
                    (data.biasLossMapping.fomoLoss || 0) +
                    (data.biasLossMapping.panicLoss || 0) +
                    (data.biasLossMapping.revengeLoss || 0) +
                    (data.biasLossMapping.dispositionLoss || 0),
                    currency,
                    exchangeRate
                  )}
                </p>
                <p className="text-xs text-zinc-400 mt-2">
                  이 나쁜 습관만 막았어도, 최신 아이폰 1대를 더 살 수 있었습니다.
                </p>
              </div>
            )}
          </div>

          {/* 푸터 */}
          <div className="p-6 border-t border-zinc-800 bg-zinc-900 flex justify-end">
            <button
              onClick={onClose}
              className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg transition-colors"
            >
              확인
            </button>
          </div>
        </div>
      </div>

      {/* 근거 지표 모달 */}
      {selectedEvidence && (
        <EvidenceModal
          isOpen={!!selectedEvidence}
          onClose={() => setSelectedEvidence(null)}
          title={selectedEvidence.title}
          evidence={selectedEvidence.evidence}
          isDarkMode={true}
        />
      )}
    </>
  );
};

