from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI
import os
import json
import numpy as np
import pandas as pd

# 내부 모듈 임포트
from app.core.database import get_db
from app.orm import StrategyTag
from app.models import CoachRequest, DeepPattern, BiasPriority, PersonalBaseline, PersonalPlaybook
from app.services.rag import RAG_CARDS, RAG_EMBEDDINGS, get_embeddings_batch, cosine_similarity_top_k
from app.services.patterns import generate_personal_playbook

router = APIRouter()

@router.post("/coach")
async def get_ai_coach(request: CoachRequest):
    """
    OpenAI API를 호출하여 트레이딩 코칭 피드백을 생성합니다.
    모든 성과 지표(Win Rate, Profit Factor 등)를 종합하여 행동 편향과 연결합니다.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {
            "diagnosis": "API Key가 설정되지 않았습니다. 환경 변수를 확인해주세요.",
            "rule": "규칙 생성 불가",
            "bias": "N/A",
            "fix": "관리자에게 문의하세요."
        }
    
    openai = OpenAI(api_key=api_key)
    
    # 1. Primary Bias 식별
    primary_bias = request.bias_priority[0]['bias'] if request.bias_priority and len(request.bias_priority) > 0 else None
    
    # 2. RAG 검색 쿼리 생성
    query = ""
    if primary_bias:
        fomo_score = request.metrics.get('fomo_score', 0)
        panic_score = request.metrics.get('panic_score', 0)
        
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
        query = "Winning psychology consistency discipline" if request.metrics.get('win_rate', 0) > 0.6 else "Trading psychology basics risk management"
    
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
                    rag_text_lines = [f"- PRINCIPLE: {c['title']}\n  INSIGHT: {c['content']}\n  ACTION: {c['action']}" for c in retrieved_cards]
                    rag_context_text = f"RAG KNOWLEDGE BASE:\n{chr(10).join(rag_text_lines)}"
                    retrieved_cards_for_response = [{"title": c['title'], "content": c['content'], "action": c['action']} for c in retrieved_cards]
        except Exception as e:
            print(f"RAG Error: {e}")

    # 4. 프롬프트 데이터 준비
    top_regrets_str = [f"{t['ticker']} (Missed ${t.get('regret', 0):.0f})" for t in request.top_regrets]
    revenge_str = ', '.join([f"{t['ticker']} (-${abs(t.get('pnl', 0)):.0f})" for t in request.revenge_details]) if request.revenge_details else "None"
    
    # Metrics Formating
    win_rate_pct = request.metrics['win_rate'] * 100
    profit_factor = request.metrics['profit_factor']
    sharpe = request.metrics.get('sharpe_ratio', 0)
    sortino = request.metrics.get('sortino_ratio', 0)
    
    personal_baseline_text = ''
    example_mae_pct = 0.0
    
    if request.personal_baseline:
        pb = request.personal_baseline
        avg_mae_pct = pb['avg_mae'] * 100
        example_mae_pct = avg_mae_pct
        personal_baseline_text = f"""
    PERSONAL BASELINE (History):
    - Avg FOMO: {pb['avg_fomo']*100:.0f}% (Cur: {request.metrics['fomo_score']*100:.0f}%)
    - Avg Panic: {pb['avg_panic']*100:.0f}% (Cur: {request.metrics['panic_score']*100:.0f}%)
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
        bias_priority_text = f"""
    FIX PRIORITY (Ranked by Impact):
    {chr(10).join([f"    {i+1}. {p['bias']}: -${p['financial_loss']:.0f} (Frequency: {(p['frequency']*100):.0f}%, Severity: {(p['severity']*100):.0f}%)" for i, p in enumerate(request.bias_priority)])}
    """
    
    behavior_shift_text = ''
    if request.behavior_shift and len(request.behavior_shift) > 0:
        behavior_shift_lines = [
            f"    - {s['bias']}: {s['trend']} ({s['change_percent']:+.1f}%)" 
            for s in request.behavior_shift
        ]
        behavior_shift_text = f"""
    BEHAVIOR SHIFT (Recent 3 vs Baseline):
    {chr(10).join(behavior_shift_lines)}
    """
    
    total_regret = request.metrics.get('total_regret', 0)
    
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
    1. TRUTH SCORE: {request.metrics['truth_score']}/100
    2. BEHAVIOR: FOMO {request.metrics['fomo_score']*100:.0f}%, Panic {request.metrics['panic_score']*100:.0f}%, Disposition {request.metrics['disposition_ratio']:.1f}x
    
    {performance_text}
    {personal_baseline_text}
    {bias_loss_text}
    {bias_priority_text}
    {behavior_shift_text}
    {best_executions_text}
    {patterns_text}
    {deep_patterns_text}
    
    {rag_context_text}

    INSTRUCTIONS (INTELLIGENT DIAGNOSIS IN KOREAN):
    
    0. STRENGTHS:
       - If BEST EXECUTIONS exist, praise 1-2 specific trades first.
    
    1. DIAGNOSIS (3 sentences, DATA-DRIVEN REASONING):
       - Sentence 1: **Analyze the User's Trading Health**. 
         Interpret the relationship between Performance Metrics (Win Rate, Profit Factor) and Risk Metrics (Sharpe Ratio, Sortino Ratio, MAE).
         * Requirement: Cite specific numbers in parentheses.
       - Sentence 2: Identify the **Root Cause** ({primary_bias}) of the issue. Explain *how* this bias degrades metrics, citing specific bias scores.
       - Sentence 3: State the **Financial Reality**. Mention the total financial loss from this bias.
    
    2. RULE: A short, memorable commandment (in Korean).
    3. BIAS: The primary bias name (Keep in English, e.g., FOMO, Panic Sell).
    4. FIX: Actionable advice based on RAG or Patterns (in Korean).
    
    Output JSON: {{ "diagnosis": "...", "rule": "...", "bias": "...", "fix": "...", "strengths": [...] }}
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
        
        # Playbook Generation
        deep_patterns_list = [DeepPattern(**dp) for dp in request.deep_patterns] if request.deep_patterns else []
        bias_priority_list = [BiasPriority(**p) for p in request.bias_priority] if request.bias_priority else []
        pb_obj = PersonalBaseline(**request.personal_baseline) if request.personal_baseline else None
        min_trades = pd.DataFrame({'is_revenge': [False]*max(1, request.metrics.get('total_trades', 1))})
        if request.revenge_details:
            for i, _ in enumerate(request.revenge_details):
                if i < len(min_trades): min_trades.iloc[i, 0] = True
        
        playbook = generate_personal_playbook(deep_patterns_list, bias_priority_list, pb_obj, min_trades)
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