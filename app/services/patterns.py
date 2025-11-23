import pandas as pd
import numpy as np
from typing import List, Optional
from datetime import datetime
from app.models import DeepPattern, BiasPriority, PersonalBaseline, PersonalPlaybook

def extract_deep_patterns(trades_df: pd.DataFrame) -> List[DeepPattern]:
    patterns = []
    
    if len(trades_df) < 3:
        return patterns
    
    # [시간 기능 추가] 시간 정보가 있으면 추출
    trades_df['entry_dt'] = pd.to_datetime(trades_df['entry_date'])
    trades_df['entry_hour'] = trades_df['entry_dt'].dt.hour
    
    # 1. MAE Time Cluster (시간 정보 활용)
    high_mae_trades = trades_df[trades_df['mae'] < -0.02]
    if len(high_mae_trades) >= 3:
        hour_distribution = high_mae_trades['entry_hour'].value_counts()
        if len(hour_distribution) > 0:
            peak_hour = hour_distribution.idxmax()
            peak_count = hour_distribution.max()
            peak_percentage = (peak_count / len(high_mae_trades)) * 100
            
            if peak_percentage >= 40:
                significance = 'HIGH' if peak_percentage >= 60 else 'MEDIUM'
                patterns.append(DeepPattern(
                    type='TIME_CLUSTER',
                    description=f"MAE가 큰 포지션({len(high_mae_trades)}건) 중 {peak_count}건({peak_percentage:.0f}%)이 {peak_hour}시에 발생",
                    significance=significance,
                    metadata={'hour': int(peak_hour), 'count': int(peak_count), 'total': len(high_mae_trades)}
                ))
    
    # 2. Price Cluster (Exit)
    valid_exits = trades_df[(trades_df['exit_day_high'] > 0) & (trades_df['panic_score'] != -1)]
    if len(valid_exits) >= 5:
        exit_ratios = valid_exits['exit_price'] / valid_exits['exit_day_high']
        avg_exit_ratio = exit_ratios.mean()
        
        if avg_exit_ratio < 0.95:
            exit_percentage = (1 - avg_exit_ratio) * 100
            patterns.append(DeepPattern(
                type='PRICE_CLUSTER',
                description=f"청산 타이밍은 평균적으로 당일 고가 대비 {exit_percentage:.1f}% 아래에서 발생",
                significance='HIGH' if exit_percentage > 5 else 'MEDIUM',
                metadata={'avg_exit_ratio': float(avg_exit_ratio), 'sample_size': len(valid_exits)}
            ))
    
    # 3. Revenge Sequence (시간 정보 활용: 시간 단위)
    revenge_trades = trades_df[trades_df['is_revenge'] == True]
    if len(revenge_trades) >= 2:
        revenge_sequences = []
        sorted_trades = trades_df.sort_values('entry_dt')
        
        for i in range(1, len(sorted_trades)):
            curr = sorted_trades.iloc[i]
            if curr['is_revenge']:
                prev_losses = sorted_trades.iloc[:i]
                prev_losses = prev_losses[prev_losses['pnl'] < 0]
                if len(prev_losses) > 0:
                    prev_loss = prev_losses.iloc[-1]
                    # [수정 완료] prev -> prev_loss 로 변경
                    time_diff = (curr['entry_dt'] - prev_loss['exit_dt']).total_seconds() / 3600
                    revenge_sequences.append(time_diff)
        
        if len(revenge_sequences) >= 2:
            avg_time = np.mean(revenge_sequences)
            if avg_time < 24:
                patterns.append(DeepPattern(
                    type='REVENGE_SEQUENCE',
                    description=f"손실 전환 직후 평균 {avg_time:.1f}시간 내 재매수하는 패턴이 {len(revenge_sequences)}회 반복",
                    significance='HIGH' if avg_time < 12 else 'MEDIUM',
                    metadata={'avg_hours': float(avg_time), 'count': len(revenge_sequences)}
                ))
    
    # 4. Market Regime FOMO
    if 'market_regime' in trades_df.columns:
        bull_trades = trades_df[trades_df['market_regime'] == 'BULL']
        bear_trades = trades_df[trades_df['market_regime'] == 'BEAR']
        
        if len(bull_trades) >= 3 and len(bear_trades) >= 3:
            bull_fomo = bull_trades[bull_trades['fomo_score'] > 0.7]['fomo_score']
            bear_fomo = bear_trades[bear_trades['fomo_score'] > 0.7]['fomo_score']
            
            bull_fomo_rate = len(bull_fomo) / len(bull_trades) if len(bull_trades) > 0 else 0
            bear_fomo_rate = len(bear_fomo) / len(bear_trades) if len(bear_trades) > 0 else 0
            
            if bull_fomo_rate > bear_fomo_rate * 1.5:
                patterns.append(DeepPattern(
                    type='MARKET_REGIME',
                    description=f"FOMO는 상승장에서만 생기는 경향 (상승장: {bull_fomo_rate*100:.0f}%, 하락장: {bear_fomo_rate*100:.0f}%)",
                    significance='HIGH' if bull_fomo_rate > 0.5 else 'MEDIUM',
                    metadata={'bull_fomo_rate': float(bull_fomo_rate), 'bear_fomo_rate': float(bear_fomo_rate)}
                ))
    
    # 4-1. Bull Regime Panic (상승장 공포 매도)
    if 'market_regime' in trades_df.columns:
        bull_trades = trades_df[trades_df['market_regime'] == 'BULL']
        bear_trades = trades_df[trades_df['market_regime'] == 'BEAR']
        
        if len(bull_trades) >= 3 and len(bear_trades) >= 3:
            bull_panic = bull_trades[(bull_trades['panic_score'] < 0.3) & (bull_trades['panic_score'] != -1)]
            bear_panic = bear_trades[(bear_trades['panic_score'] < 0.3) & (bear_trades['panic_score'] != -1)]
            
            bull_panic_rate = len(bull_panic) / len(bull_trades) if len(bull_trades) > 0 else 0
            bear_panic_rate = len(bear_panic) / len(bear_trades) if len(bear_trades) > 0 else 0
            
            # 상승장에서 공포 매도가 하락장보다 많거나 비슷하면 문제
            if bull_panic_rate >= bear_panic_rate * 0.8 and bull_panic_rate > 0.2:
                patterns.append(DeepPattern(
                    type='BULL_REGIME_PANIC',
                    description=f"상승장에서 공포 매도 패턴 (상승장: {bull_panic_rate*100:.0f}%, 하락장: {bear_panic_rate*100:.0f}%)",
                    significance='HIGH' if bull_panic_rate > 0.3 else 'MEDIUM',
                    metadata={'bull_panic_rate': float(bull_panic_rate), 'bear_panic_rate': float(bear_panic_rate), 'regime': 'BULL'}
                ))
    
    # 5. MAE Cluster
    if len(high_mae_trades) >= 5:
        avg_hold_time = high_mae_trades['duration_days'].mean()
        overall_avg_hold = trades_df['duration_days'].mean()
        
        if avg_hold_time > overall_avg_hold * 1.5:
            patterns.append(DeepPattern(
                type='MAE_CLUSTER',
                description=f"MAE가 큰 포지션({len(high_mae_trades)}건)은 평균 {avg_hold_time:.1f}일 보유 (전체 평균: {overall_avg_hold:.1f}일)",
                significance='MEDIUM',
                metadata={'avg_hold_days': float(avg_hold_time), 'overall_avg': float(overall_avg_hold)}
            ))
    
    # 6. Short-term Chicken Exit (단기 쫄보 청산)
    winners = trades_df[trades_df['pnl'] > 0]
    if len(winners) >= 3:
        # 5분 이내(0.1일) + 2% 미만 수익 = 단기 쫄보 청산
        short_win_trades = winners[
            (winners['duration_days'] < 0.1) &  # 약 2.4시간 이내
            (winners['return_pct'] < 0.02)     # 2% 미만 수익
        ]
        if len(short_win_trades) >= 2:
            short_win_rate = len(short_win_trades) / len(winners)
            if short_win_rate > 0.3:  # 30% 이상이면 문제
                patterns.append(DeepPattern(
                    type='SHORT_TERM_CHICKEN',
                    description=f"수익 거래 중 {len(short_win_trades)}건({short_win_rate*100:.0f}%)이 2시간 이내 2% 미만 수익으로 청산",
                    significance='HIGH' if short_win_rate > 0.5 else 'MEDIUM',
                    metadata={'short_win_count': len(short_win_trades), 'short_win_rate': float(short_win_rate), 'total_winners': len(winners)}
                ))
    
    # 7. Long-term Loss Hold (장기 손절)
    losers = trades_df[trades_df['pnl'] <= 0]
    if len(losers) >= 3:
        long_loss_trades = losers[losers['duration_days'] > 30]
        if len(long_loss_trades) >= 2:
            long_loss_rate = len(long_loss_trades) / len(losers)
            if long_loss_rate > 0.2:  # 20% 이상이면 문제
                avg_long_loss_days = long_loss_trades['duration_days'].mean()
                patterns.append(DeepPattern(
                    type='LONG_TERM_LOSS',
                    description=f"손실 거래 중 {len(long_loss_trades)}건({long_loss_rate*100:.0f}%)이 30일 이상 보유 후 손절 (평균 {avg_long_loss_days:.1f}일)",
                    significance='HIGH' if long_loss_rate > 0.3 else 'MEDIUM',
                    metadata={'long_loss_count': len(long_loss_trades), 'long_loss_rate': float(long_loss_rate), 'avg_days': float(avg_long_loss_days)}
                ))
    
    return patterns

def generate_personal_playbook(
    patterns: List[DeepPattern],
    bias_priority: Optional[List[BiasPriority]],
    personal_baseline: Optional[PersonalBaseline],
    trades_df: pd.DataFrame
) -> PersonalPlaybook:
    rules = []
    based_on_biases = []
    
    time_patterns = [p for p in patterns if p.type == 'TIME_CLUSTER']
    for tp in time_patterns:
        hour = tp.metadata.get('hour', 0) if tp.metadata else 0
        if 14 <= hour <= 15:
            rules.append("오후 2-3시에는 신규 진입을 금지한다")
        elif 9 <= hour <= 10:
            rules.append("장 초 첫 20분에는 매매하지 않는다")
    
    if bias_priority and len(bias_priority) > 0:
        primary_bias = bias_priority[0].bias
        if primary_bias == 'FOMO':
            if personal_baseline and personal_baseline.avg_fomo > 0.8:
                rules.append("장 초 첫 20분에는 매매하지 않는다 (FOMO 회피)")
            elif personal_baseline and personal_baseline.avg_fomo > 0.7:
                rules.append("고점 매수(FOMO)를 피하기 위해 진입 전 30분 대기")
            based_on_biases.append('FOMO')
    
    if personal_baseline and personal_baseline.avg_mae < -0.02:
        mae_percent = abs(personal_baseline.avg_mae) * 100
        rules.append(f"MAE가 {mae_percent:.0f}% 넘어가면 재진입 금지")
    
    mae_patterns = [p for p in patterns if p.type == 'MAE_CLUSTER']
    for mp in mae_patterns:
        if mp.metadata:
            avg_hold = mp.metadata.get('avg_hold_days', 0)
            if avg_hold > 3:
                rules.append(f"보유 기간이 {avg_hold:.0f}일을 넘으면 손절을 고려한다")
    
    price_patterns = [p for p in patterns if p.type == 'PRICE_CLUSTER']
    for pp in price_patterns:
        if pp.metadata:
            exit_ratio = pp.metadata.get('avg_exit_ratio', 1.0)
            if exit_ratio < 0.95:
                rules.append("당일 고가 기준 95% 이상 구간에서는 진입 금지")
    
    revenge_count = len(trades_df[trades_df['is_revenge'] == True])
    if revenge_count >= 2:
        rules.append("손실 거래 직후 24시간 내 재매수 금지")
        based_on_biases.append('Revenge Trading')
    
    revenge_patterns = [p for p in patterns if p.type == 'REVENGE_SEQUENCE']
    for rp in revenge_patterns:
        if rp.metadata:
            avg_hours = rp.metadata.get('avg_hours', 24)
            if avg_hours < 12:
                rules.append("손실 후 최소 12시간은 거래하지 않는다")
    
    if bias_priority:
        panic_bias = [b for b in bias_priority if b.bias == 'Panic Sell']
        if panic_bias and len(panic_bias) > 0:
            if personal_baseline and personal_baseline.avg_panic < 0.3:
                rules.append("저점 매도(Panic)를 피하기 위해 청산 전 10분 대기")
            based_on_biases.append('Panic Sell')
    
    if bias_priority:
        disp_bias = [b for b in bias_priority if b.bias == 'Disposition Effect']
        if disp_bias and len(disp_bias) > 0:
            if personal_baseline and personal_baseline.avg_disposition_ratio > 1.5:
                rules.append("손실 종목은 수익 종목보다 빠르게 청산한다")
            based_on_biases.append('Disposition Effect')
    
    market_patterns = [p for p in patterns if p.type == 'MARKET_REGIME']
    for mp in market_patterns:
        if mp.metadata:
            bull_fomo_rate = mp.metadata.get('bull_fomo_rate', 0)
            if bull_fomo_rate > 0.5:
                rules.append("상승장에서는 FOMO에 주의하며 진입 타이밍을 신중히 선택한다")
    
    if len(rules) == 0:
        rules.append("거래 전 잠시 멈추고 감정을 점검한다")
    
    return PersonalPlaybook(
        rules=rules,
        generated_at=datetime.now().isoformat(),
        based_on={
            'patterns': len(patterns),
            'biases': list(set(based_on_biases)) if based_on_biases else []
        }
    )