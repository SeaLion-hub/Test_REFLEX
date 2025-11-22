import React, { useState } from 'react';
import { Brain, AlertTriangle, CheckCircle2, Zap, Award, TrendingUp, TrendingDown, Target, BookOpen, X, Frown, Meh, Smile, Info } from 'lucide-react';
import { AIAnalysis, RAGReference } from '../types';

interface AICoachProps {
  analysis: AIAnalysis | null;
  loading: boolean;
  truthScore?: number; // Truth Score를 prop으로 받음
}

interface RAGModalProps {
  reference: RAGReference;
  isOpen: boolean;
  onClose: () => void;
  isDarkMode?: boolean;
}

// RAG 원칙 팝업 모달
const RAGModal: React.FC<RAGModalProps> = ({ reference, isOpen, onClose, isDarkMode = true }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className={`relative z-10 w-full max-w-lg rounded-xl shadow-2xl border ${
        isDarkMode
          ? 'bg-zinc-900 border-zinc-800'
          : 'bg-white border-zinc-200'
      }`}>
        <div className={`flex items-center justify-between p-6 border-b ${
          isDarkMode ? 'border-zinc-800' : 'border-zinc-200'
        }`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              isDarkMode ? 'bg-purple-900/30 text-purple-400' : 'bg-purple-100 text-purple-600'
            }`}>
              <BookOpen className="w-5 h-5" />
            </div>
            <h2 className={`text-lg font-bold ${
              isDarkMode ? 'text-zinc-100' : 'text-zinc-900'
            }`}>
              행동 금융학 원칙
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
            <h3 className={`text-xl font-bold mb-2 ${
              isDarkMode ? 'text-purple-300' : 'text-purple-900'
            }`}>
              {reference.title}
            </h3>
            <p className={`text-sm leading-relaxed ${
              isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
            }`}>
              {reference.content}
            </p>
          </div>
          <div className={`p-4 rounded-lg border ${
            isDarkMode
              ? 'bg-emerald-950/20 border-emerald-900/30'
              : 'bg-emerald-50 border-emerald-200'
          }`}>
            <div className="flex items-start gap-2">
              <Zap className={`w-5 h-5 mt-0.5 ${
                isDarkMode ? 'text-emerald-400' : 'text-emerald-600'
              }`} />
              <div>
                <h4 className={`font-semibold mb-1 ${
                  isDarkMode ? 'text-emerald-300' : 'text-emerald-900'
                }`}>
                  실천 방법
                </h4>
                <p className={`text-sm ${
                  isDarkMode ? 'text-emerald-200' : 'text-emerald-700'
                }`}>
                  {reference.action}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const AICoach: React.FC<AICoachProps> = ({ analysis, loading, truthScore }) => {
  const [selectedReference, setSelectedReference] = useState<RAGReference | null>(null);

  // Truth Score 기반 AI 페르소나 결정
  const getAIPersona = (score: number) => {
    if (score < 50) {
      return {
        icon: Frown,
        iconEmoji: '😠',
        tone: 'warning',
        bgColor: 'bg-red-950/20',
        borderColor: 'border-red-900/50',
        iconBg: 'bg-red-900/30',
        iconColor: 'text-red-400',
        prefix: '⚠️ 경고: ',
        message: '이 패턴이 계속되면 위험합니다'
      };
    } else if (score < 75) {
      return {
        icon: Meh,
        iconEmoji: '😐',
        tone: 'neutral',
        bgColor: 'bg-yellow-950/20',
        borderColor: 'border-yellow-900/50',
        iconBg: 'bg-yellow-900/30',
        iconColor: 'text-yellow-400',
        prefix: '💡 개선 필요: ',
        message: '개선할 여지가 있습니다'
      };
    } else {
      return {
        icon: Smile,
        iconEmoji: '😊',
        tone: 'positive',
        bgColor: 'bg-emerald-950/20',
        borderColor: 'border-emerald-900/50',
        iconBg: 'bg-emerald-900/30',
        iconColor: 'text-emerald-400',
        prefix: '✅ 잘하고 있어요: ',
        message: '좋은 패턴을 유지하세요'
      };
    }
  };

  const persona = truthScore !== undefined ? getAIPersona(truthScore) : null;
  const PersonaIcon = persona?.icon || Brain;

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
      {/* AI 페르소나 헤더 (Truth Score 기반) */}
      <div className={`flex items-center gap-3 mb-6 p-4 rounded-lg border ${
        persona ? `${persona.bgColor} ${persona.borderColor}` : 'bg-purple-900/30 border-purple-800'
      }`}>
        <div className={`p-2 rounded-lg ${
          persona ? `${persona.iconBg} ${persona.iconColor}` : 'bg-purple-900/30 text-purple-400'
        }`}>
          {persona ? (
            <PersonaIcon className="w-6 h-6" />
          ) : (
            <Brain className="w-6 h-6" />
          )}
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-bold text-zinc-100">AI Interpretation</h2>
          {persona && (
            <p className={`text-sm mt-1 ${persona.iconColor}`}>
              {persona.prefix}{persona.message}
            </p>
          )}
        </div>
        {persona && (
          <span className="text-2xl">{persona.iconEmoji}</span>
        )}
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

      {/* RAG 참고 원칙 태그 */}
      {analysis.references && analysis.references.length > 0 && (
        <div className="bg-gradient-to-br from-purple-950/20 to-indigo-900/10 border border-purple-900/30 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-5 h-5 text-purple-400" />
            <h3 className="text-sm font-bold text-purple-400 uppercase tracking-wider">
              참고 원칙 (행동 금융학 기반)
            </h3>
          </div>
          <p className="text-xs text-purple-200/80 mb-3">
            AI 진단은 아래 행동 금융학 원칙에 근거합니다. 클릭하면 상세 내용을 확인할 수 있습니다.
          </p>
          <div className="flex flex-wrap gap-2">
            {analysis.references.map((ref, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedReference(ref)}
                className="text-xs px-3 py-2 bg-purple-900/20 border border-purple-800/50 rounded-lg hover:bg-purple-900/30 hover:border-purple-700/70 transition-all text-purple-300 hover:text-purple-200 flex items-center gap-2"
              >
                <BookOpen className="w-3 h-3" />
                {ref.title} →
              </button>
            ))}
          </div>
        </div>
      )}

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

      {/* RAG 원칙 팝업 모달 */}
      {selectedReference && (
        <RAGModal
          reference={selectedReference}
          isOpen={!!selectedReference}
          onClose={() => setSelectedReference(null)}
          isDarkMode={true}
        />
      )}
    </div>
  );
};
