
import React, { useRef, useState } from 'react';
import { Upload, FileText, AlertCircle, Skull, GitMerge, Database, FileSpreadsheet, FileSearch, TrendingUp, Brain, Shield } from 'lucide-react';
import { parseCSV, analyzeTrades } from '../services/analysisEngine';
import { AnalysisResult } from '../types';
import Threads from './Threads';

interface UploadViewProps {
  onAnalyze: (result: AnalysisResult) => void;
}

const SAMPLE_PAIRED = `Ticker,Entry Date,Entry Price,Exit Date,Exit Price,Qty
AAPL,2023-01-10,130.50,2023-01-15,135.20,100
TSLA,2023-02-01,180.00,2023-02-03,172.50,50
NVDA,2023-02-10,210.00,2023-02-20,230.00,20
AMD,2023-03-05,85.00,2023-03-06,82.00,200
GOOGL,2023-03-10,95.00,2023-03-25,105.00,100
AMZN,2023-04-01,100.00,2023-04-05,98.00,150`;

const SAMPLE_LOG = `Ticker,Date,Action,Price,Qty
AAPL,2023-01-10,BUY,130.50,100
AAPL,2023-01-12,BUY,132.00,50
AAPL,2023-01-15,SELL,135.20,150
TSLA,2023-02-01,BUY,180.00,50
TSLA,2023-02-03,SELL,172.50,50`;

const REKT_LOG = `Ticker,Date,Action,Price,Qty
GME,2021-01-27,BUY,350.00,10
GME,2021-01-28,SELL,120.00,10
GME,2021-01-28,BUY,150.00,20
GME,2021-01-28,SELL,130.00,20
GME,2021-01-28,BUY,140.00,50
GME,2021-01-28,SELL,125.00,50
TSLA,2023-02-01,BUY,198.00,20
TSLA,2023-02-02,SELL,180.00,20
TSLA,2023-02-02,BUY,185.00,30
TSLA,2023-02-03,SELL,175.00,30`;

export const UploadView: React.FC<UploadViewProps> = ({ onAnalyze }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [loadingStage, setLoadingStage] = useState<string>('');

  const handleFile = async (file: File) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        setIsProcessing(true);
        setLoadingStage('CSV 파일 파싱 중...');
        
        const text = e.target?.result as string;
        const rows = parseCSV(text);
        if (rows.length === 0) throw new Error("No valid data found.");
        
        setLoadingStage('시장 데이터 수집 중...');
        // analyzeTrades 내부에서 단계별 진행 상황을 시뮬레이션하기 위해
        // 약간의 지연을 추가하여 사용자 경험 개선
        await new Promise(resolve => setTimeout(resolve, 300));
        
        setLoadingStage('FOMO 패턴 탐지 중...');
        await new Promise(resolve => setTimeout(resolve, 300));
        
        setLoadingStage('Panic Sell 패턴 분석 중...');
        await new Promise(resolve => setTimeout(resolve, 300));
        
        setLoadingStage('GPT-4o가 심리 분석 중...');
        const result = await analyzeTrades(rows);
        
        setLoadingStage('분석 완료!');
        await new Promise(resolve => setTimeout(resolve, 200));
        
        onAnalyze(result);
      } catch (err) {
        setError("Format Error. Ensure headers match 'Ticker,Date,Action,Price,Qty' or 'Ticker,Entry Date...'.");
      } finally {
        setIsProcessing(false);
        setLoadingStage('');
      }
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  };

  const loadSample = async (csvData: string) => {
    setIsProcessing(true);
    setLoadingStage('CSV 파일 파싱 중...');
    
    const rows = parseCSV(csvData);
    
    setLoadingStage('시장 데이터 수집 중...');
    await new Promise(resolve => setTimeout(resolve, 300));
    
    setLoadingStage('FOMO 패턴 탐지 중...');
    await new Promise(resolve => setTimeout(resolve, 300));
    
    setLoadingStage('Panic Sell 패턴 분석 중...');
    await new Promise(resolve => setTimeout(resolve, 300));
    
    setLoadingStage('GPT-4o가 심리 분석 중...');
    const result = await analyzeTrades(rows);
    
    setLoadingStage('분석 완료!');
    await new Promise(resolve => setTimeout(resolve, 200));
    
    onAnalyze(result);
    setIsProcessing(false);
    setLoadingStage('');
  };


  const downloadSample = () => {
    const header = "Ticker,Entry Date,Entry Price,Exit Date,Exit Price,Qty\n";
    const row = "AAPL,2023-01-10,130.50,2023-01-15,135.20,100";
    const blob = new Blob([header + row], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "truth_pipeline_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#09090b]">
      {/* Threads 배경 */}
      <div className="absolute inset-0 z-0">
        <Threads
          color={[0.1, 0.9, 0.5]} // emerald 색상 (RGB 0-1 범위)
          amplitude={1}
          distance={0}
          enableMouseInteraction={true}
        />
      </div>

      {/* 콘텐츠 레이어 */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen p-6">
        <div className="max-w-2xl w-full text-center space-y-10">
          <div className="space-y-6">
            {/* PRISM 타이틀 */}
            <h1 className="text-7xl font-extrabold tracking-tighter text-white drop-shadow-[0_0_20px_rgba(16,185,129,0.5)]">
              PRISM
            </h1>
            <div className="space-y-3">
              <h2 className="text-2xl font-bold text-white max-w-2xl mx-auto">
                Uncover Your Trading Blind Spots
              </h2>
              <p className="text-lg text-zinc-300 max-w-2xl mx-auto leading-relaxed">
                Upload your transaction history and let our AI reveal the psychological patterns costing you money.
              </p>
            </div>
          </div>

          <div 
            className="relative border-2 border-dashed border-zinc-800/50 rounded-3xl p-16 hover:border-emerald-500/50 hover:bg-zinc-900/50 transition-all cursor-pointer group bg-zinc-950/70 backdrop-blur-sm"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          {isProcessing ? (
             <div className="flex flex-col items-center gap-6">
                <div className="p-6 bg-zinc-900 rounded-full border border-zinc-800">
                    {loadingStage.includes('파싱') && <FileSearch className="w-10 h-10 text-emerald-500" />}
                    {loadingStage.includes('시장 데이터') && <Database className="w-10 h-10 text-emerald-500 animate-spin" />}
                    {loadingStage.includes('패턴') && <TrendingUp className="w-10 h-10 text-emerald-500" />}
                    {loadingStage.includes('GPT') && <Brain className="w-10 h-10 text-emerald-500" />}
                    {!loadingStage && <Database className="w-10 h-10 text-emerald-500 animate-spin" />}
                </div>
                <div className="space-y-2 text-center">
                    <p className="text-zinc-200 font-medium">{loadingStage || '분석 중...'}</p>
                    <div className="flex items-center justify-center gap-2 text-xs text-zinc-500">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                      <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                      <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                    </div>
                </div>
             </div>
          ) : (
              <div className="flex flex-col items-center gap-6">
                <div className="p-6 bg-zinc-900 rounded-full border border-zinc-800 group-hover:border-emerald-500/30 group-hover:text-emerald-400 transition-all">
                  <Upload className="w-10 h-10 text-zinc-400 group-hover:text-emerald-400" />
                </div>
                <div className="space-y-2">
                  <p className="text-xl font-medium text-zinc-200">거래 내역을 드래그하여 업로드하세요</p>
                  <div className="text-sm text-zinc-500">
                     <p>필수 형식: Ticker, Entry Date, Entry Price, Exit Date, Exit Price, Qty</p>
                     <button onClick={(e) => { e.stopPropagation(); downloadSample(); }} className="text-emerald-500 hover:underline mt-2 text-xs">
                        템플릿 CSV 다운로드
                     </button>
                  </div>
                  <div className="mt-4 pt-4 border-t border-zinc-800/50">
                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                      <Shield className="w-4 h-4" />
                      <span>데이터는 익명화되며 이 분석에만 사용됩니다. 원본 거래 내역은 저장하지 않습니다.</span>
                    </div>
                  </div>
                </div>
              </div>
          )}
          <input 
            type="file" 
            ref={fileInputRef}
            className="hidden" 
            accept=".csv"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
        </div>

        {error && (
            <div className="flex items-center gap-2 text-red-400 bg-red-950/20 border border-red-900/30 p-4 rounded-lg justify-center">
              <AlertCircle className="w-5 h-5" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-zinc-800/50">
            <button 
              onClick={() => loadSample(SAMPLE_PAIRED)}
              className="bg-zinc-900/50 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 px-4 py-4 rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:scale-[1.02]"
            >
              <FileSpreadsheet className="w-5 h-5 text-emerald-500" />
              <span className="text-sm font-medium">Standard CSV</span>
              <span className="text-[10px] text-zinc-500">Pre-paired Trades</span>
            </button>
            
            <button 
              onClick={() => loadSample(SAMPLE_LOG)}
              className="bg-zinc-900/50 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 px-4 py-4 rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:scale-[1.02]"
            >
              <GitMerge className="w-5 h-5 text-blue-500" />
              <span className="text-sm font-medium">Execution Log</span>
              <span className="text-[10px] text-zinc-500">Test FIFO Logic</span>
            </button>
            
            <button 
              onClick={() => loadSample(REKT_LOG)}
              className="bg-red-950/10 hover:bg-red-900/20 border border-red-900/30 text-red-400 px-4 py-4 rounded-xl flex flex-col items-center justify-center gap-2 transition-all hover:scale-[1.02]"
            >
              <Skull className="w-5 h-5" />
              <span className="text-sm font-medium">"Rekt" Mode</span>
              <span className="text-[10px] text-red-500/60">High FOMO & Revenge</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
