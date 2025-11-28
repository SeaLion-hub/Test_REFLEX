from fastapi import APIRouter, UploadFile, HTTPException
import pandas as pd
import io
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from app.models import AnalysisResponse, EnrichedTrade, BehavioralMetrics, PersonalBaseline, BiasLossMapping, BiasPriority, BehaviorShift, EquityCurvePoint, BiasFreeMetrics
from app.services.market import fetch_market_data_cached, calculate_metrics, detect_market_regime
from app.services.patterns import extract_deep_patterns

router = APIRouter()

# 거래 비용 상수 정의
DEFAULT_COMMISSION_RATE = 0.001  # 0.1% 기본 수수료율
DEFAULT_SLIPPAGE_RATE = 0.0005   # 0.05% 기본 슬리피지

# --- [핵심] JSON 직렬화 오류 방지를 위한 안전한 변환 함수 ---
def safe_float(value, default=0.0):
    """NaN, Inf를 0.0(또는 지정된 default)으로 변환하여 JSON 에러 방지"""
    if value is None:
        return default
    try:
        val = float(value)
        if np.isnan(val) or np.isinf(val):
            return default
        return val
    except:
        return default

def calculate_trading_cost(entry_price: float, exit_price: float, qty: float) -> float:
    trade_value = abs(entry_price * qty)
    commission = trade_value * DEFAULT_COMMISSION_RATE * 2
    slippage = trade_value * DEFAULT_SLIPPAGE_RATE * 2
    return safe_float(commission + slippage)

def calculate_opportunity_cost(trades_df: pd.DataFrame) -> tuple[float, float, float, float, bool]:
    try:
        if len(trades_df) == 0:
            return (0.0, 0.0, 0.0, 0.0, False)
        
        # 편향 거래 식별
        high_fomo = trades_df[(trades_df['fomo_score'] > 0.7) & (trades_df['fomo_score'] != -1) & (trades_df['pnl'] < 0)]
        low_panic = trades_df[(trades_df['panic_score'] < 0.3) & (trades_df['panic_score'] != -1) & (trades_df['pnl'] < 0)]
        revenge = trades_df[(trades_df['is_revenge'] == True) & (trades_df['pnl'] < 0)]
        
        biased_indices = set()
        biased_indices.update(high_fomo.index)
        biased_indices.update(low_panic.index)
        biased_indices.update(revenge.index)
        
        biased_trades_df = trades_df.loc[list(biased_indices)]
        
        if len(biased_trades_df) == 0:
            return (0.0, 0.0, 0.0, 0.0, False)
        
        biased_trades_pnl = biased_trades_df['pnl'].sum()
        total_bias_loss = abs(biased_trades_pnl)
        
        min_date = biased_trades_df['entry_dt'].min()
        max_date = biased_trades_df['exit_dt'].max()
        
        spy_start = (min_date - timedelta(days=5)).strftime("%Y-%m-%d")
        spy_end = (max_date + timedelta(days=5)).strftime("%Y-%m-%d")
        
        # [수정] auto_adjust=False로 일관성 유지
        spy_df = yf.download('SPY', start=spy_start, end=spy_end, progress=False, auto_adjust=False)
        if spy_df.empty:
            return (0.0, safe_float(biased_trades_pnl), 0.0, safe_float(total_bias_loss), True)
        
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        
        total_opportunity_cost = 0.0
        total_invested = 0.0
        
        for _, trade in biased_trades_df.iterrows():
            entry_dt = pd.to_datetime(trade['entry_dt']).normalize()
            exit_dt = pd.to_datetime(trade['exit_dt']).normalize()
            
            # 인덱스 찾기 안전장치
            try:
                if entry_dt not in spy_df.index:
                    entry_locs = spy_df.index.get_indexer([entry_dt], method='nearest')
                    if entry_locs[0] == -1: continue
                    entry_idx = entry_locs[0]
                else:
                    entry_idx = spy_df.index.get_loc(entry_dt)

                if exit_dt not in spy_df.index:
                    exit_locs = spy_df.index.get_indexer([exit_dt], method='nearest')
                    if exit_locs[0] == -1: continue
                    exit_idx = exit_locs[0]
                else:
                    exit_idx = spy_df.index.get_loc(exit_dt)
            except:
                continue
            
            invested_amount = abs(trade['entry_price'] * trade['qty'])
            
            try:
                entry_price_spy = safe_float(spy_df.iloc[entry_idx]['Close'])
                exit_price_spy = safe_float(spy_df.iloc[exit_idx]['Close'])
                
                spy_return_pct = (exit_price_spy - entry_price_spy) / entry_price_spy if entry_price_spy > 0 else 0.0
                user_return_pct = trade['return_pct'] if 'return_pct' in trade else 0.0
                
                return_diff_pct = spy_return_pct - user_return_pct
                opportunity_cost_for_trade = invested_amount * return_diff_pct
                
                total_opportunity_cost += opportunity_cost_for_trade
                total_invested += invested_amount
            except:
                continue
        
        spy_return_during_biased = 0.0
        opportunity_cost = 0.0
        
        if total_invested > 0:
            spy_return_during_biased = total_opportunity_cost / total_invested
            opportunity_cost = total_opportunity_cost
        
        biased_trades_cost = 0.0
        for _, trade in biased_trades_df.iterrows():
            trading_cost = calculate_trading_cost(trade['entry_price'], trade['exit_price'], trade['qty'])
            biased_trades_cost += trading_cost
        
        opportunity_cost_with_savings = opportunity_cost + biased_trades_cost
        
        return (
            safe_float(opportunity_cost_with_savings), 
            safe_float(biased_trades_pnl), 
            safe_float(spy_return_during_biased), 
            safe_float(total_bias_loss), 
            False
        )
        
    except Exception as e:
        print(f"Error calculating opportunity cost: {e}")
        return (0.0, 0.0, 0.0, 0.0, True)

def calculate_beta_and_jensens_alpha(
    trades_df: pd.DataFrame, 
    risk_free_rate: float = 0.02 / 252
) -> tuple[float, float, bool]:
    try:
        if len(trades_df) < 20:
            return (1.0, 0.0, False)
        
        min_date = trades_df['entry_dt'].min()
        max_date = trades_df['exit_dt'].max()
        duration_days = (max_date - min_date).days
        
        if duration_days < 60:
            return (1.0, 0.0, False)
        
        spy_start = (min_date - timedelta(days=10)).strftime("%Y-%m-%d")
        spy_end = (max_date + timedelta(days=10)).strftime("%Y-%m-%d")
        
        spy_df = yf.download('SPY', start=spy_start, end=spy_end, progress=False, auto_adjust=False)
        if spy_df.empty:
            return (1.0, 0.0, False)
        
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        
        portfolio_returns = []
        market_returns = []
        
        for _, trade in trades_df.iterrows():
            entry_dt = pd.to_datetime(trade['entry_dt']).normalize()
            exit_dt = pd.to_datetime(trade['exit_dt']).normalize()
            
            trade_days = pd.bdate_range(entry_dt, exit_dt)
            if len(trade_days) == 0:
                continue
            
            trade_return = safe_float(trade['return_pct'])
            if len(trade_days) > 0:
                daily_return = trade_return / len(trade_days)
            else:
                daily_return = 0
            
            for day in trade_days:
                if day in spy_df.index:
                    try:
                        spy_idx = spy_df.index.get_loc(day)
                        if spy_idx > 0:
                            spy_prev = safe_float(spy_df.iloc[spy_idx - 1]['Close'])
                            spy_curr = safe_float(spy_df.iloc[spy_idx]['Close'])
                            market_return = (spy_curr - spy_prev) / spy_prev if spy_prev > 0 else 0
                            
                            portfolio_returns.append(daily_return)
                            market_returns.append(market_return)
                    except:
                        continue
        
        if len(portfolio_returns) < 20:
            return (1.0, 0.0, False)
        
        portfolio_returns = np.array(portfolio_returns)
        market_returns = np.array(market_returns)
        
        valid_mask = ~np.isnan(portfolio_returns) & ~np.isnan(market_returns)
        portfolio_returns = portfolio_returns[valid_mask]
        market_returns = market_returns[valid_mask]

        if len(portfolio_returns) < 20:
             return (1.0, 0.0, False)

        covariance = np.cov(portfolio_returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        
        if market_variance == 0 or np.isnan(market_variance):
            return (1.0, 0.0, False)
        
        beta = covariance / market_variance
        
        portfolio_avg_return = np.mean(portfolio_returns)
        market_avg_return = np.mean(market_returns)
        
        expected_return = risk_free_rate + beta * (market_avg_return - risk_free_rate)
        jensens_alpha = portfolio_avg_return - expected_return
        jensens_alpha_annualized = jensens_alpha * 252
        
        return (safe_float(beta), safe_float(jensens_alpha_annualized), True)
        
    except Exception as e:
        print(f"Error calculating Beta: {e}")
        return (1.0, 0.0, False)

def calculate_regime_weight(market_regime: str, fomo_score: float, panic_score: float) -> float:
    is_fomo_buy = fomo_score != -1 and fomo_score >= 0.7
    is_panic_sell = panic_score != -1 and panic_score <= 0.3
    
    if market_regime == 'BULL':
        if is_panic_sell: return 1.5
        elif is_fomo_buy: return 0.8
        else: return 1.0
    elif market_regime == 'BEAR':
        if is_fomo_buy: return 1.5
        elif is_panic_sell: return 1.0
        else: return 1.0
    else:
        return 1.0

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
        entry_date_full = str(row['entry_date'])
        exit_date_full = str(row['exit_date'])
        
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
            raw_metrics = calculate_metrics(row, market_df)
            # [중요] 여기서 모든 메트릭을 안전하게 변환
            for k, v in raw_metrics.items():
                metrics[k] = safe_float(v)
        
        entry_price = safe_float(row['entry_price'])
        exit_price = safe_float(row['exit_price'])
        qty = safe_float(row['qty'])

        trading_cost = calculate_trading_cost(entry_price, exit_price, qty)
        pnl_gross = (exit_price - entry_price) * qty
        pnl = pnl_gross - trading_cost
        
        ret_pct = 0.0
        if entry_price != 0:
            ret_pct = (exit_price - entry_price) / entry_price
        
        d1 = pd.to_datetime(entry_date_full)
        d2 = pd.to_datetime(exit_date_full)
        duration = max(0, (d2 - d1).days)
        
        market_regime = detect_market_regime(ticker, entry_date_key, market_df)
        
        enriched_trades.append({
            "id": f"{ticker}-{entry_date_full}",
            "ticker": ticker,
            "entry_date": entry_date_full,
            "entry_price": entry_price,
            "exit_date": exit_date_full,
            "exit_price": exit_price,
            "qty": qty,
            "pnl": safe_float(pnl),
            "return_pct": safe_float(ret_pct),
            "duration_days": duration,
            "market_regime": market_regime,
            "is_revenge": False,
            **metrics
        })
        
    trades_df = pd.DataFrame(enriched_trades)
    
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
    
    win_rate = len(winners) / total_trades if total_trades > 0 else 0.0
    avg_win = winners['pnl'].mean() if not winners.empty else 0.0
    avg_loss = abs(losers['pnl'].mean()) if not losers.empty else 0.0
    profit_factor = (avg_win * len(winners)) / (avg_loss * len(losers)) if avg_loss > 0 else 0.0
    
    valid_fomo = trades_df[trades_df['fomo_score'] != -1]['fomo_score']
    fomo_index = valid_fomo.mean() if not valid_fomo.empty else 0.0
    
    weighted_panic_sum = 0
    valid_panic_count = 0
    for _, row in trades_df.iterrows():
        if row['panic_score'] != -1:
            score = row['panic_score']
            regime = row.get('market_regime', 'UNKNOWN')
            if regime == 'BULL' and score < 0.3:
                score = max(0.0, score * 0.67)
            weighted_panic_sum += score
            valid_panic_count += 1
    
    weighted_panic_avg = weighted_panic_sum / valid_panic_count if valid_panic_count > 0 else 0.0
    panic_index = 1.0 - weighted_panic_avg
    
    avg_win_hold = winners['duration_days'].mean() if not winners.empty else 0.0
    avg_loss_hold = losers['duration_days'].mean() if not losers.empty else 0.0
    base_disposition_ratio = avg_loss_hold / avg_win_hold if avg_win_hold > 0 else 0.0
    
    if not winners.empty:
        short_win_trades = winners[(winners['duration_days'] < 0.1) & (winners['return_pct'] < 0.02)]
        if len(short_win_trades) > 0:
            short_win_ratio = len(short_win_trades) / len(winners)
            if short_win_ratio > 0.3:
                base_disposition_ratio *= (1 + short_win_ratio * 0.5)
    
    if not losers.empty:
        long_loss_trades = losers[losers['duration_days'] > 30]
        if len(long_loss_trades) > 0:
            long_loss_ratio = len(long_loss_trades) / len(losers)
            if long_loss_ratio > 0.2:
                base_disposition_ratio *= (1 + long_loss_ratio * 0.3)
    
    disposition_ratio = base_disposition_ratio
    
    returns = trades_df['return_pct'].tolist()
    # [중요] returns 리스트의 각 항목도 안전하게 변환
    returns = [safe_float(r) for r in returns]
    
    avg_return = np.mean(returns) if returns else 0.0
    std_dev = np.std(returns) if len(returns) > 1 else 0.0
    
    sharpe_ratio = 0.0
    if std_dev > 0:
        sharpe_ratio = (avg_return - 0.02/252) / std_dev
    
    downside_returns = [r for r in returns if r < 0]
    downside_dev = np.sqrt(np.mean([r**2 for r in downside_returns])) if downside_returns else 0.0
    
    sortino_ratio = 0.0
    if downside_dev > 0:
        sortino_ratio = avg_return / downside_dev
    
    max_drawdown = 0.0
    if len(trades_df) > 0:
        trades_df_sorted_for_mdd = trades_df.sort_values('entry_dt').copy()
        trades_df_sorted_for_mdd['cumulative_pnl'] = trades_df_sorted_for_mdd['pnl'].cumsum()
        
        cumulative_pnls = [safe_float(x) for x in trades_df_sorted_for_mdd['cumulative_pnl'].tolist()]
        
        if len(cumulative_pnls) > 0:
            peak = cumulative_pnls[0]
            max_dd = 0.0
            for pnl in cumulative_pnls:
                if pnl > peak: peak = pnl
                if peak != 0:
                    drawdown = (peak - pnl) / abs(peak) if peak > 0 else 0.0
                else:
                    drawdown = 0.0
                if drawdown > max_dd: max_dd = drawdown
            max_drawdown = max_dd * 100
    
    alpha = 0.0
    try:
        beta, jensens_alpha, is_valid = calculate_beta_and_jensens_alpha(trades_df)
        if is_valid:
            alpha = jensens_alpha
        else:
            alpha = avg_return
    except:
        alpha = avg_return

    luck_percentile = 50.0
    if total_trades >= 5 and len(trades_df) > 0:
        simulations = 1000
        realized_total_pnl = trades_df['pnl'].sum()
        winners_df = trades_df[trades_df['pnl'] > 0]
        losers_df = trades_df[trades_df['pnl'] <= 0]
        sim_win_rate = len(winners_df) / len(trades_df) if len(trades_df) > 0 else 0
        
        win_pnls = winners_df['pnl'].tolist()
        loss_pnls = losers_df['pnl'].abs().tolist()
        
        better_outcomes = 0
        
        if win_pnls or loss_pnls:
            np.random.seed(42)
            for _ in range(simulations):
                sim_total = 0
                for _ in range(total_trades):
                    if np.random.random() < sim_win_rate:
                        if win_pnls: sim_total += np.random.choice(win_pnls)
                    else:
                        if loss_pnls: sim_total -= np.random.choice(loss_pnls)
                
                if sim_total > realized_total_pnl:
                    better_outcomes += 1
            
            luck_percentile = (better_outcomes / simulations) * 100

    total_regret = trades_df['regret'].sum() if 'regret' in trades_df else 0.0
    
    weighted_fomo_sum = 0
    valid_fomo_count = 0
    for _, row in trades_df.iterrows():
        if row['fomo_score'] != -1:
            score = row['fomo_score']
            regime = row.get('market_regime', 'UNKNOWN')
            if regime == 'BEAR': score *= 1.5
            elif regime == 'BULL': score *= 0.8
            weighted_fomo_sum += score
            valid_fomo_count += 1
            
    weighted_fomo_index = weighted_fomo_sum / valid_fomo_count if valid_fomo_count > 0 else 0.0
    
    base_score = 50.0
    base_score += (win_rate * 20)
    base_score -= (weighted_fomo_index * 20) 
    base_score -= ((1 - panic_index) * 20) 
    base_score -= max(0.0, (disposition_ratio - 1) * 10)
    base_score -= (revenge_count * 5)
    if total_trades >= 5:
        base_score += (sharpe_ratio * 5)
    else:
        base_score += 5
    
    truth_score = int(max(0, min(100, base_score)))
    
    personal_baseline = None
    if total_trades >= 3:
        valid_mae = trades_df[trades_df['mae'] != 0]['mae']
        avg_mae = valid_mae.mean() if not valid_mae.empty else 0.0
        
        personal_baseline = PersonalBaseline(
            avg_fomo=safe_float(fomo_index),
            avg_panic=safe_float(panic_index),
            avg_mae=safe_float(abs(avg_mae) if avg_mae < 0 else 0),
            avg_disposition_ratio=safe_float(disposition_ratio),
            avg_revenge_count=safe_float(revenge_count / total_trades if total_trades > 0 else 0)
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
            fomo_loss=safe_float(fomo_loss),
            panic_loss=safe_float(panic_loss),
            revenge_loss=safe_float(revenge_loss),
            disposition_loss=safe_float(disposition_loss)
        )
    
    bias_free_metrics = None
    if total_trades > 0:
        current_total_pnl = trades_df['pnl'].sum()
        total_bias_loss_from_mapping = (
            bias_loss_mapping.fomo_loss + 
            bias_loss_mapping.panic_loss + 
            bias_loss_mapping.revenge_loss + 
            bias_loss_mapping.disposition_loss
        ) if bias_loss_mapping else 0.0
        
        opportunity_cost, biased_trades_pnl, spy_return_rate, total_bias_loss, spy_load_failed_opportunity = calculate_opportunity_cost(trades_df)
        
        adjusted_pnl = current_total_pnl - biased_trades_pnl + opportunity_cost
        adjusted_improvement = adjusted_pnl - current_total_pnl
        
        bias_free_metrics = BiasFreeMetrics(
            current_pnl=safe_float(current_total_pnl),
            potential_pnl=safe_float(adjusted_pnl),
            bias_loss=safe_float(total_bias_loss_from_mapping),
            opportunity_cost=safe_float(opportunity_cost),
            adjusted_improvement=safe_float(adjusted_improvement)
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
                financial_loss=safe_float(bias_loss_mapping.fomo_loss),
                frequency=safe_float(fomo_frequency),
                severity=safe_float(fomo_severity)
            ))
        
        low_panic_count = len(trades_df[(trades_df['panic_score'] < 0.3) & (trades_df['panic_score'] != -1)])
        panic_frequency = low_panic_count / total_trades if total_trades > 0 else 0
        panic_severity = min(1.0, (1 - panic_index) / 0.8) if panic_index < 1 else 0
        if bias_loss_mapping.panic_loss > 0 or panic_frequency > 0.3:
            priorities.append(BiasPriority(
                bias='Panic Sell',
                priority=0,
                financial_loss=safe_float(bias_loss_mapping.panic_loss),
                frequency=safe_float(panic_frequency),
                severity=safe_float(panic_severity)
            ))
        
        revenge_frequency = revenge_count / total_trades if total_trades > 0 else 0
        revenge_severity = min(1.0, revenge_count / 3.0) if revenge_count > 0 else 0
        if bias_loss_mapping.revenge_loss > 0 or revenge_count > 0:
            priorities.append(BiasPriority(
                bias='Revenge Trading',
                priority=0,
                financial_loss=safe_float(bias_loss_mapping.revenge_loss),
                frequency=safe_float(revenge_frequency),
                severity=safe_float(revenge_severity)
            ))
        
        disposition_frequency = len(winners_with_regret) / len(winners) if not winners.empty else 0
        disposition_severity = min(1.0, (disposition_ratio - 1) / 1.5) if disposition_ratio > 1 else 0
        if bias_loss_mapping.disposition_loss > 0 or disposition_ratio > 1.2:
            priorities.append(BiasPriority(
                bias='Disposition Effect',
                priority=0,
                financial_loss=safe_float(bias_loss_mapping.disposition_loss),
                frequency=safe_float(disposition_frequency),
                severity=safe_float(disposition_severity)
            ))
        
        def calculate_priority_score(p: BiasPriority) -> float:
            base_score = p.financial_loss * 10
            if p.financial_loss < 50:
                if p.frequency > 0.5 and p.severity > 0.6:
                    base_score += (p.frequency * 100 * 20) + (p.severity * 100 * 15)
                else:
                    base_score += (p.frequency * 100 * 10) + (p.severity * 100 * 5)
            else:
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
        
        # Helper to safely calculate shift
        def calc_shift(recent, baseline, bias_name):
            if baseline > 0:
                change = ((recent - baseline) / baseline) * 100
                trend = 'IMPROVING' if change < -5 else 'WORSENING' if change > 5 else 'STABLE'
                
                if bias_name == 'Panic Sell':
                    trend = 'IMPROVING' if change > 5 else 'WORSENING' if change < -5 else 'STABLE'
                elif bias_name == 'Disposition Effect':
                    trend = 'IMPROVING' if change < -10 else 'WORSENING' if change > 10 else 'STABLE'
                else:
                    trend = 'IMPROVING' if change < -5 else 'WORSENING' if change > 5 else 'STABLE'

                shifts.append(BehaviorShift(
                    bias=bias_name,
                    recent_value=safe_float(recent),
                    baseline_value=safe_float(baseline),
                    change_percent=safe_float(change),
                    trend=trend
                ))

        # FOMO
        rec_fomo = recent_trades[recent_trades['fomo_score'] != -1]['fomo_score'].mean() if not recent_trades.empty else 0
        base_fomo = baseline_trades[baseline_trades['fomo_score'] != -1]['fomo_score'].mean() if not baseline_trades.empty else 0
        calc_shift(rec_fomo, base_fomo, 'FOMO')
        
        # Panic
        rec_panic = recent_trades[recent_trades['panic_score'] != -1]['panic_score'].mean() if not recent_trades.empty else 0
        base_panic = baseline_trades[baseline_trades['panic_score'] != -1]['panic_score'].mean() if not baseline_trades.empty else 0
        calc_shift(rec_panic, base_panic, 'Panic Sell')
        
        # Revenge
        rec_rev = len(recent_trades[recent_trades['is_revenge'] == True])
        base_rev = len(baseline_trades[baseline_trades['is_revenge'] == True])
        base_rev_rate = base_rev / len(baseline_trades) if len(baseline_trades) > 0 else 0
        rec_rev_rate = rec_rev / len(recent_trades) if len(recent_trades) > 0 else 0
        calc_shift(rec_rev_rate, base_rev_rate + 0.0001, 'Revenge Trading')
        
        # Disposition
        rec_winners = recent_trades[recent_trades['pnl'] > 0]
        rec_losers = recent_trades[recent_trades['pnl'] <= 0]
        rec_disp = 0
        if not rec_winners.empty and not rec_losers.empty:
            rec_disp = rec_losers['duration_days'].mean() / rec_winners['duration_days'].mean()
            
        base_winners = baseline_trades[baseline_trades['pnl'] > 0]
        base_losers = baseline_trades[baseline_trades['pnl'] <= 0]
        base_disp = 0
        if not base_winners.empty and not base_losers.empty:
            base_disp = base_losers['duration_days'].mean() / base_winners['duration_days'].mean()
            
        calc_shift(rec_disp, base_disp, 'Disposition Effect')
        
        behavior_shift = shifts if shifts else None
    
    trades_df_sorted = trades_df.sort_values('entry_dt')
    trades_df_sorted['cumulative_pnl'] = trades_df_sorted['pnl'].cumsum()
    
    benchmark_data = None
    benchmark_load_failed = False
    try:
        if len(trades_df_sorted) > 0:
            min_date = trades_df_sorted['entry_dt'].min()
            max_date = trades_df_sorted['exit_dt'].max()
            spy_start = (min_date - timedelta(days=5)).strftime("%Y-%m-%d")
            spy_end = (max_date + timedelta(days=5)).strftime("%Y-%m-%d")
            
            spy_df = yf.download('SPY', start=spy_start, end=spy_end, progress=False, auto_adjust=False)
            if spy_df.empty:
                benchmark_load_failed = True
            elif not spy_df.empty:
                if isinstance(spy_df.columns, pd.MultiIndex):
                    spy_df.columns = spy_df.columns.get_level_values(0)
                
                initial_spy_price = safe_float(spy_df.iloc[0]['Close'])
                initial_investment = abs(safe_float(trades_df_sorted.iloc[0]['entry_price']) * safe_float(trades_df_sorted.iloc[0]['qty']))
                
                benchmark_data = {}
                for idx, (_, row) in enumerate(trades_df_sorted.iterrows()):
                    entry_dt = pd.to_datetime(row['entry_dt']).normalize()
                    
                    if entry_dt in spy_df.index:
                        entry_idx = spy_df.index.get_loc(entry_dt)
                    else:
                        entry_locs = spy_df.index.get_indexer([entry_dt], method='nearest')
                        entry_idx = entry_locs[0] if entry_locs[0] != -1 else -1
                        
                    if entry_idx != -1 and entry_idx < len(spy_df):
                        current_spy_price = safe_float(spy_df.iloc[entry_idx]['Close'])
                        spy_return_pct = (current_spy_price - initial_spy_price) / initial_spy_price if initial_spy_price > 0 else 0.0
                        benchmark_data[row['id']] = safe_float(initial_investment * spy_return_pct)
    except Exception as e:
        print(f"Error calculating benchmark data: {e}")
        benchmark_load_failed = True
        benchmark_data = None
    
    equity_curve = []
    for _, row in trades_df_sorted.iterrows():
        benchmark_pnl = None
        if benchmark_data and row['id'] in benchmark_data:
            benchmark_pnl = benchmark_data[row['id']]
        
        equity_curve.append(EquityCurvePoint(
            date=row['entry_date'],
            cumulative_pnl=safe_float(row['cumulative_pnl']),
            fomo_score=safe_float(row['fomo_score']) if row['fomo_score'] != -1 else None,
            panic_score=safe_float(row['panic_score']) if row['panic_score'] != -1 else None,
            is_revenge=bool(row['is_revenge']),
            ticker=row['ticker'],
            pnl=safe_float(row['pnl']),
            trade_id=row['id'],
            base_score=safe_float(row.get('base_score')) if pd.notna(row.get('base_score')) else None,
            volume_weight=safe_float(row.get('volume_weight')) if pd.notna(row.get('volume_weight')) else None,
            regime_weight=safe_float(row.get('regime_weight')) if pd.notna(row.get('regime_weight')) else None,
            contextual_score=safe_float(row.get('contextual_score')) if pd.notna(row.get('contextual_score')) else None,
            market_regime=row.get('market_regime', 'UNKNOWN'),
            benchmark_cumulative_pnl=safe_float(benchmark_pnl) if benchmark_pnl is not None else None
        ))
    
    metrics_obj = BehavioralMetrics(
        total_trades=total_trades,
        win_rate=safe_float(win_rate),
        profit_factor=safe_float(profit_factor),
        fomo_score=safe_float(fomo_index),
        panic_score=safe_float(panic_index),
        disposition_ratio=safe_float(disposition_ratio),
        revenge_trading_count=revenge_count,
        truth_score=truth_score,
        sharpe_ratio=safe_float(sharpe_ratio),
        sortino_ratio=safe_float(sortino_ratio),
        alpha=safe_float(alpha),
        luck_percentile=safe_float(luck_percentile),
        max_drawdown=safe_float(max_drawdown)
    )
    
    for idx, row in trades_df.iterrows():
        fomo_score = row.get('fomo_score', -1.0)
        panic_score = row.get('panic_score', -1.0)
        is_revenge = row.get('is_revenge', False)
        
        should_decompose = (
            (fomo_score != -1 and fomo_score >= 0.7) or 
            (panic_score != -1 and panic_score <= 0.3) or 
            is_revenge
        )
        
        if should_decompose:
            fomo_base = row.get('fomo_score_base', fomo_score if fomo_score != -1 else 0.5)
            panic_base = row.get('panic_score_base', panic_score if panic_score != -1 else 0.5)
            
            base_score = 100.0
            if fomo_score != -1:
                base_score -= (fomo_base * 20)
            if panic_score != -1:
                base_score -= ((1 - panic_base) * 20)
            base_score = max(0.0, min(100.0, base_score))
            
            vol_weight_entry = row.get('volume_weight_entry', 1.0)
            vol_weight_exit = row.get('volume_weight_exit', 1.0)
            volume_weight = max(vol_weight_entry, vol_weight_exit)
            
            regime_weight = calculate_regime_weight(
                row.get('market_regime', 'UNKNOWN'), 
                fomo_score, 
                panic_score
            )
            
            contextual_score = base_score * volume_weight * regime_weight
            contextual_score = max(0.0, min(150.0, contextual_score))
            
            trades_df.at[idx, 'base_score'] = safe_float(base_score)
            trades_df.at[idx, 'volume_weight'] = safe_float(volume_weight)
            trades_df.at[idx, 'regime_weight'] = safe_float(regime_weight)
            trades_df.at[idx, 'contextual_score'] = safe_float(contextual_score)
        else:
            trades_df.at[idx, 'base_score'] = None
            trades_df.at[idx, 'volume_weight'] = None
            trades_df.at[idx, 'regime_weight'] = None
            trades_df.at[idx, 'contextual_score'] = None
    
    final_trades = []
    for _, row in trades_df.iterrows():
        final_trades.append(EnrichedTrade(
            id=row['id'],
            ticker=row['ticker'],
            entry_date=row['entry_date'],
            entry_price=safe_float(row['entry_price']),
            exit_date=row['exit_date'],
            exit_price=safe_float(row['exit_price']),
            qty=safe_float(row['qty']),
            pnl=safe_float(row['pnl']),
            return_pct=safe_float(row['return_pct']),
            duration_days=int(row['duration_days']),
            market_regime=row['market_regime'],
            is_revenge=bool(row['is_revenge']),
            fomo_score=safe_float(row['fomo_score']),
            panic_score=safe_float(row['panic_score']),
            mae=safe_float(row['mae']),
            mfe=safe_float(row['mfe']),
            efficiency=safe_float(row['efficiency']),
            regret=safe_float(row['regret']),
            entry_day_high=safe_float(row['entry_day_high']),
            entry_day_low=safe_float(row['entry_day_low']),
            exit_day_high=safe_float(row['exit_day_high']),
            exit_day_low=safe_float(row['exit_day_low']),
            base_score=safe_float(row.get('base_score')) if pd.notna(row.get('base_score')) else None,
            volume_weight=safe_float(row.get('volume_weight')) if pd.notna(row.get('volume_weight')) else None,
            regime_weight=safe_float(row.get('regime_weight')) if pd.notna(row.get('regime_weight')) else None,
            contextual_score=safe_float(row.get('contextual_score')) if pd.notna(row.get('contextual_score')) else None
        ))

    deep_patterns = extract_deep_patterns(trades_df)
    benchmark_load_failed_final = benchmark_load_failed or spy_load_failed_opportunity
    
    return AnalysisResponse(
        trades=final_trades,
        metrics=metrics_obj,
        is_low_sample=total_trades < 5,
        personal_baseline=personal_baseline,
        bias_loss_mapping=bias_loss_mapping,
        bias_free_metrics=bias_free_metrics,
        bias_priority=bias_priority,
        behavior_shift=behavior_shift,
        equity_curve=equity_curve,
        deep_patterns=deep_patterns if deep_patterns else None,
        benchmark_load_failed=benchmark_load_failed_final
    )