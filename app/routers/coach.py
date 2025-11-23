from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List

# 내부 모듈 임포트
from app.core.database import get_db
from app.orm import StrategyTag
from app.models import CoachRequest, DeepPattern, BiasPriority, PersonalBaseline, PersonalPlaybook, NewsVerification, NewsVerificationRequest
from app.services.rag import RAG_CARDS, RAG_EMBEDDINGS, get_embeddings_batch, cosine_similarity_top_k
from app.services.patterns import generate_personal_playbook
from app.services.news import fetch_news_context, validate_news_relevance

router = APIRouter()

@router.post("/coach")
async def get_ai_coach(request: CoachRequest):
    """
    OpenAI API를 호출하여 트레이딩 코칭 피드백을 생성합니다.
    모든 성과 지표(Win Rate, Profit Factor 등)를 종합하여 행동 편향과 연결합니다.
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY")
    
    if not api_key:
        return {
            "diagnosis": "API Key가 설정되지 않았습니다. 환경 변수를 확인해주세요.",
            "rule": "규칙 생성 불가",
            "bias": "N/A",
            "fix": "관리자에게 문의하세요."
        }
    
    openai = OpenAI(api_key=api_key)
    
    # 1. Primary Bias 식별 (camelCase/snake_case 모두 처리)
    primary_bias = None
    if request.bias_priority and len(request.bias_priority) > 0:
        first_item = request.bias_priority[0]
        primary_bias = first_item.get('bias') or first_item.get('Bias')
    
    # 2. RAG 검색 쿼리 생성
    query = ""
    if primary_bias:
        fomo_score = request.metrics.get('fomo_score') or request.metrics.get('fomoScore') or 0
        panic_score = request.metrics.get('panic_score') or request.metrics.get('panicScore') or 0
        
        if primary_bias == "FOMO":
            query = "FOMO extreme high entry chasing panic buying impulse" if fomo_score > 0.8 else "FOMO chasing high entry impulse fear of missing out"
        elif primary_bias == "Panic Sell":
            query = "Panic Sell extreme loss aversion selling low fear" if panic_score < 0.2 else "Panic Sell loss aversion selling low fear"
        elif primary_bias == "Revenge Trading":
            query = "Revenge Trading anger emotional recovery tilt overtrading"
        elif primary_bias == "Disposition Effect":
            query = "Disposition Effect holding losers selling winners too early"
        else:
            query = f"{primary_bias} trading psychology bias"
    else:
        win_rate_check = request.metrics.get('win_rate') or request.metrics.get('winRate') or 0
        query = "Winning psychology consistency discipline" if win_rate_check > 0.6 else "Trading psychology basics risk management"
    
    # 3. RAG 검색
    rag_context_text = ""
    retrieved_cards_for_response = []
    if RAG_CARDS and RAG_EMBEDDINGS is not None:
        try:
            filtered_indices = []
            if primary_bias:
                target_tags = []
                if primary_bias == "FOMO": target_tags = ["FOMO", "entry", "chasing"]
                elif primary_bias == "Panic Sell": target_tags = ["Panic Sell", "exit", "loss_aversion"]
                elif primary_bias == "Revenge Trading": target_tags = ["Revenge Trading", "revenge", "emotion"]
                elif primary_bias == "Disposition Effect": target_tags = ["Disposition Effect", "holding_loser"]
                
                for idx, card in enumerate(RAG_CARDS):
                    if any(t in card.get('tags', []) for t in target_tags):
                        filtered_indices.append(idx)
            if not filtered_indices: filtered_indices = list(range(len(RAG_CARDS)))
            
            query_embeddings = get_embeddings_batch([query], openai)
            if query_embeddings and len(query_embeddings) > 0:
                query_vec = np.array(query_embeddings[0])
                target_vecs = RAG_EMBEDDINGS[filtered_indices]
                threshold = 0.4 if primary_bias else 0.6
                local_indices, _ = cosine_similarity_top_k(query_vec, target_vecs, k=2, threshold=threshold)
                final_indices = [filtered_indices[i] for i in local_indices]
                retrieved_cards = [RAG_CARDS[i] for i in final_indices]
                
                if retrieved_cards:
                    rag_text_lines = [f"- PRINCIPLE: {c['title']}\n  DEFINITION: {c.get('definition', '')}\n  CONNECTION: {c.get('connection', '')}\n  PRESCRIPTION: {c.get('prescription', '')}" for c in retrieved_cards]
                    rag_context_text = f"RAG KNOWLEDGE BASE:\n{chr(10).join(rag_text_lines)}"
                    retrieved_cards_for_response = [{"title": c['title'], "definition": c.get('definition', ''), "connection": c.get('connection', ''), "prescription": c.get('prescription', '')} for c in retrieved_cards]
        except Exception as e:
            print(f"RAG Error: {e}")

    # 4. 프롬프트 데이터 준비
    top_regrets_str = [f"{t['ticker']} (Missed ${t.get('regret', 0):.0f})" for t in request.top_regrets]
    revenge_str = ', '.join([f"{t['ticker']} (-${abs(t.get('pnl', 0)):.0f})" for t in request.revenge_details]) if request.revenge_details else "None"
    
    # Metrics Formating (camelCase/snake_case 모두 처리)
    win_rate = request.metrics.get('win_rate') or request.metrics.get('winRate') or 0
    win_rate_pct = win_rate * 100
    profit_factor = request.metrics.get('profit_factor') or request.metrics.get('profitFactor') or 0
    sharpe = request.metrics.get('sharpe_ratio') or request.metrics.get('sharpeRatio') or 0
    sortino = request.metrics.get('sortino_ratio') or request.metrics.get('sortinoRatio') or 0
    
    personal_baseline_text = ''
    example_mae_pct = 0.0
    
    if request.personal_baseline:
        pb = request.personal_baseline
        avg_mae = pb.get('avg_mae') or pb.get('avgMae') or 0
        avg_mae_pct = avg_mae * 100
        example_mae_pct = avg_mae_pct
        personal_baseline_text = f"""
    PERSONAL BASELINE (History):
    - Avg FOMO: {(pb.get('avg_fomo') or pb.get('avgFomo') or 0)*100:.0f}% (Cur: {(request.metrics.get('fomo_score') or request.metrics.get('fomoScore') or 0)*100:.0f}%)
    - Avg Panic: {(pb.get('avg_panic') or pb.get('avgPanic') or 0)*100:.0f}% (Cur: {(request.metrics.get('panic_score') or request.metrics.get('panicScore') or 0)*100:.0f}%)
    """

    performance_text = f"""
    ADVANCED RISK METRICS (FACTS):
    - Win Rate: {win_rate_pct:.1f}%
    - Profit Factor: {profit_factor:.2f}
    - Avg MAE (Drawdown Risk): -{example_mae_pct:.1f}%
    - Sharpe Ratio: {sharpe:.2f}
    - Sortino Ratio: {sortino:.2f}
    - Revenge Trading Count: {request.metrics['revenge_trading_count']}
    """
    
    bias_loss_text = ''
    if request.bias_loss_mapping:
        blm = request.bias_loss_mapping
        bias_loss_text = f"""
    FINANCIAL IMPACT OF BIASES:
    - FOMO Loss: -${blm['fomo_loss']:.0f}
    - Panic Sell Loss: -${blm['panic_loss']:.0f}
    - Revenge Trading Loss: -${blm['revenge_loss']:.0f}
    - Disposition Effect (Missed): -${blm['disposition_loss']:.0f}
    """
    
    bias_priority_text = ''
    if request.bias_priority and len(request.bias_priority) > 0:
        # camelCase와 snake_case 모두 처리
        def get_financial_loss(p: dict) -> float:
            return p.get('financial_loss') or p.get('financialLoss') or 0.0
        def get_frequency(p: dict) -> float:
            return p.get('frequency') or 0.0
        def get_severity(p: dict) -> float:
            return p.get('severity') or 0.0
        
        # 우선순위 점수 계산 (사용자에게 보여주기 위해)
        def calculate_priority_score(p: dict) -> float:
            loss = get_financial_loss(p)
            freq = get_frequency(p)
            sev = get_severity(p)
            # analysis.py와 동일한 로직 사용
            base_score = loss * 10
            if loss < 50:
                if freq > 0.5 and sev > 0.6:
                    base_score += (freq * 100 * 20) + (sev * 100 * 15)
                else:
                    base_score += (freq * 100 * 10) + (sev * 100 * 5)
            else:
                base_score += (freq * 100 * 20) + (sev * 100 * 10)
            return base_score
        
        # 점수 순으로 정렬하여 표시
        sorted_biases = sorted(request.bias_priority, key=calculate_priority_score, reverse=True)
        
        bias_priority_text = f"""
    FIX PRIORITY (Ranked by Financial Impact):
    * 우선순위는 실제 금전적 손실을 최우선으로, 빈도와 심각도를 보조 지표로 산정되었습니다.
    {chr(10).join([f"    {i+1}. {p.get('bias', 'Unknown')}: -${get_financial_loss(p):.0f} 손실 | {get_frequency(p)*100:.0f}% 빈도 | {get_severity(p)*100:.0f}% 심각도" for i, p in enumerate(sorted_biases)])}
    """
    
    behavior_shift_text = ''
    if request.behavior_shift and len(request.behavior_shift) > 0:
        # camelCase와 snake_case 모두 처리
        def get_change_percent(s: dict) -> float:
            return s.get('change_percent') or s.get('changePercent') or 0.0
        def get_trend(s: dict) -> str:
            return s.get('trend') or 'STABLE'
        
        behavior_shift_lines = [
            f"    - {s.get('bias', 'Unknown')}: {get_trend(s)} ({get_change_percent(s):+.1f}%)" 
            for s in request.behavior_shift
        ]
        behavior_shift_text = f"""
    BEHAVIOR SHIFT (Recent 3 vs Baseline):
    {chr(10).join(behavior_shift_lines)}
    """
    
    total_regret = request.metrics.get('total_regret') or request.metrics.get('totalRegret') or 0
    
    best_executions_text = ''
    if request.best_executions:
        lines = [f"- {be['ticker']}: {be.get('execution_type')} - {be.get('reason')}" for be in request.best_executions]
        best_executions_text = f"BEST EXECUTIONS:\n{chr(10).join(lines)}"

    patterns_text = ''
    if request.patterns:
        lines = [f"- {p.get('description')}" for p in request.patterns]
        patterns_text = f"DETECTED PATTERNS:\n{chr(10).join(lines)}"

    deep_patterns_text = ''
    if request.deep_patterns:
        lines = [f"- [{dp.get('type')}] {dp.get('description')}" for dp in request.deep_patterns]
        deep_patterns_text = f"DEEP PATTERNS (AI Cluster):\n{chr(10).join(lines)}"

    # --- Behavioral Economics Context Extraction ---
    contextual_info = ""
    if request.deep_patterns:
        # 시장 상황별 패턴 추출
        bull_panic = [dp for dp in request.deep_patterns 
                      if 'BULL' in str(dp.get('metadata', {})).upper() or 
                         ('상승장' in str(dp.get('description', '')) and '공포' in str(dp.get('description', '')))]
        volume_spike = [dp for dp in request.deep_patterns 
                       if 'volume' in str(dp.get('description', '')).lower() or 
                          '거래량' in str(dp.get('description', '')) or
                          'VOLUME' in str(dp.get('type', '')).upper()]
        
        if bull_panic:
            contextual_info += f"\n- 상승장 공포 매도 패턴: {len(bull_panic)}건 감지\n"
        if volume_spike:
            contextual_info += f"\n- 거래량 폭발 시점 매매: {len(volume_spike)}건 감지\n"
    
    # Bias별 맥락 정보 추출
    bias_context = ""
    if request.bias_priority:
        for bias_item in request.bias_priority:
            bias_name = bias_item.get('bias', '')
            if bias_name == 'Panic Sell':
                # Panic Sell의 경우 시장 상황 정보 활용
                panic_freq = bias_item.get('frequency', 0) * 100
                bias_context += f"\n- Panic Sell 발생 빈도: {panic_freq:.0f}% (상승장에서 발생 시 더 심각)\n"
            elif bias_name == 'FOMO':
                fomo_freq = bias_item.get('frequency', 0) * 100
                bias_context += f"\n- FOMO 발생 빈도: {fomo_freq:.0f}% (거래량 폭발 시 더 심각)\n"
            elif bias_name == 'Disposition Effect':
                disp_freq = bias_item.get('frequency', 0) * 100
                bias_context += f"\n- Disposition Effect 발생 빈도: {disp_freq:.0f}% (단기 쫄보 청산 또는 장기 손절 패턴)\n"
    
    behavioral_context_text = f"""
    BEHAVIORAL ECONOMICS CONTEXT:
    {contextual_info}
    {bias_context}
    """

    # 5. 프롬프트 강화 (한국어 강제)
    prompt = f"""
    Act as the "Truth Pipeline" AI. You are an objective, data-driven Trading Coach.
    
    CRITICAL RULES (STRICTLY ENFORCED):
    - **LANGUAGE: ALL RESPONSES MUST BE IN KOREAN (한국어).**
    - EVIDENCE IS KING: Your diagnosis must be based 100% on the HARD EVIDENCE numbers below.
    - FACT-BASED REASONING: You MUST cite the specific number that led to your advice.
      * Bad: "리스크 관리를 더 잘해야 합니다."
      * Good: "평균 MAE가 -{example_mae_pct:.1f}%로 깊어, 손절 라인을 더 타이트하게 잡아야 합니다."
      * Good: "승률은 {win_rate_pct:.0f}%로 낮지만 손익비가 {profit_factor:.2f}로 높아 추세를 잘 타고 계십니다."
    - RAG IS QUEEN: Your advice (Rule/Fix) must be inspired by the RAG KNOWLEDGE BASE provided (if available).
    - SANDWICH FEEDBACK: Praise (Strengths) -> Criticize (Weaknesses) -> Encourage (Fix).
    - PROCESS EVALUATION: Focus on REPEATED PATTERNS, not single trades.
    - PERSONA: "Ruthless" is OUT. "Tough Love" is IN. "이것만 고치면 완벽해" style.
    
    USER PROFILE:
    - Mode: {"NOVICE" if request.is_low_sample else "EXPERIENCED"}
    
    KEY METRICS:
    1. TRUTH SCORE: {(request.metrics.get('truth_score') or request.metrics.get('truthScore') or 0)}/100
    2. BEHAVIOR: FOMO {(request.metrics.get('fomo_score') or request.metrics.get('fomoScore') or 0)*100:.0f}%, Panic {(request.metrics.get('panic_score') or request.metrics.get('panicScore') or 0)*100:.0f}%, Disposition {(request.metrics.get('disposition_ratio') or request.metrics.get('dispositionRatio') or 0):.1f}x
    
    {performance_text}
    {personal_baseline_text}
    {bias_loss_text}
    {bias_priority_text}
    {behavior_shift_text}
    {best_executions_text}
    {patterns_text}
    {deep_patterns_text}
    {behavioral_context_text}
    
    {rag_context_text}

    INSTRUCTIONS (INTELLIGENT DIAGNOSIS IN KOREAN):
    
    0. STRENGTHS (이달의 명장면):
       - **CRITICAL**: BEST EXECUTIONS가 제공되면 반드시 strengths 배열을 생성하세요.
       - 형식: [{{"ticker": "종목코드", "execution": "완벽한 진입/고점 매도/칼손절/완벽한 거래", "lesson": "칭찬 메시지 (1문장)", "reason": "구체적 이유"}}]
       - 예시: [{{"ticker": "AAPL", "execution": "완벽한 진입", "lesson": "FOMO 점수 5%로 저점 매수를 잘 잡으셨습니다. 이 타이밍 감각을 유지하세요.", "reason": "FOMO 점수 5%로 저점 매수"}}]
       - BEST EXECUTIONS가 없으면 strengths는 빈 배열 []로 반환하세요.
       - 최대 3개까지만 생성하세요.
    
    1. DIAGNOSIS (3 sentences, DATA-DRIVEN REASONING):
       - Sentence 1: **Analyze the User's Trading Health**. 
         Interpret the relationship between Performance Metrics (Win Rate, Profit Factor) and Risk Metrics (Sharpe Ratio, Sortino Ratio, MAE).
         * Requirement: Cite specific numbers in parentheses.
       - Sentence 2: Identify the **Root Cause** ({primary_bias}) of the issue. 
         **CRITICAL**: You MUST connect this bias to the BEHAVIORAL ECONOMICS CONTEXT above.
         * If Panic Sell in BULL market: Explain this is "Loss Aversion" bias causing "Capitulation" in a bull market, which is more dangerous than panic in bear markets.
         * If FOMO with volume spike: Explain this is "Herding Bias" or "FOMO" causing "Chasing" behavior during volume explosions.
         * If Disposition with short-term exits: Explain this is "Disposition Effect" with "Premature Profit Taking" (쫄보 청산).
         * Cite specific behavioral economics terms (Loss Aversion, Herding, Anchoring, Disposition Effect, etc.)
         * Explain *how* this bias degrades metrics, citing specific bias scores AND market context.
       - Sentence 3: State the **Financial Reality**. Mention the total financial loss from this bias and WHY the market context makes it worse.
    
    2. RULE: A short, memorable commandment (in Korean) that incorporates the behavioral bias context.
    3. BIAS: The primary bias name (Keep in English, e.g., FOMO, Panic Sell) followed by the behavioral economics term in parentheses, e.g., "Panic Sell (Loss Aversion)".
    4. FIX: Actionable advice based on RAG or Patterns (in Korean). Include specific strategies to overcome the identified behavioral bias in the given market context.
    
    5. ACTION PLAN (3A: RAG 기반 개인화된 행동 계획 생성):
       - **CRITICAL**: 가장 문제인 편향 1개와 그 근거가 된 수치 2~3개만 사용하여 생성합니다.
       - **STRUCTURE**: 반드시 plan_step_1, plan_step_2, plan_step_3의 3단계로만 생성합니다.
       - **NUMBER CITATION REQUIRED**: 각 계획 단계마다 반드시 지표 명칭과 숫자를 1회씩 인용해야 합니다.
         * 예시: "Panic score 0.25 (volume_weight 1.5 반영)를 고려하여..."
         * 예시: "fomo_score 0.85와 regime_weight 1.5가 결합된 상황에서는..."
         * 예시: "disposition_ratio 2.3이 감지되었으므로..."
       - **FORMAT**: 각 단계는 구체적이고 실행 가능한 행동 지침이어야 합니다.
       - **CONTEXT**: RAG KNOWLEDGE BASE의 처방(prescription)을 참고하되, 반드시 숫자를 인용합니다.
    
    Output JSON: {{ 
        "diagnosis": "...", 
        "rule": "...", 
        "bias": "...", 
        "fix": "...", 
        "strengths": [...],
        "plan_step_1": "... (숫자 인용 필수)",
        "plan_step_2": "... (숫자 인용 필수)",
        "plan_step_3": "... (숫자 인용 필수)"
    }}
    """
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data-driven trading coach. Always respond with valid JSON only. IMPORTANT: Respond in Korean."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        content = completion.choices[0].message.content
        result = json.loads(content)
        
        if retrieved_cards_for_response: result["references"] = retrieved_cards_for_response
        if "strengths" not in result: result["strengths"] = []
        
        # 이달의 명장면 Fallback: best_executions를 strengths로 변환
        if len(result.get("strengths", [])) == 0 and request.best_executions:
            execution_type_map = {
                "PERFECT_ENTRY": "완벽한 진입",
                "PERFECT_EXIT": "고점 매도",
                "CLEAN_CUT": "칼손절",
                "PERFECT_TRADE": "완벽한 거래"
            }
            
            lesson_map = {
                "PERFECT_ENTRY": "저점 매수 타이밍을 잘 잡으셨습니다. 이 원칙을 다른 종목에도 적용해보세요.",
                "PERFECT_EXIT": "고점 매도로 수익을 극대화하셨습니다. 이 판단력을 유지하세요.",
                "CLEAN_CUT": "빠른 손절로 큰 손실을 막았습니다. 이 훈련된 반사신경이 중요합니다.",
                "PERFECT_TRADE": "진입과 청산 모두 완벽했습니다. 이런 거래를 템플릿으로 삼으세요."
            }
            
            result["strengths"] = [
                {
                    "ticker": be.get("ticker", ""),
                    "execution": execution_type_map.get(be.get("execution_type", ""), "우수한 거래"),
                    "lesson": lesson_map.get(be.get("execution_type", ""), "잘한 매매입니다."),
                    "reason": be.get("reason", "")
                }
                for be in request.best_executions[:3]  # 최대 3개
            ]
        
        # 3A: PersonalPlaybook 생성 (LLM이 생성한 plan_step_1/2/3 사용)
        plan_step_1 = result.get("plan_step_1", "거래 전 잠시 멈추고 감정을 점검하십시오.")
        plan_step_2 = result.get("plan_step_2", "손절 라인을 명확히 설정하고 자동 주문을 활용하십시오.")
        plan_step_3 = result.get("plan_step_3", "매매일지를 작성하여 패턴을 분석하십시오.")
        
        # 가장 문제인 편향 추출 (숫자 인용을 위한 컨텍스트)
        primary_bias_info = {}
        if request.bias_priority and len(request.bias_priority) > 0:
            primary = request.bias_priority[0]
            primary_bias_info = {
                'bias': primary.get('bias') or primary.get('Bias') or '',
                'financial_loss': primary.get('financial_loss') or primary.get('financialLoss') or 0.0,
                'frequency': primary.get('frequency') or 0.0,
                'severity': primary.get('severity') or 0.0
            }
        
        # 숫자 인용이 없는 경우 강제 추가 (fallback)
        if not any(keyword in plan_step_1.lower() for keyword in ['score', 'weight', 'ratio', 'index', 'percentile', 'fomo', 'panic', 'disposition', 'regime', 'volume']):
            if primary_bias_info.get('bias') == 'FOMO':
                fomo_val = request.metrics.get('fomo_score') or request.metrics.get('fomoScore') or 0
                plan_step_1 = f"fomo_score {fomo_val*100:.0f}%를 고려하여 {plan_step_1}"
            elif primary_bias_info.get('bias') == 'Panic Sell':
                panic_val = request.metrics.get('panic_score') or request.metrics.get('panicScore') or 0
                plan_step_1 = f"panic_score {panic_val*100:.0f}%를 고려하여 {plan_step_1}"
        
        if not any(keyword in plan_step_2.lower() for keyword in ['score', 'weight', 'ratio', 'index', 'percentile', 'fomo', 'panic', 'disposition', 'regime', 'volume']):
            disp_ratio = request.metrics.get('disposition_ratio') or request.metrics.get('dispositionRatio') or 0
            if disp_ratio > 1.0:
                plan_step_2 = f"disposition_ratio {disp_ratio:.1f}x를 고려하여 {plan_step_2}"
            else:
                revenge_count = request.metrics.get('revenge_trading_count') or request.metrics.get('revengeTradingCount') or 0
                if revenge_count > 0:
                    plan_step_2 = f"revenge_trading_count {revenge_count}회를 고려하여 {plan_step_2}"
        
        if not any(keyword in plan_step_3.lower() for keyword in ['score', 'weight', 'ratio', 'index', 'percentile', 'fomo', 'panic', 'disposition', 'regime', 'volume']):
            truth_score_val = request.metrics.get('truth_score') or request.metrics.get('truthScore') or 0
            plan_step_3 = f"truth_score {truth_score_val}/100을 고려하여 {plan_step_3}"
        
        playbook = PersonalPlaybook(
            plan_step_1=plan_step_1,
            plan_step_2=plan_step_2,
            plan_step_3=plan_step_3,
            generated_at=datetime.now().isoformat(),
            based_on={
                'primary_bias': primary_bias_info.get('bias', ''),
                'patterns': len(request.deep_patterns) if request.deep_patterns else 0,
                'biases': [p.get('bias') or p.get('Bias') or '' for p in request.bias_priority] if request.bias_priority else []
            }
        )
        result["playbook"] = playbook.dict()
        
        return result
            
    except Exception as e:
        print(f"AI Coach Error: {e}")
        return {
            "diagnosis": "AI 분석을 사용할 수 없습니다.",
            "rule": "리스크 관리를 확인하세요.",
            "bias": "Service Error",
            "fix": "API 키나 네트워크 상태를 확인하세요."
        }

def build_news_verification_prompt(news_titles: List[str], ticker: str, date: str, fomo_score: float) -> str:
    """
    뉴스 검증 + FOMO 판단 통합 프롬프트
    """
    news_list = chr(10).join([f"{i+1}. {title}" for i, title in enumerate(news_titles)])
    
    return f"""
당신은 행동 재무학 판사입니다. 다음 정보를 바탕으로 이 거래가 'FOMO (뇌동매매)'인지 판단하세요.

[거래 정보]
- 종목: {ticker}
- 날짜: {date}
- FOMO Score (수식 기반): {fomo_score:.2f} (0.7 이상 = 고가 매수)

[발견된 뉴스 헤드라인]
{news_list}

[판단 프로세스]

Step 1: 뉴스 적합성 판단
- 위 뉴스 중 '주가 변동의 직접적 원인'을 설명하는 것이 있는가?
- 적합한 뉴스: "급등", "과열", "경고", "실적", "공시", "투기", "공매도", "숏스퀴즈" 등 키워드 포함
- 부적합한 뉴스: 제품 발표, 광고, 일반 기업 뉴스, 공장 방문 등 장기적 뉴스

Step 2: FOMO 판단 (적합한 뉴스가 2개 이상일 때만)
- "과열 경고", "투기", "공매도 숏스퀴즈", "광기", "급등 주의" → GUILTY (FOMO 유죄)
- "실적 발표", "기술적 돌파", "분석가 추천", "합리적 상승" → INNOCENT (합리적 판단)
- 중립적 뉴스 또는 뉴스 부족 → UNKNOWN (증거 불충분)

[출력 형식]
{{
    "relevance_check": "RELEVANT" | "IRRELEVANT",
    "relevant_count": 숫자,
    "verdict": "GUILTY" | "INNOCENT" | "UNKNOWN",
    "reasoning": "판단 근거 (한국어, 1-2문장)",
    "confidence": "HIGH" | "MEDIUM" | "LOW"
}}

중요 규칙:
1. 적합한 뉴스가 1개 이하이면 verdict는 반드시 "UNKNOWN"이어야 합니다.
2. 적합한 뉴스가 2개 이상일 때만 GUILTY 또는 INNOCENT 판단을 내리세요.
3. reasoning은 반드시 한국어로 작성하세요.
4. confidence는 판단 근거의 명확성에 따라 결정하세요 (뉴스가 명확하면 HIGH, 애매하면 LOW).
"""

@router.post("/verify-news", response_model=NewsVerification)
async def verify_news(request: NewsVerificationRequest):
    """
    뉴스 검증 API: 특정 거래에 대한 뉴스 기반 FOMO 판단
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY")
    
    if not api_key:
        return NewsVerification(
            verdict="UNKNOWN",
            reasoning="API Key가 설정되지 않았습니다.",
            confidence="LOW",
            news_titles=[],
            source="none"
        )
    
    openai = OpenAI(api_key=api_key)
    
    # 1. 뉴스 검색
    news_titles, source = fetch_news_context(request.ticker, request.date)
    
    # 뉴스가 없으면 즉시 반환
    if not news_titles or (len(news_titles) == 1 and "없음" in news_titles[0] or "실패" in news_titles[0]):
        return NewsVerification(
            verdict="UNKNOWN",
            reasoning="뉴스 데이터를 찾을 수 없어 판단을 보류합니다. 수식 기반 점수만 참고하세요.",
            confidence="LOW",
            news_titles=news_titles if news_titles else [],
            source=source
        )
    
    # 2. 키워드 기반 사전 필터링 (선택적)
    is_relevant, relevance_reason = validate_news_relevance(news_titles, request.ticker, request.date)
    
    # 3. LLM 뉴스 검증 프롬프트 호출
    prompt = build_news_verification_prompt(news_titles, request.ticker, request.date, request.fomo_score)
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a behavioral finance judge. Always respond with valid JSON only. IMPORTANT: Respond in Korean for reasoning field."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # 판단이므로 낮은 temperature
        )
        
        content = completion.choices[0].message.content
        result = json.loads(content)
        
        return NewsVerification(
            verdict=result.get("verdict", "UNKNOWN"),
            reasoning=result.get("reasoning", "판단 근거를 생성할 수 없습니다."),
            confidence=result.get("confidence", "LOW"),
            news_titles=news_titles,
            source=source,
            relevance_check=result.get("relevance_check"),
            relevant_count=result.get("relevant_count")
        )
        
    except Exception as e:
        print(f"News verification error: {e}")
        return NewsVerification(
            verdict="UNKNOWN",
            reasoning=f"AI 판단 중 오류가 발생했습니다: {str(e)}",
            confidence="LOW",
            news_titles=news_titles,
            source=source
        )

@router.post("/strategy-tag")
async def save_strategy_tag(request: dict, db: Session = Depends(get_db)):
    # (기존과 동일)
    trade_id = request.get('trade_id')
    strategy_tag = request.get('strategy_tag')
    if not trade_id or not strategy_tag: return {"success": False, "message": "Missing fields"}
    try:
        existing = db.query(StrategyTag).filter(StrategyTag.trade_id == trade_id).first()
        if existing: existing.tag = strategy_tag
        else: db.add(StrategyTag(trade_id=trade_id, tag=strategy_tag))
        db.commit()
        return {"success": True, "message": "Saved"}
    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="DB Error")