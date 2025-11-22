import React from 'react';
import { X, AlertCircle, Target, Zap } from 'lucide-react';
import { EnrichedTrade } from '../types';

interface StrategyTagModalProps {
  trade: EnrichedTrade;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (tag: 'BREAKOUT' | 'AGGRESSIVE_ENTRY' | 'FOMO') => void;
  isDarkMode: boolean;
}

export const StrategyTagModal: React.FC<StrategyTagModalProps> = ({
  trade,
  isOpen,
  onClose,
  onConfirm,
  isDarkMode
}) => {
  if (!isOpen) return null;

  const handleSelect = (tag: 'BREAKOUT' | 'AGGRESSIVE_ENTRY' | 'FOMO') => {
    onConfirm(tag);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className={`relative z-10 w-full max-w-md rounded-xl shadow-2xl border ${
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
              isDarkMode ? 'bg-orange-900/30 text-orange-400' : 'bg-orange-100 text-orange-600'
            }`}>
              <AlertCircle className="w-5 h-5" />
            </div>
            <h2 className={`text-lg font-bold ${
              isDarkMode ? 'text-zinc-100' : 'text-zinc-900'
            }`}>
              거래 소명하기
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
                {trade.ticker}
              </span>
              <span className={`text-sm ${
                trade.fomoScore > 0.7
                  ? 'text-red-400'
                  : isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
              }`}>
                FOMO: {(trade.fomoScore * 100).toFixed(0)}%
              </span>
            </div>
            <div className={`text-xs font-mono ${
              isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
            }`}>
              {trade.entryDate} @ ${trade.entryPrice.toFixed(2)}
            </div>
          </div>

          {/* Question */}
          <div>
            <p className={`text-base mb-4 ${
              isDarkMode ? 'text-zinc-200' : 'text-zinc-900'
            }`}>
              이 거래는 전략적 진입이었나요?
            </p>
            <p className={`text-sm mb-6 ${
              isDarkMode ? 'text-zinc-400' : 'text-zinc-600'
            }`}>
              시스템이 FOMO로 오진단했을 수 있습니다. 실제 매매 의도를 알려주세요.
            </p>
          </div>

          {/* Options */}
          <div className="space-y-3">
            {/* Option 1: Breakout Strategy */}
            <button
              onClick={() => handleSelect('BREAKOUT')}
              className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                isDarkMode
                  ? 'bg-blue-950/30 border-blue-900/50 hover:border-blue-700 hover:bg-blue-950/50'
                  : 'bg-blue-50 border-blue-200 hover:border-blue-400 hover:bg-blue-100'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${
                  isDarkMode ? 'bg-blue-900/40 text-blue-400' : 'bg-blue-100 text-blue-600'
                }`}>
                  <Target className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className={`font-semibold mb-1 ${
                    isDarkMode ? 'text-blue-300' : 'text-blue-900'
                  }`}>
                    네, 돌파 매매(Breakout) 전략입니다
                  </div>
                  <div className={`text-xs ${
                    isDarkMode ? 'text-blue-200/70' : 'text-blue-700'
                  }`}>
                    의도적인 고가 진입으로 돌파를 노린 전략적 매매였습니다.
                    FOMO 점수에서 제외되며, 'Aggressive Entry' 태그로 평가됩니다.
                  </div>
                </div>
              </div>
            </button>

            {/* Option 2: Aggressive Entry */}
            <button
              onClick={() => handleSelect('AGGRESSIVE_ENTRY')}
              className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                isDarkMode
                  ? 'bg-purple-950/30 border-purple-900/50 hover:border-purple-700 hover:bg-purple-950/50'
                  : 'bg-purple-50 border-purple-200 hover:border-purple-400 hover:bg-purple-100'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${
                  isDarkMode ? 'bg-purple-900/40 text-purple-400' : 'bg-purple-100 text-purple-600'
                }`}>
                  <Zap className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className={`font-semibold mb-1 ${
                    isDarkMode ? 'text-purple-300' : 'text-purple-900'
                  }`}>
                    네, 공격적 진입(Aggressive Entry) 전략입니다
                  </div>
                  <div className={`text-xs ${
                    isDarkMode ? 'text-purple-200/70' : 'text-purple-700'
                  }`}>
                    모멘텀을 따라 고가 진입을 선택한 의도적인 전략입니다.
                    FOMO 점수에서 제외됩니다.
                  </div>
                </div>
              </div>
            </button>

            {/* Option 3: FOMO */}
            <button
              onClick={() => handleSelect('FOMO')}
              className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                isDarkMode
                  ? 'bg-red-950/30 border-red-900/50 hover:border-red-700 hover:bg-red-950/50'
                  : 'bg-red-50 border-red-200 hover:border-red-400 hover:bg-red-100'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${
                  isDarkMode ? 'bg-red-900/40 text-red-400' : 'bg-red-100 text-red-600'
                }`}>
                  <AlertCircle className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className={`font-semibold mb-1 ${
                    isDarkMode ? 'text-red-300' : 'text-red-900'
                  }`}>
                    아니요, 뇌동매매였습니다
                  </div>
                  <div className={`text-xs ${
                    isDarkMode ? 'text-red-200/70' : 'text-red-700'
                  }`}>
                    고가 매수는 감정적 판단이었습니다. 시스템의 FOMO 진단이 정확합니다.
                    "솔직한 인정이 발전의 시작입니다."
                  </div>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
