import React, { useState } from 'react';
import { Brain, AlertTriangle, CheckCircle2, Zap, Award, TrendingUp, TrendingDown, Target, BookOpen, X, Frown, Meh, Smile, Info } from 'lucide-react';
import { AIAnalysis, RAGReference } from '../types';

interface AICoachProps {
  analysis: AIAnalysis | null;
  loading: boolean;
  truthScore?: number; // Truth Score를 prop으로 받음
  isDarkMode?: boolean; // 다크모드 상태
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
            <h3 className={`text-xl font-bold mb-3 ${
              isDarkMode ? 'text-purple-300' : 'text-purple-900'
            }`}>
              {reference.title}
            </h3>
            
            {/* Definition */}
            <div className="mb-4">
              <h4 className={`text-xs font-bold uppercase tracking-wider mb-2 ${
                isDarkMode ? 'text-purple-400' : 'text-purple-700'
              }`}>
                정의
              </h4>
              <p className={`text-sm leading-relaxed ${
                isDarkMode ? 'text-zinc-300' : 'text-zinc-700'
              }`}>
                {reference.definition}
              </p>
            </div>

            {/* Connection */}
            <div className={`mb-4 p-3 rounded-lg border ${
              isDarkMode
                ? 'bg-blue-950/20 border-blue-900/30'
                : 'bg-blue-50 border-blue-200'
            }`}>
              <h4 className={`text-xs font-bold uppercase tracking-wider mb-2 ${
                isDarkMode ? 'text-blue-400' : 'text-blue-700'
              }`}>
                시스템 연결
              </h4>
              <p className={`text-sm leading-relaxed ${
                isDarkMode ? 'text-blue-200' : 'text-blue-800'
              }`}>
                {reference.connection}
              </p>
            </div>

            {/* Prescription */}
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
                    처방
                  </h4>
                  <p className={`text-sm ${
                    isDarkMode ? 'text-emerald-200' : 'text-emerald-700'
                  }`}>
                    {reference.prescription}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const AICoach: React.FC<AICoachProps> = ({ analysis, loading, truthScore, isDarkMode = false }) => {
  const [selectedReference, setSelectedReference] = useState<RAGReference | null>(null);

  // Truth Score 기반 AI 페르소나 결정
  const getAIPersona = (score: number) => {
    if (score < 50) {
      return {
        icon: Frown,
        iconEmoji: '😠',
        tone: 'warning',
        bgColor: isDarkMode ? 'bg-red-950/20' : 'bg-red-50',
        borderColor: isDarkMode ? 'border-red-900/50' : 'border-red-300',
        iconBg: isDarkMode ? 'bg-red-900/30' : 'bg-red-100',
        iconColor: isDarkMode ? 'text-red-400' : 'text-red-600',
        prefix: '⚠️ 경고: ',
        message: '이 패턴이 계속되면 위험합니다'
      };
    } else if (score < 75) {
      return {
        icon: Meh,
        iconEmoji: '😐',
        tone: 'neutral',
        bgColor: isDarkMode ? 'bg-yellow-950/20' : 'bg-yellow-50',
        borderColor: isDarkMode ? 'border-yellow-900/50' : 'border-yellow-300',
        iconBg: isDarkMode ? 'bg-yellow-900/30' : 'bg-yellow-100',
        iconColor: isDarkMode ? 'text-yellow-400' : 'text-yellow-600',
        prefix: '💡 개선 필요: ',
        message: '개선할 여지가 있습니다'
      };
    } else {
      return {
        icon: Smile,
        iconEmoji: '😊',
        tone: 'positive',
        bgColor: isDarkMode ? 'bg-emerald-950/20' : 'bg-emerald-50',
        borderColor: isDarkMode ? 'border-emerald-900/50' : 'border-emerald-300',
        iconBg: isDarkMode ? 'bg-emerald-900/30' : 'bg-emerald-100',
        iconColor: isDarkMode ? 'text-emerald-400' : 'text-emerald-600',
        prefix: '✅ 잘하고 있어요: ',
        message: '좋은 패턴을 유지하세요'
      };
    }
  };

  const persona = truthScore !== undefined ? getAIPersona(truthScore) : null;
  const PersonaIcon = persona?.icon || Brain;

  if (loading) {
    return (
      <div className={`border rounded-xl p-6 space-y-4 transition-colors ${
        isDarkMode 
          ? 'bg-zinc-900 border-zinc-800' 
          : 'bg-white border-zinc-200'
      }`}>
        <div className={`h-6 w-1/3 rounded ${
          isDarkMode ? 'bg-zinc-800' : 'bg-zinc-200'
        }`}></div>
        <div className="space-y-2">
          <div className={`h-4 rounded w-full ${
            isDarkMode ? 'bg-zinc-800' : 'bg-zinc-200'
          }`}></div>
          <div className={`h-4 rounded w-5/6 ${
            isDarkMode ? 'bg-zinc-800' : 'bg-zinc-200'
          }`}></div>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className={`border rounded-xl p-6 lg:p-8 space-y-8 transition-colors ${
      isDarkMode 
        ? 'bg-gradient-to-b from-zinc-900 to-zinc-950 border-zinc-800' 
        : 'bg-gradient-to-b from-white to-zinc-50 border-zinc-200'
    }`}>
      {/* AI 페르소나 헤더 (Truth Score 기반) */}
      <div className={`flex items-center gap-3 mb-6 p-4 rounded-lg border ${
        persona 
          ? `${persona.bgColor} ${persona.borderColor}` 
          : isDarkMode 
            ? 'bg-purple-900/30 border-purple-800' 
            : 'bg-purple-100/50 border-purple-300'
      }`}>
        <div className={`p-2 rounded-lg ${
          persona 
            ? `${persona.iconBg} ${persona.iconColor}` 
            : isDarkMode 
              ? 'bg-purple-900/30 text-purple-400' 
              : 'bg-purple-100 text-purple-600'
        }`}>
          {persona ? (
            <PersonaIcon className="w-6 h-6" />
          ) : (
            <Brain className="w-6 h-6" />
          )}
        </div>
        <div className="flex-1">
          <h2 className={`text-xl font-bold ${
            isDarkMode ? 'text-zinc-100' : 'text-zinc-900'
          }`}>AI 해석</h2>
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

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <div>
            <h3 className={`text-sm font-medium uppercase tracking-wider mb-2 ${
              isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
            }`}>진단</h3>
            <p className={`text-lg leading-relaxed border-l-2 pl-4 ${
              isDarkMode 
                ? 'text-zinc-200 border-purple-500/50' 
                : 'text-zinc-800 border-purple-400/50'
            }`}>
              {analysis.diagnosis}
            </p>
          </div>
          
          <div>
             <h3 className={`text-sm font-medium uppercase tracking-wider mb-2 ${
               isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
             }`}>주요 편향</h3>
             <div className={`flex items-center gap-2 p-3 rounded-lg border w-fit ${
               isDarkMode
                 ? 'text-red-400 bg-red-950/10 border-red-900/20'
                 : 'text-red-600 bg-red-50 border-red-200'
             }`}>
                <AlertTriangle className="w-5 h-5" />
                <span className="font-semibold">{analysis.bias}</span>
             </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className={`border p-4 rounded-xl ${
            isDarkMode
              ? 'bg-emerald-950/10 border-emerald-900/20'
              : 'bg-emerald-50 border-emerald-200'
          }`}>
            <h3 className={`text-sm font-medium uppercase tracking-wider mb-2 flex items-center gap-2 ${
              isDarkMode ? 'text-emerald-500' : 'text-emerald-600'
            }`}>
                <CheckCircle2 className="w-4 h-4" />
                원칙
            </h3>
            <p className={`text-xl font-serif italic ${
              isDarkMode ? 'text-emerald-100' : 'text-emerald-900'
            }`}>
              "{analysis.rule}"
            </p>
          </div>

          <div>
            <h3 className={`text-sm font-medium uppercase tracking-wider mb-2 ${
              isDarkMode ? 'text-zinc-500' : 'text-zinc-600'
            }`}>우선 수정 사항</h3>
            <div className="flex items-start gap-3">
                <div className={`mt-1 p-1 rounded ${
                  isDarkMode 
                    ? 'bg-blue-900/30 text-blue-400' 
                    : 'bg-blue-100 text-blue-600'
                }`}>
                    <Zap className="w-4 h-4" />
                </div>
                <p className={isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}>
                  {analysis.fix}
                </p>
            </div>
          </div>
        </div>
      </div>

      {/* RAG 참고 원칙 태그 */}
      {analysis.references && analysis.references.length > 0 && (
        <div className={`border rounded-xl p-6 space-y-4 ${
          isDarkMode
            ? 'bg-gradient-to-br from-purple-950/20 to-indigo-900/10 border-purple-900/30'
            : 'bg-gradient-to-br from-purple-50 to-indigo-50 border-purple-200'
        }`}>
          <div className="flex items-center gap-2 mb-4">
            <Info className={`w-5 h-5 ${
              isDarkMode ? 'text-purple-400' : 'text-purple-600'
            }`} />
            <h3 className={`text-sm font-bold uppercase tracking-wider ${
              isDarkMode ? 'text-purple-400' : 'text-purple-600'
            }`}>
              참고 원칙 (행동 금융학 기반)
            </h3>
          </div>
          <p className={`text-xs mb-3 ${
            isDarkMode ? 'text-purple-200/80' : 'text-purple-700/80'
          }`}>
            AI 진단은 아래 행동 금융학 원칙에 근거합니다. 클릭하면 상세 내용을 확인할 수 있습니다.
          </p>
          <div className="flex flex-wrap gap-2">
            {analysis.references.map((ref, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedReference(ref)}
                className={`text-xs px-3 py-2 border rounded-lg transition-all flex items-center gap-2 ${
                  isDarkMode
                    ? 'bg-purple-900/20 border-purple-800/50 hover:bg-purple-900/30 hover:border-purple-700/70 text-purple-300 hover:text-purple-200'
                    : 'bg-purple-100 border-purple-300 hover:bg-purple-200 hover:border-purple-400 text-purple-700 hover:text-purple-900'
                }`}
              >
                <BookOpen className="w-3 h-3" />
                {ref.title} →
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Personal Playbook (3A: 3단계 구조) */}
      {analysis.playbook && (analysis.playbook.plan_step_1 || analysis.playbook.rules) && (
        <div className={`border rounded-xl p-6 space-y-4 ${
          isDarkMode
            ? 'bg-gradient-to-br from-blue-950/20 to-indigo-900/10 border-blue-900/30'
            : 'bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200'
        }`}>
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className={`w-5 h-5 ${
              isDarkMode ? 'text-blue-400' : 'text-blue-600'
            }`} />
            <h3 className={`text-sm font-bold uppercase tracking-wider ${
              isDarkMode ? 'text-blue-400' : 'text-blue-600'
            }`}>
              3단계 회복 플랜
            </h3>
          </div>
          <div className={`border rounded-lg p-4 mb-3 ${
            isDarkMode
              ? 'bg-blue-950/30 border-blue-900/40'
              : 'bg-blue-100 border-blue-300'
          }`}>
            <p className={`text-xs mb-2 ${
              isDarkMode ? 'text-blue-200/80' : 'text-blue-800/80'
            }`}>
              AI가 당신의 거래 패턴을 분석하여 생성한 개인화된 행동 계획입니다.
            </p>
            <p className={`text-xs italic ${
              isDarkMode ? 'text-blue-300/60' : 'text-blue-700/60'
            }`}>
              기반: {analysis.playbook.based_on?.primary_bias || '일반'} 편향, {analysis.playbook.based_on?.patterns || 0}개 패턴
            </p>
          </div>
          
          {/* 3A: 3단계 고정 구조 표시 */}
          {analysis.playbook.plan_step_1 ? (
            <div className="space-y-3">
              <div className={`flex items-start gap-3 p-3 rounded-lg border ${
                isDarkMode
                  ? 'bg-blue-950/20 border-blue-900/30'
                  : 'bg-blue-50 border-blue-200'
              }`}>
                <span className={`mt-1 font-bold text-lg ${
                  isDarkMode ? 'text-blue-400' : 'text-blue-600'
                }`}>1</span>
                <span className={`flex-1 leading-relaxed ${
                  isDarkMode ? 'text-zinc-200' : 'text-zinc-800'
                }`}>{analysis.playbook.plan_step_1}</span>
              </div>
              <div className={`flex items-start gap-3 p-3 rounded-lg border ${
                isDarkMode
                  ? 'bg-blue-950/20 border-blue-900/30'
                  : 'bg-blue-50 border-blue-200'
              }`}>
                <span className={`mt-1 font-bold text-lg ${
                  isDarkMode ? 'text-blue-400' : 'text-blue-600'
                }`}>2</span>
                <span className={`flex-1 leading-relaxed ${
                  isDarkMode ? 'text-zinc-200' : 'text-zinc-800'
                }`}>{analysis.playbook.plan_step_2}</span>
              </div>
              <div className={`flex items-start gap-3 p-3 rounded-lg border ${
                isDarkMode
                  ? 'bg-blue-950/20 border-blue-900/30'
                  : 'bg-blue-50 border-blue-200'
              }`}>
                <span className={`mt-1 font-bold text-lg ${
                  isDarkMode ? 'text-blue-400' : 'text-blue-600'
                }`}>3</span>
                <span className={`flex-1 leading-relaxed ${
                  isDarkMode ? 'text-zinc-200' : 'text-zinc-800'
                }`}>{analysis.playbook.plan_step_3}</span>
              </div>
            </div>
          ) : (
            /* 하위 호환성: 기존 rules 표시 */
            analysis.playbook.rules && analysis.playbook.rules.length > 0 && (
              <ul className="space-y-2">
                {analysis.playbook.rules.map((rule, idx) => (
                  <li key={idx} className={`flex items-start gap-3 ${
                    isDarkMode ? 'text-zinc-200' : 'text-zinc-800'
                  }`}>
                    <span className={`mt-1 font-bold ${
                      isDarkMode ? 'text-blue-400' : 'text-blue-600'
                    }`}>•</span>
                    <span className="flex-1 leading-relaxed">{rule}</span>
                  </li>
                ))}
              </ul>
            )
          )}
        </div>
      )}

      {/* RAG 원칙 팝업 모달 */}
      {selectedReference && (
        <RAGModal
          reference={selectedReference}
          isOpen={!!selectedReference}
          onClose={() => setSelectedReference(null)}
          isDarkMode={isDarkMode}
        />
      )}
    </div>
  );
};
