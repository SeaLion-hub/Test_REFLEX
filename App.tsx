import React, { useState, useEffect } from 'react';
import { UploadView } from './components/UploadView';
import { Dashboard } from './components/Dashboard';
import { AnalysisResult } from './types';

const App: React.FC = () => {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [showAnalysisReport, setShowAnalysisReport] = useState(false);

  useEffect(() => {
    if (result) {
      // 분석 완료 - 모달은 더 이상 자동으로 표시하지 않음 (메인 뷰에 통합됨)
      setShowAnalysisReport(false);
    }
  }, [result]);

  return (
    <div className="antialiased">
      {!result ? (
        <UploadView onAnalyze={setResult} />
      ) : (
        <Dashboard 
          data={result} 
          onReset={() => {
            setResult(null);
            setShowAnalysisReport(false);
          }}
          showAnalysisReport={showAnalysisReport}
          onCloseAnalysisReport={() => setShowAnalysisReport(false)}
        />
      )}
    </div>
  );
};

export default App;
