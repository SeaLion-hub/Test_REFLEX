import React, { useState, useEffect } from 'react';
import { UploadView } from './components/UploadView';
import { Dashboard } from './components/Dashboard';
import { AnalysisTransition } from './components/AnalysisTransition';
import { AnalysisResult } from './types';

const App: React.FC = () => {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [showAnalysisReport, setShowAnalysisReport] = useState(false);
  const [showTransition, setShowTransition] = useState(false);

  useEffect(() => {
    if (result) {
      // 분석 완료 - 바로 Dashboard로 전환 (전환 화면 제거)
      setShowTransition(false);
      setShowAnalysisReport(false);
    }
  }, [result]);

  const handleTransitionComplete = () => {
    setShowTransition(false);
  };

  const handleReset = () => {
    setResult(null);
    setShowAnalysisReport(false);
    setShowTransition(false);
  };

  return (
    <div className="antialiased bg-[#09090b] min-h-screen">
      {!result ? (
        <UploadView onAnalyze={setResult} />
      ) : showTransition ? (
        <AnalysisTransition 
          result={result} 
          onComplete={handleTransitionComplete}
        />
      ) : (
        <Dashboard 
          data={result} 
          onReset={handleReset}
          showAnalysisReport={showAnalysisReport}
          onCloseAnalysisReport={() => setShowAnalysisReport(false)}
        />
      )}
    </div>
  );
};

export default App;
