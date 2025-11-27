import React, { useEffect, useState } from 'react';
import { AnalysisResult } from '../types';
import Threads from './Threads';

interface AnalysisTransitionProps {
  result: AnalysisResult;
  onComplete: () => void;
}

export const AnalysisTransition: React.FC<AnalysisTransitionProps> = ({ result, onComplete }) => {
  const [showDashboard, setShowDashboard] = useState(false);

  const finalScore = result.metrics.truthScore;

  useEffect(() => {
    // 짧은 딜레이 후 Dashboard로 전환
    const timer = setTimeout(() => {
      setShowDashboard(true);
      setTimeout(() => {
        onComplete();
      }, 500);
    }, 1000);

    return () => clearTimeout(timer);
  }, [onComplete]);

  // Truth Score 색상 결정
  const scoreColor = finalScore >= 75 
    ? 'text-emerald-400' 
    : finalScore >= 50 
    ? 'text-yellow-400' 
    : 'text-red-400';
  
  const scoreRing = finalScore >= 75 
    ? 'border-emerald-500' 
    : finalScore >= 50 
    ? 'border-yellow-500' 
    : 'border-red-500';

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#09090b]">
      {/* Threads 배경 */}
      <div className={`absolute inset-0 z-0 transition-opacity duration-700 ${
        showDashboard ? 'opacity-0' : 'opacity-100'
      }`}>
        <Threads
          color={[0.1, 0.9, 0.5]} // emerald 색상
          amplitude={1}
          distance={0}
          enableMouseInteraction={true}
        />
      </div>

      {/* 콘텐츠 레이어 */}
      <div className={`relative z-10 flex flex-col items-center justify-center min-h-screen p-6 transition-opacity duration-700 ${
        showDashboard ? 'opacity-0' : 'opacity-100'
      }`}>
        <div className="text-center space-y-8">
          {/* Truth Score 다이얼 */}
          <div className="flex flex-col items-center">
            <div className={`w-64 h-64 rounded-full border-8 ${scoreRing} flex items-center justify-center shadow-[0_0_40px_rgba(0,0,0,0.8)] relative bg-[#0c0c0e] transition-all duration-300 ${
              showDashboard ? 'scale-95 opacity-0' : 'scale-100 opacity-100'
            }`}>
              <span className={`text-8xl font-bold tracking-tighter ${scoreColor} transition-all duration-200`}>
                {finalScore}
              </span>
            </div>
            
            {/* 완료 메시지 */}
            <div className={`mt-8 transition-opacity duration-300 ${
              showDashboard ? 'opacity-0' : 'opacity-100'
            }`}>
              <p className="text-emerald-400 text-xl font-semibold">분석 완료</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

