from fastapi import APIRouter, UploadFile, HTTPException
import pandas as pd
import io
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from app.models import AnalysisResponse, EnrichedTrade, BehavioralMetrics, PersonalBaseline, BiasLossMapping, BiasPriority, BehaviorShift, EquityCurvePoint
from app.services.market import fetch_market_data_cached, calculate_metrics, detect_market_regime
from app.services.patterns import extract_deep_patterns

router = APIRouter()

def calculate_regime_weight(
    market_regime: str, 
    fomo_score: float, 
    panic_score: float
) -> float:
    """
    Regime Weight 계산 공식 (MVP 안전성 우선)
    
    Args:
        market_regime: 'BULL', 'BEAR', 'SIDEWAYS', 'UNKNOWN'
        fomo_score: FOMO 점수 (0.0 ~ 1.0, -1은 무효)
        panic_score: Panic 점수 (0.0 ~ 1.0, -1은 무효)
    
    Returns:
        regime_weight: 0.8, 1.0, 또는 1.5
    """
    # FOMO Buy 판단: fomo_score >= 0.7
    is_fomo_buy = fomo_score != -1 and fomo_score >= 0.7
    
    # Panic Sell 판단: panic_score != -1 and panic_score <= 0.3
    is_panic_sell = panic_score != -1 and panic_score <= 0.3
    
    if market_regime == 'BULL':
        if is_panic_sell:
            return 1.5  # 최대 페널티: 상승장에서 공포 매도
        elif is_fomo_buy:
            return 0.8  # 완화: 상승장 매수는 때로 합리적
        else:
            return 1.0  # 표준
    
    elif market_regime == 'BEAR':
        if is_fomo_buy:
            return 1.5  # 최대 페널티: 하락장 반등 추격 매수
        elif is_panic_sell:
            return 1.0  # 하락장에서 파는 것은 불가피성 있음
        else:
            return 1.0  # 표준
    
    else:  # SIDEWAYS, UNKNOWN
        return 1.0  # 표준 (맥락 불명확)

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_trades(file: UploadFile):
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        
        required = {'ticker', 'entry_date', 'entry_price', 'exit_date', 'exit_price'}
        if not required.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required}")
            
        if 'qty' not in df.columns:
            df['qty'] = 1
            
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid CSV format")

    unique_ticker_ranges = {}
    for _, row in df.iterrows():
        ticker = str(row['ticker'])
        # [시간 기능 추가] API 호출 및 캐싱 시에는 날짜(YYYY-MM-DD)만 사용
        try:
            entry_date_key = pd.to_datetime(row['entry_date']).strftime("%Y-%m-%d")
            exit_date_key = pd.to_datetime(row['exit_date']).strftime("%Y-%m-%d")
        except:
            entry_date_key = str(row['entry_date'])
            exit_date_key = str(row['exit_date'])
            
        key = (ticker, entry_date_key, exit_date_key)
        if key not in unique_ticker_ranges:
            unique_ticker_ranges[key] = fetch_market_data_cached(ticker, entry_date_key, exit_date_key)
    
    enriched_trades = []
    for _, row in df.iterrows():
        ticker = str(row['ticker'])
        entry_date_full = str(row['entry_date']) # 시간 포함 원본
        exit_date_full = str(row['exit_date'])   # 시간 포함 원본
        
        # 시장 데이터 조회용 키
        try:
            entry_date_key = pd.to_datetime(entry_date_full).strftime("%Y-%m-%d")
            exit_date_key = pd.to_datetime(exit_date_full).strftime("%Y-%m-%d")
        except:
            entry_date_key = entry_date_full
            exit_date_key = exit_date_full

        market_df = unique_ticker_ranges.get((ticker, entry_date_key, exit_date_key))
        
        metrics = {
            "fomo_score": -1.0, "panic_score": -1.0, 
            "fomo_score_base": -1.0, "panic_score_base": -1.0,
            "volume_weight_entry": 1.0, "volume_weight_exit": 1.0,
            "mae": 0.0, "mfe": 0.0,
            "efficiency": 0.0, "regret": 0.0, 
            "entry_day_high": 0.0, "entry_day_low": 0.0,
            "exit_day_high": 0.0, "exit_day_low": 0.0
        }
        
        if market_df is not None:
            metrics = calculate_metrics(row, market_df)
            
        pnl = (row['exit_price'] - row['entry_price']) * row['qty']
        ret_pct = (row['exit_price'] - row['entry_price']) / row['entry_price']
        
        # [시간 기능 추가] Duration 계산 시 시간까지 고려
        d1 = pd.to_datetime(entry_date_full)
        d2 = pd.to_datetime(exit_date_full)
        duration = max(0, (d2 - d1).days) # 소수점 일수 필요시 .total_seconds() / 86400 사용 가능
        
        market_regime = detect_market_regime(ticker, entry_date_key, market_df)
        
        enriched_trades.append({
            "id": f"{ticker}-{entry_date_full}",
            "ticker": ticker,
            "entry_date": entry_date_full,
            "entry_price": row['entry_price'],
            "exit_date": exit_date_full,
            "exit_price": row['exit_price'],
            "qty": row['qty'],
            "pnl": pnl,
            "return_pct": ret_pct,
            "duration_days": duration,
            "market_regime": market_regime,
            "is_revenge": False,
            **metrics
        })
        
    trades_df = pd.DataFrame(enriched_trades)
    
    # 시간순 정렬 (시/분/초 포함)
    trades_df['entry_dt'] = pd.to_datetime(trades_df['entry_date'])
    trades_df['exit_dt'] = pd.to_datetime(trades_df['exit_date'])
    trades_df = trades_df.sort_values('entry_dt')
    
    revenge_count = 0
    for i in range(1, len(trades_df)):
        curr = trades_df.iloc[i]
        prev_candidates = trades_df.iloc[:i]
        same_ticker = prev_candidates[prev_candidates['ticker'] == curr['ticker']]
        
        is_revenge = False
        for _, prev in same_ticker.iterrows():
            if prev['pnl'] < 0:
                # [시간 기능 추가] 정밀한 24시간 이내 재진입 체크
                time_diff = (curr['entry_dt'] - prev['exit_dt']).total_seconds() / 3600
                if 0 <= time_diff <= 24:
                    is_revenge = True
                    break
        
        if is_revenge:
            trades_df.at[trades_df.index[i], 'is_revenge'] = True
            revenge_count += 1
            
    total_trades = len(trades_df)
    winners = trades_df[trades_df['pnl'] > 0]
    losers = trades_df[trades_df['pnl'] <= 0]
    
    win_rate = len(winners) / total_trades if total_trades > 0 else 0
    avg_win = winners['pnl'].mean() if not winners.empty else 0
    avg_loss = abs(losers['pnl'].mean()) if not losers.empty else 0
    profit_factor = (avg_win * len(winners)) / (avg_loss * len(losers)) if avg_loss > 0 else 0
    
    valid_fomo = trades_df[trades_df['fomo_score'] != -1]['fomo_score']
    fomo_index = valid_fomo.mean() if not valid_fomo.empty else 0
    
    # --- Panic Score with Market Regime Weighting ---
    weighted_panic_sum = 0
    valid_panic_count = 0
    
    for _, row in trades_df.iterrows():
        if row['panic_score'] != -1:
            score = row['panic_score']
            regime = row.get('market_regime', 'UNKNOWN')
            
            # 상승장(BULL)에서 저점 매도(Panic < 0.3)는 더 심각한 문제
            # 하락장(BEAR)은 공포가 당연하므로 일반 처벌
            if regime == 'BULL' and score < 0.3:  # 저점 매도인 경우만
                score = max(0.0, score * 0.67)  # 1/1.5 = 0.67 (더 낮은 점수 = 더 나쁨)
            # BEAR와 SIDEWAYS는 그대로 (1.0배)
            
            weighted_panic_sum += score
            valid_panic_count += 1
    
    weighted_panic_avg = weighted_panic_sum / valid_panic_count if valid_panic_count > 0 else 0
    panic_index = 1 - weighted_panic_avg  # 낮은 panic_score = 높은 panic_index
    
    # --- Disposition Ratio with Time Context ---
    avg_win_hold = winners['duration_days'].mean() if not winners.empty else 0
    avg_loss_hold = losers['duration_days'].mean() if not losers.empty else 0
    base_disposition_ratio = avg_loss_hold / avg_win_hold if avg_win_hold > 0 else 0
    
    # Time Context Weighting: 너무 짧은 시간 내 작은 수익 청산 패널티
    if not winners.empty:
        # 5분 이내(0.1일) + 2% 미만 수익 = 단기 쫄보 청산
        short_win_trades = winners[
            (winners['duration_days'] < 0.1) &  # 약 2.4시간 이내
            (winners['return_pct'] < 0.02)     # 2% 미만 수익
        ]
        if len(short_win_trades) > 0:
            short_win_ratio = len(short_win_trades) / len(winners)
            if short_win_ratio > 0.3:  # 30% 이상이면 문제
                # 단기 쫄보 청산 가중치 적용
                base_disposition_ratio *= (1 + short_win_ratio * 0.5)
    
    # 장기 보유 후 손절도 문제 (30일 이상 보유 후 손절)
    if not losers.empty:
        long_loss_trades = losers[losers['duration_days'] > 30]
        if len(long_loss_trades) > 0:
            long_loss_ratio = len(long_loss_trades) / len(losers)
            if long_loss_ratio > 0.2:  # 20% 이상이면 문제
                base_disposition_ratio *= (1 + long_loss_ratio * 0.3)
    
    disposition_ratio = base_disposition_ratio
    
    returns = trades_df['return_pct'].tolist()
    avg_return = np.mean(returns) if returns else 0.0
    
    std_dev = np.std(returns) if len(returns) > 1 else 0.0
    sharpe_ratio = (avg_return - 0.02/252) / std_dev if std_dev > 0 else 0.0
    
    downside_returns = [r for r in returns if r < 0]
    downside_dev = np.sqrt(np.mean([r**2 for r in downside_returns])) if downside_returns else 0.0
    sortino_ratio = avg_return / downside_dev if downside_dev > 0 else 0.0
    
    alpha = 0.0
    try:
        if len(trades_df) > 0:
            min_date = trades_df['entry_dt'].min()
            max_date = trades_df['exit_dt'].max()
            spy_start = (min_date - timedelta(days=10)).strftime("%Y-%m-%d")
            spy_end = (max_date + timedelta(days=10)).strftime("%Y-%m-%d")
            
            spy_df = yf.download('SPY', start=spy_start, end=spy_end, progress=False)
            if not spy_df.empty:
                if isinstance(spy_df.columns, pd.MultiIndex):
                    spy_df.columns = spy_df.columns.get_level_values(0)
                
                spy_start_price = spy_df.iloc[0]['Close']
                spy_end_price = spy_df.iloc[-1]['Close']
                spy_return = (spy_end_price - spy_start_price) / spy_start_price
                
                portfolio_return = avg_return * len(trades_df)
                alpha = portfolio_return - spy_return
    except Exception as e:
        alpha = avg_return
    
    luck_percentile = 50.0
    is_low_sample = total_trades < 5
    if not is_low_sample and len(trades_df) > 0:
        simulations = 1000
        realized_total_pnl = trades_df['pnl'].sum()
        
        # 실제 통계 계산
        winners_df = trades_df[trades_df['pnl'] > 0]
        losers_df = trades_df[trades_df['pnl'] <= 0]
        win_rate = len(winners_df) / len(trades_df) if len(trades_df) > 0 else 0
        
        # 실제 PnL 분포
        win_pnls = winners_df['pnl'].tolist()
        loss_pnls = losers_df['pnl'].abs().tolist()
        
        better_outcomes = 0
        simulation_results = []
        
        np.random.seed(42)
        for _ in range(simulations):
            sim_total = 0
            
            # 실제 승률을 유지하면서 실제 PnL 분포에서 샘플링
            for _ in range(total_trades):
                if np.random.random() < win_rate:
                    # 승리: 실제 승리 PnL 중 랜덤 선택
                    if len(win_pnls) > 0:
                        sim_total += np.random.choice(win_pnls)
                else:
                    # 패배: 실제 손실 PnL 중 랜덤 선택
                    if len(loss_pnls) > 0:
                        sim_total -= np.random.choice(loss_pnls)
            
            simulation_results.append(sim_total)
            if sim_total > realized_total_pnl:
                better_outcomes += 1
        
        # Percentile 계산
        luck_percentile = (better_outcomes / simulations) * 100
        
        # 추가: 시뮬레이션 결과의 분포를 보고 해석 개선
        if len(simulation_results) > 0:
            simulation_results.sort()
            p25 = simulation_results[int(simulations * 0.25)]
            p75 = simulation_results[int(simulations * 0.75)]
            
            # 실제 성과가 분위수보다 얼마나 다른지
            if realized_total_pnl > p75:
                # 상위 25%에 속함 = 운이 좋음
                luck_percentile = max(0, luck_percentile - 5)
            elif realized_total_pnl < p25:
                # 하위 25%에 속함 = 운이 나쁨
                luck_percentile = min(100, luck_percentile + 5)
    
    # --- Truth Score Calculation (Market Regime Weighted) ---
    weighted_fomo_sum = 0
    valid_fomo_count = 0
    
    for _, row in trades_df.iterrows():
        if row['fomo_score'] != -1:
            score = row['fomo_score']
            regime = row.get('market_regime', 'UNKNOWN')
            
            if regime == 'BEAR':
                score *= 1.5
            elif regime == 'BULL':
                score *= 0.8
                
            weighted_fomo_sum += score
            valid_fomo_count += 1
            
    weighted_fomo_index = weighted_fomo_sum / valid_fomo_count if valid_fomo_count > 0 else 0
    
    base_score = 50
    base_score += (win_rate * 20)
    base_score -= (weighted_fomo_index * 20) 
    base_score -= ((1 - panic_index) * 20) 
    base_score -= max(0, (disposition_ratio - 1) * 10)
    base_score -= (revenge_count * 5)
    if not is_low_sample:
        base_score += (sharpe_ratio * 5)
    else:
        base_score += 5
    
    truth_score = int(max(0, min(100, base_score)))
    
    personal_baseline = None
    if total_trades >= 3:
        valid_mae = trades_df[trades_df['mae'] != 0]['mae']
        avg_mae = valid_mae.mean() if not valid_mae.empty else 0
        
        personal_baseline = PersonalBaseline(
            avg_fomo=fomo_index,
            avg_panic=panic_index,
            avg_mae=abs(avg_mae) if avg_mae < 0 else 0,
            avg_disposition_ratio=disposition_ratio,
            avg_revenge_count=revenge_count / total_trades if total_trades > 0 else 0
        )
    
    bias_loss_mapping = None
    if total_trades > 0:
        high_fomo_trades = trades_df[(trades_df['fomo_score'] > 0.7) & (trades_df['fomo_score'] != -1)]
        fomo_loss = abs(high_fomo_trades[high_fomo_trades['pnl'] < 0]['pnl'].sum()) if not high_fomo_trades.empty else 0
        
        low_panic_trades = trades_df[(trades_df['panic_score'] < 0.3) & (trades_df['panic_score'] != -1)]
        panic_loss = abs(low_panic_trades[low_panic_trades['pnl'] < 0]['pnl'].sum()) if not low_panic_trades.empty else 0
        
        revenge_trades = trades_df[trades_df['is_revenge'] == True]
        revenge_loss = abs(revenge_trades[revenge_trades['pnl'] < 0]['pnl'].sum()) if not revenge_trades.empty else 0
        
        winners_with_regret = trades_df[(trades_df['pnl'] > 0) & (trades_df['regret'] > 0)]
        disposition_loss = winners_with_regret['regret'].sum() if not winners_with_regret.empty else 0
        
        bias_loss_mapping = BiasLossMapping(
            fomo_loss=float(fomo_loss),
            panic_loss=float(panic_loss),
            revenge_loss=float(revenge_loss),
            disposition_loss=float(disposition_loss)
        )
    
    bias_priority = None
    if bias_loss_mapping:
        priorities = []
        
        high_fomo_count = len(trades_df[(trades_df['fomo_score'] > 0.7) & (trades_df['fomo_score'] != -1)])
        fomo_frequency = high_fomo_count / total_trades if total_trades > 0 else 0
        fomo_severity = min(1.0, fomo_index / 0.8) if fomo_index > 0 else 0
        if bias_loss_mapping.fomo_loss > 0 or fomo_frequency > 0.3:
            priorities.append(BiasPriority(
                bias='FOMO',
                priority=0,
                financial_loss=bias_loss_mapping.fomo_loss,
                frequency=fomo_frequency,
                severity=fomo_severity
            ))
        
        low_panic_count = len(trades_df[(trades_df['panic_score'] < 0.3) & (trades_df['panic_score'] != -1)])
        panic_frequency = low_panic_count / total_trades if total_trades > 0 else 0
        panic_severity = min(1.0, (1 - panic_index) / 0.8) if panic_index < 1 else 0
        if bias_loss_mapping.panic_loss > 0 or panic_frequency > 0.3:
            priorities.append(BiasPriority(
                bias='Panic Sell',
                priority=0,
                financial_loss=bias_loss_mapping.panic_loss,
                frequency=panic_frequency,
                severity=panic_severity
            ))
        
        revenge_frequency = revenge_count / total_trades if total_trades > 0 else 0
        revenge_severity = min(1.0, revenge_count / 3.0) if revenge_count > 0 else 0
        if bias_loss_mapping.revenge_loss > 0 or revenge_count > 0:
            priorities.append(BiasPriority(
                bias='Revenge Trading',
                priority=0,
                financial_loss=bias_loss_mapping.revenge_loss,
                frequency=revenge_frequency,
                severity=revenge_severity
            ))
        
        disposition_frequency = len(winners_with_regret) / len(winners) if not winners.empty else 0
        disposition_severity = min(1.0, (disposition_ratio - 1) / 1.5) if disposition_ratio > 1 else 0
        if bias_loss_mapping.disposition_loss > 0 or disposition_ratio > 1.2:
            priorities.append(BiasPriority(
                bias='Disposition Effect',
                priority=0,
                financial_loss=bias_loss_mapping.disposition_loss,
                frequency=disposition_frequency,
                severity=disposition_severity
            ))
        
        # 정렬: 손실 중심이지만 빈도와 심각도도 합리적으로 반영
        # 공식: 손실($) * 10 + 빈도(%) * 30 + 심각도(%) * 20
        # 예시:
        # - $500 손실, 20% 빈도, 50% 심각도 = 5000 + 600 + 1000 = 6600점
        # - $100 손실, 50% 빈도, 80% 심각도 = 1000 + 1500 + 1600 = 4100점
        # → 손실이 큰 편향이 우선순위가 높음
        
        # 손실이 0이지만 빈도와 심각도가 매우 높은 경우도 고려
        def calculate_priority_score(p: BiasPriority) -> float:
            # 기본 점수: 손실 중심
            base_score = p.financial_loss * 10
            
            # 손실이 없거나 작을 때: 빈도와 심각도로 보완
            if p.financial_loss < 50:
                # 빈도와 심각도가 모두 높으면 잠재적 위험으로 간주
                if p.frequency > 0.5 and p.severity > 0.6:
                    base_score += (p.frequency * 100 * 20) + (p.severity * 100 * 15)
                else:
                    base_score += (p.frequency * 100 * 10) + (p.severity * 100 * 5)
            else:
                # 손실이 있을 때: 빈도와 심각도는 보조 지표
                base_score += (p.frequency * 100 * 20) + (p.severity * 100 * 10)
            
            return base_score
        
        priorities.sort(key=calculate_priority_score, reverse=True)
        for i, p in enumerate(priorities):
            p.priority = i + 1
        
        bias_priority = priorities if priorities else None
    
    behavior_shift = None
    if total_trades >= 6:
        recent_trades = trades_df.tail(3)
        baseline_trades = trades_df.head(max(1, total_trades - 3))
        shifts = []
        
        recent_fomo = recent_trades[recent_trades['fomo_score'] != -1]['fomo_score'].mean() if not recent_trades[recent_trades['fomo_score'] != -1].empty else 0
        baseline_fomo = baseline_trades[baseline_trades['fomo_score'] != -1]['fomo_score'].mean() if not baseline_trades[baseline_trades['fomo_score'] != -1].empty else 0
        if baseline_fomo > 0:
            fomo_change = ((recent_fomo - baseline_fomo) / baseline_fomo) * 100
            fomo_trend = 'IMPROVING' if fomo_change < -5 else 'WORSENING' if fomo_change > 5 else 'STABLE'
            shifts.append(BehaviorShift(
                bias='FOMO',
                recent_value=recent_fomo,
                baseline_value=baseline_fomo,
                change_percent=fomo_change,
                trend=fomo_trend
            ))
        
        recent_panic = recent_trades[recent_trades['panic_score'] != -1]['panic_score'].mean() if not recent_trades[recent_trades['panic_score'] != -1].empty else 0
        baseline_panic = baseline_trades[baseline_trades['panic_score'] != -1]['panic_score'].mean() if not baseline_trades[baseline_trades['panic_score'] != -1].empty else 0
        if baseline_panic > 0:
            panic_change = ((recent_panic - baseline_panic) / baseline_panic) * 100
            panic_trend = 'IMPROVING' if panic_change > 5 else 'WORSENING' if panic_change < -5 else 'STABLE'
            shifts.append(BehaviorShift(
                bias='Panic Sell',
                recent_value=recent_panic,
                baseline_value=baseline_panic,
                change_percent=panic_change,
                trend=panic_trend
            ))
        
        recent_revenge = len(recent_trades[recent_trades['is_revenge'] == True])
        baseline_revenge = len(baseline_trades[baseline_trades['is_revenge'] == True])
        baseline_revenge_rate = baseline_revenge / len(baseline_trades) if len(baseline_trades) > 0 else 0
        recent_revenge_rate = recent_revenge / len(recent_trades) if len(recent_trades) > 0 else 0
        if baseline_revenge_rate > 0 or recent_revenge_rate > 0:
            revenge_change = ((recent_revenge_rate - baseline_revenge_rate) / (baseline_revenge_rate + 0.01)) * 100
            revenge_trend = 'IMPROVING' if revenge_change < -10 else 'WORSENING' if revenge_change > 10 else 'STABLE'
            shifts.append(BehaviorShift(
                bias='Revenge Trading',
                recent_value=recent_revenge_rate,
                baseline_value=baseline_revenge_rate,
                change_percent=revenge_change,
                trend=revenge_trend
            ))
        
        recent_winners = recent_trades[recent_trades['pnl'] > 0]
        recent_losers = recent_trades[recent_trades['pnl'] <= 0]
        baseline_winners = baseline_trades[baseline_trades['pnl'] > 0]
        baseline_losers = baseline_trades[baseline_trades['pnl'] <= 0]
        
        recent_disposition = (recent_losers['duration_days'].mean() / recent_winners['duration_days'].mean()) if (not recent_winners.empty and not recent_losers.empty and recent_winners['duration_days'].mean() > 0) else 0
        baseline_disposition = (baseline_losers['duration_days'].mean() / baseline_winners['duration_days'].mean()) if (not baseline_winners.empty and not baseline_losers.empty and baseline_winners['duration_days'].mean() > 0) else 0
        
        if baseline_disposition > 0 and recent_disposition > 0:
            disposition_change = ((recent_disposition - baseline_disposition) / baseline_disposition) * 100
            disposition_trend = 'IMPROVING' if disposition_change < -10 else 'WORSENING' if disposition_change > 10 else 'STABLE'
            shifts.append(BehaviorShift(
                bias='Disposition Effect',
                recent_value=recent_disposition,
                baseline_value=baseline_disposition,
                change_percent=disposition_change,
                trend=disposition_trend
            ))
        
        behavior_shift = shifts if shifts else None
    
    trades_df_sorted = trades_df.sort_values('entry_dt')
    trades_df_sorted['cumulative_pnl'] = trades_df_sorted['pnl'].cumsum()
    
    equity_curve = []
    for _, row in trades_df_sorted.iterrows():
        equity_curve.append(EquityCurvePoint(
            date=row['entry_date'],
            cumulative_pnl=float(row['cumulative_pnl']),
            fomo_score=float(row['fomo_score']) if row['fomo_score'] != -1 else None,
            panic_score=float(row['panic_score']) if row['panic_score'] != -1 else None,
            is_revenge=bool(row['is_revenge']),
            ticker=row['ticker'],
            pnl=float(row['pnl']),
            trade_id=row['id'],  # 클릭 인터랙션용
            base_score=row.get('base_score'),
            volume_weight=row.get('volume_weight'),
            regime_weight=row.get('regime_weight'),
            contextual_score=row.get('contextual_score'),
            market_regime=row.get('market_regime', 'UNKNOWN')
        ))
    
    metrics_obj = BehavioralMetrics(
        total_trades=total_trades,
        win_rate=win_rate,
        profit_factor=profit_factor,
        fomo_score=fomo_index,
        panic_score=panic_index,
        disposition_ratio=disposition_ratio,
        revenge_trading_count=revenge_count,
        truth_score=truth_score,
        sharpe_ratio=float(sharpe_ratio),
        sortino_ratio=float(sortino_ratio),
        alpha=float(alpha),
        luck_percentile=float(luck_percentile)
    )
    
    # --- Contextual Score 분해 필드 계산 (조건부 부착) ---
    for idx, row in trades_df.iterrows():
        fomo_score = row.get('fomo_score', -1.0)
        panic_score = row.get('panic_score', -1.0)
        is_revenge = row.get('is_revenge', False)
        market_regime = row.get('market_regime', 'UNKNOWN')
        
        # 분해 필드 부착 기준 (OR 조건)
        should_decompose = (
            (fomo_score != -1 and fomo_score >= 0.7) or  # Condition 1: High FOMO
            (panic_score != -1 and panic_score <= 0.3) or  # Condition 2: High Panic
            is_revenge  # Condition 3: Revenge Trading
        )
        
        if should_decompose:
            # Base Score 계산 (순수 심리 지표 기반, 0~100 스케일)
            fomo_base = row.get('fomo_score_base', fomo_score if fomo_score != -1 else 0.5)
            panic_base = row.get('panic_score_base', panic_score if panic_score != -1 else 0.5)
            
            # Base Score: 100점에서 FOMO와 Panic 페널티 차감
            base_score = 100.0
            if fomo_score != -1:
                base_score -= (fomo_base * 20)  # FOMO 페널티 (최대 20점)
            if panic_score != -1:
                base_score -= ((1 - panic_base) * 20)  # Panic 페널티 (최대 20점)
            base_score = max(0.0, min(100.0, base_score))
            
            # Volume Weight (진입/청산 중 더 나쁜 쪽 선택)
            vol_weight_entry = row.get('volume_weight_entry', 1.0)
            vol_weight_exit = row.get('volume_weight_exit', 1.0)
            volume_weight = max(vol_weight_entry, vol_weight_exit)  # 더 큰 가중치 사용
            
            # Regime Weight
            regime_weight = calculate_regime_weight(
                market_regime, 
                fomo_score, 
                panic_score
            )
            
            # Contextual Score (표시용, 0~150 clamp)
            contextual_score = base_score * volume_weight * regime_weight
            contextual_score = max(0.0, min(150.0, contextual_score))
            
            # 분해 필드 추가
            trades_df.at[idx, 'base_score'] = float(base_score)
            trades_df.at[idx, 'volume_weight'] = float(volume_weight)
            trades_df.at[idx, 'regime_weight'] = float(regime_weight)
            trades_df.at[idx, 'contextual_score'] = float(contextual_score)
        else:
            # 분해 필드 없음 (None)
            trades_df.at[idx, 'base_score'] = None
            trades_df.at[idx, 'volume_weight'] = None
            trades_df.at[idx, 'regime_weight'] = None
            trades_df.at[idx, 'contextual_score'] = None
    # --------------------------------------------------------
    
    final_trades = []
    for _, row in trades_df.iterrows():
        final_trades.append(EnrichedTrade(
            id=row['id'],
            ticker=row['ticker'],
            entry_date=row['entry_date'],
            entry_price=row['entry_price'],
            exit_date=row['exit_date'],
            exit_price=row['exit_price'],
            qty=row['qty'],
            pnl=row['pnl'],
            return_pct=row['return_pct'],
            duration_days=row['duration_days'],
            market_regime=row['market_regime'],
            is_revenge=row['is_revenge'],
            fomo_score=row['fomo_score'],
            panic_score=row['panic_score'],
            mae=row['mae'],
            mfe=row['mfe'],
            efficiency=row['efficiency'],
            regret=row['regret'],
            entry_day_high=row['entry_day_high'],
            entry_day_low=row['entry_day_low'],
            exit_day_high=row['exit_day_high'],
            exit_day_low=row['exit_day_low'],
            base_score=row.get('base_score'),
            volume_weight=row.get('volume_weight'),
            regime_weight=row.get('regime_weight'),
            contextual_score=row.get('contextual_score')
        ))

    deep_patterns = extract_deep_patterns(trades_df)
    
    return AnalysisResponse(
        trades=final_trades,
        metrics=metrics_obj,
        is_low_sample=total_trades < 5,
        personal_baseline=personal_baseline,
        bias_loss_mapping=bias_loss_mapping,
        bias_priority=bias_priority,
        behavior_shift=behavior_shift,
        equity_curve=equity_curve,
        deep_patterns=deep_patterns if deep_patterns else None
    )