import React, { useState, useEffect } from 'react';
import { X, Scale, Loader2, CheckCircle2, XCircle, AlertCircle, Gavel } from 'lucide-react';
import { EnrichedTrade, NewsVerification } from '../types';

interface AIJudgeModalProps {
  trade: EnrichedTrade;
  isOpen: boolean;
  onClose: () => void;
  onAppeal: () => void; // 이의 제기 (소명하기 모달로 이동)
  isDarkMode: boolean;
}

export const AIJudgeModal: React.FC<AIJudgeModalProps> = ({
  trade,
  isOpen,
  onClose,
  onAppeal,
  isDarkMode
}) => {
  const [verification, setVerification] = useState<NewsVerification | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && !verification && !loading) {
      fetchNewsVerification();
    }
  }, [isOpen]);

  const fetchNewsVerification = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/verify-news', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker: trade.ticker,
          date: trade.entryDate,
          fomo_score: trade.fomoScore
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }

      const result = await response.json();
      setVerification(result as NewsVerification);
    } catch (err) {
      console.error('News verification error:', err);
      setError('뉴스 검증 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const getVerdictColor = (verdict: string) => {
    if (verdict === 'GUILTY') {
      return isDarkMode ? 'text-red-400' : 'text-red-600';
    } else if (verdict === 'INNOCENT') {
      return isDarkMode ? 'text-emerald-400' : 'text-emerald-600';
    } else {
      return isDarkMode ? 'text-yellow-400' : 'text-yellow-600';
    }
  };

  const getVerdictBg = (verdict: string) => {
    if (verdict === 'GUILTY') {
      return isDarkMode ? 'bg-red-950/30 border-red-900/50' : 'bg-red-50 border-red-200';
    } else if (verdict === 'INNOCENT') {
      return isDarkMode ? 'bg-emerald-950/30 border-emerald-900/50' : 'bg-emerald-50 border-emerald-200';
    } else {
      return isDarkMode ? 'bg-yellow-950/30 border-yellow-900/50' : 'bg-yellow-50 border-yellow-200';
    }
  };

  const getVerdictText = (verdict: string) => {
    if (verdict === 'GUILTY') return '유죄 (뇌동매매 확정)';
    if (verdict === 'INNOCENT') return '무죄 (전략적 진입)';
    return '보류 (증거 불충분)';
  };

  const getConfidenceText = (confidence: string) => {
    if (confidence === 'HIGH') return '높음';
    if (confidence === 'MEDIUM') return '보통';
    return '낮음';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className={`relative z-10 w-full max-w-2xl rounded-xl shadow-2xl border ${
        isDarkMode
          ? 'bg-zinc-900 border-zinc-800'
          : 'bg-white border-zinc-200'
      }`}>
        {/* Header */}
        <div className={`flex items-center justify-between p-6 border-b ${
          isDarkMode ? 'border-zinc-800' : 'border-zinc-200'
        }`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              isDarkMode ? 'bg-purple-900/30 text-purple-400' : 'bg-purple-100 text-purple-600'
            }`}>
              <Gavel className="w-6 h-6" />
            </div>
            <div>
              <h2 className={`text-xl font-bold ${
                isDarkMode ? 'text-zinc-100' : 'text-zinc-900'
              }`}>
                🏛️ AI 행동 재무학 재판소
              </h2>
              <p className={`text-xs mt-1 ${
                isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
              }`}>
                {trade.ticker} • {trade.entryDate}
              </p>
            </div>
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

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Trade Info */}
          <div className={`p-4 rounded-lg border ${
            isDarkMode
              ? 'bg-zinc-950 border-zinc-800'
              : 'bg-zinc-50 border-zinc-200'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <span className={`font-semibold ${
                isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
              }`}>
                거래 정보
              </span>
              <span className={`text-sm font-mono ${
                trade.fomoScore > 0.7
                  ? 'text-red-400'
                  : isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
              }`}>
                FOMO Score: {(trade.fomoScore * 100).toFixed(0)}%
              </span>
            </div>
            <div className={`text-xs font-mono ${
              isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
            }`}>
              진입: {trade.entryDate} @ ${trade.entryPrice.toFixed(2)}
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-purple-400 mb-4" />
              <p className={`text-sm ${
                isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
              }`}>
                AI 판사가 뉴스를 검토 중입니다...
              </p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className={`p-4 rounded-lg border ${
              isDarkMode
                ? 'bg-red-950/30 border-red-900/50'
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center gap-2">
                <AlertCircle className={`w-5 h-5 ${
                  isDarkMode ? 'text-red-400' : 'text-red-600'
                }`} />
                <p className={`text-sm ${
                  isDarkMode ? 'text-red-300' : 'text-red-700'
                }`}>
                  {error}
                </p>
              </div>
            </div>
          )}

          {/* Verdict */}
          {verification && !loading && (
            <>
              <div className={`p-6 rounded-lg border-2 ${getVerdictBg(verification.verdict)}`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    {verification.verdict === 'GUILTY' ? (
                      <XCircle className={`w-8 h-8 ${getVerdictColor(verification.verdict)}`} />
                    ) : verification.verdict === 'INNOCENT' ? (
                      <CheckCircle2 className={`w-8 h-8 ${getVerdictColor(verification.verdict)}`} />
                    ) : (
                      <AlertCircle className={`w-8 h-8 ${getVerdictColor(verification.verdict)}`} />
                    )}
                    <div>
                      <h3 className={`text-2xl font-bold ${getVerdictColor(verification.verdict)}`}>
                        {getVerdictText(verification.verdict)}
                      </h3>
                      <p className={`text-xs mt-1 ${
                        isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
                      }`}>
                        확신도: {getConfidenceText(verification.confidence)}
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Reasoning */}
                <div className={`mt-4 p-4 rounded-lg ${
                  isDarkMode ? 'bg-zinc-950/50' : 'bg-white/50'
                }`}>
                  <h4 className={`text-sm font-semibold mb-2 ${
                    isDarkMode ? 'text-zinc-300' : 'text-zinc-900'
                  }`}>
                    판결문
                  </h4>
                  <p className={`text-sm leading-relaxed ${
                    isDarkMode ? 'text-zinc-200' : 'text-zinc-800'
                  }`}>
                    {verification.reasoning}
                  </p>
                </div>
              </div>

              {/* News Evidence */}
              {verification.newsTitles && verification.newsTitles.length > 0 && (
                <div className={`p-4 rounded-lg border ${
                  isDarkMode
                    ? 'bg-zinc-950 border-zinc-800'
                    : 'bg-zinc-50 border-zinc-200'
                }`}>
                  <h4 className={`text-sm font-semibold mb-3 ${
                    isDarkMode ? 'text-zinc-300' : 'text-zinc-900'
                  }`}>
                    핵심 증거 (참조한 뉴스)
                  </h4>
                  <div className="space-y-2">
                    {verification.newsTitles.map((title, idx) => (
                      <div key={idx} className={`p-3 rounded border ${
                        isDarkMode
                          ? 'bg-zinc-900/50 border-zinc-800'
                          : 'bg-white border-zinc-200'
                      }`}>
                        <div className="flex items-start gap-2">
                          <span className={`text-xs font-mono ${
                            isDarkMode ? 'text-zinc-500' : 'text-zinc-400'
                          }`}>
                            {idx + 1}.
                          </span>
                          <p className={`text-sm flex-1 ${
                            isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
                          }`}>
                            {title}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {verification.source === 'cache' && (
                    <p className={`text-xs mt-3 ${
                      isDarkMode ? 'text-zinc-500' : 'text-zinc-500'
                    }`}>
                      * 시연용 캐시 데이터 사용
                    </p>
                  )}
                </div>
              )}
            </>
          )}

          {/* Actions */}
          {verification && !loading && (
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
              <button
                onClick={onClose}
                className={`px-4 py-2 rounded-lg border transition-colors ${
                  isDarkMode
                    ? 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'
                    : 'bg-zinc-100 border-zinc-300 text-zinc-700 hover:bg-zinc-200'
                }`}
              >
                결과 승복
              </button>
              {verification.verdict === 'GUILTY' && (
                <button
                  onClick={() => {
                    onClose();
                    onAppeal();
                  }}
                  className={`px-4 py-2 rounded-lg border transition-colors ${
                    isDarkMode
                      ? 'bg-orange-900/30 border-orange-800/50 text-orange-300 hover:bg-orange-900/50'
                      : 'bg-orange-50 border-orange-200 text-orange-700 hover:bg-orange-100'
                  }`}
                >
                  이의 제기 (소명하기)
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

