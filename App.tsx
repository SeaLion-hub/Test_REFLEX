import React, { useState } from 'react';
import { UploadView } from './components/UploadView';
import { Dashboard } from './components/Dashboard';
import { AnalysisResult } from './types';

const App: React.FC = () => {
  const [result, setResult] = useState<AnalysisResult | null>(null);

  return (
    <div className="antialiased">
      {!result ? (
        <UploadView onAnalyze={setResult} />
      ) : (
        <Dashboard data={result} onReset={() => setResult(null)} />
      )}
    </div>
  );
};

export default App;
