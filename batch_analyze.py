import os
import glob
import requests
import pandas as pd
import time
import json

# ---------------------------------------------------------
# 1. 설정
# ---------------------------------------------------------
API_URL = "http://127.0.0.1:8000/analyze"
INPUT_PATTERN = "trader_*.csv"  # 분석할 파일 패턴
OUTPUT_FILE = "analysis_summary.csv"

# ---------------------------------------------------------
# 2. 페르소나 분류 로직 (프론트엔드 로직 포팅)
# ---------------------------------------------------------
def classify_persona(metrics):
    # 지표 추출
    fomo_index = metrics.get('fomo_score', 0)
    panic_index = metrics.get('panic_score', 0) # 백엔드에서 1 - weighted_avg로 옴 (높을수록 Panic 성향)
    # 백엔드 panic_score: 1.0 - weighted_avg (panic_score가 낮을수록 저점 매도이므로, weighted_avg가 낮음 -> panic_index가 높음? 아니면 반대?)
    # models.py 확인: panic_index = 1.0 - weighted_panic_avg.
    # weighted_panic_avg는 panic_score(0~1)들의 평균.
    # panic_score는 (매도가 - 저가)/(고가 - 저가). 즉 0에 가까울수록 바닥 매도(나쁨).
    # 바닥 매도를 많이 하면 weighted_panic_avg가 낮아짐 (예: 0.1).
    # 그러면 panic_index = 1 - 0.1 = 0.9.
    # 즉, Panic Index가 높을수록 "공포 매도 성향"이 강함 (Bad). -> Fear Value = panic_index * 100
    
    revenge_count = metrics.get('revenge_trading_count', 0)
    disposition_ratio = metrics.get('disposition_ratio', 0)

    # 시각화 점수 변환 (0~100)
    fear = panic_index * 100
    greed = fomo_index * 100
    resilience = max(0, 100 - (revenge_count * 25)) # 낮을수록 나쁨
    discipline = max(0, 200 - (disposition_ratio * 100)) # 낮을수록 나쁨

    # 분류 로직 (Charts.tsx와 동일)
    if resilience <= 50: return "도박사 (Gambler)"
    if discipline < 50: return "존버족 (Bag Holder)"
    if greed > 70: return "불나방 (FOMO King)"
    if fear > 70: return "유리멘탈 (Panic Seller)"
    
    if resilience >= 80 and discipline >= 70 and greed <= 40 and fear <= 40:
        return "전략가 (Master Tactician)"
    
    if greed > 50 and fear > 50: return "뇌동매매 (Impulsive)"
    if greed < 30 and fear > 60: return "소심한 개미 (Timid)"
    
    return "평범한 투자자 (Average Joe)"

# ---------------------------------------------------------
# 3. 메인 분석 루프
# ---------------------------------------------------------
def main():
    # 파일 목록 가져오기
    files = glob.glob(INPUT_PATTERN)
    if not files:
        print(f"❌ '{INPUT_PATTERN}' 패턴과 일치하는 파일이 없습니다.")
        return

    print(f"🔍 총 {len(files)}개의 파일을 발견했습니다. 분석을 시작합니다...")
    print("-" * 60)

    results = []

    for i, file_path in enumerate(files):
        filename = os.path.basename(file_path)
        print(f"[{i+1}/{len(files)}] Analyzing {filename}...", end=" ", flush=True)

        try:
            # 1. CSV 파일 읽기 및 전송
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'text/csv')}
                response = requests.post(API_URL, files=files)

            if response.status_code == 200:
                data = response.json()
                metrics = data['metrics']
                
                # 2. 데이터 추출
                truth_score = metrics['truth_score']
                
                # 편향 손실 합계 (Bias Loss Mapping 또는 Bias Free Metrics 사용)
                bias_loss = 0
                if data.get('bias_loss_mapping'):
                    m = data['bias_loss_mapping']
                    bias_loss = (m.get('fomo_loss', 0) + m.get('panic_loss', 0) + 
                                 m.get('revenge_loss', 0) + m.get('disposition_loss', 0))
                
                # 3. 페르소나 분류
                persona = classify_persona(metrics)

                # 결과 저장
                results.append({
                    "Filename": filename,
                    "Persona": persona,
                    "Truth Score": truth_score,
                    "Bias Loss ($)": round(bias_loss, 2),
                    "Win Rate (%)": round(metrics['win_rate'] * 100, 1),
                    "Profit Factor": round(metrics['profit_factor'], 2)
                })
                print("✅ 완료")
            else:
                print(f"❌ 실패 (Status: {response.status_code})")
                print(response.text)

        except Exception as e:
            print(f"❌ 에러: {str(e)}")
        
        # API 호출 간격 (서버 부하 방지)
        time.sleep(0.5)

    # ---------------------------------------------------------
    # 4. 결과 저장
    # ---------------------------------------------------------
    if results:
        df_results = pd.DataFrame(results)
        # 점수 순으로 정렬
        df_results = df_results.sort_values("Truth Score", ascending=False)
        
        df_results.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print("-" * 60)
        print(f"🎉 분석 완료! 결과가 '{OUTPUT_FILE}'에 저장되었습니다.")
        print("\n[요약 미리보기]")
        print(df_results[['Filename', 'Persona', 'Truth Score', 'Bias Loss ($)']].to_string(index=False))
    else:
        print("저장할 결과가 없습니다.")

if __name__ == "__main__":
    main()