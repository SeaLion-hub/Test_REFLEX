"""
RAG 서비스 v2.0 - 구조화된 하이브리드 검색

각 카드의 definition, connection, prescription을 분리하여 검색하고,
메타데이터 필터링 + 벡터 검색 + 재랭킹을 통한 정확한 검색을 제공합니다.
"""
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
import os

# 경로 설정 (프로젝트 루트 기준)
BASE_DIR = Path(__file__).parent.parent.parent
RAG_FILE_PATH = BASE_DIR / "rag_cards.json"
RAG_EMBED_PATH = BASE_DIR / "rag_embeddings_v2.json"

# 전역 변수
RAG_CARDS_RAW: List[dict] = []  # 원본 카드 데이터
RAG_INDEX: Dict = {}  # 구조화된 인덱스
RAG_LOADED: bool = False


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """코사인 유사도 계산"""
    vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-9)
    vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-9)
    return float(np.dot(vec1_norm, vec2_norm))


def get_embeddings_batch(texts: List[str], client: OpenAI) -> List[List[float]]:
    """한 번의 API 호출로 여러 텍스트의 임베딩을 생성"""
    try:
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return []


def load_rag_index():
    """구조화된 RAG 인덱스 로드"""
    global RAG_CARDS_RAW, RAG_INDEX, RAG_LOADED
    
    try:
        # 원본 카드 로드
        if not RAG_FILE_PATH.exists():
            print(f"⚠ Warning: {RAG_FILE_PATH} not found. RAG feature disabled.")
            RAG_INDEX = {}
            RAG_LOADED = False
            return
        
        with open(RAG_FILE_PATH, "r", encoding="utf-8") as f:
            RAG_CARDS_RAW = json.load(f)
        
        if not RAG_CARDS_RAW:
            print("⚠ Warning: RAG cards file is empty. RAG feature disabled.")
            RAG_INDEX = {}
            RAG_LOADED = False
            return
        
        # 구조화된 임베딩 로드
        if not RAG_EMBED_PATH.exists():
            print(f"⚠ Warning: {RAG_EMBED_PATH} not found. RAG feature disabled.")
            print(f"   Please run: python generate_embeddings_v2.py")
            RAG_INDEX = {}
            RAG_LOADED = False
            return
        
        with open(RAG_EMBED_PATH, "r", encoding="utf-8") as f:
            structured_data = json.load(f)
        
        RAG_INDEX = structured_data.get("cards", {})
        
        if not RAG_INDEX:
            print("⚠ Warning: Structured embeddings file is empty. RAG feature disabled.")
            RAG_LOADED = False
            return
        
        print(f"✓ Loaded {len(RAG_INDEX)} structured RAG cards from {RAG_EMBED_PATH}")
        total_chunks = sum(len(card.get("chunks", {})) for card in RAG_INDEX.values())
        print(f"✓ Total chunks: {total_chunks} (definition, connection, prescription)")
        RAG_LOADED = True
        
    except Exception as e:
        print(f"❌ Error loading RAG index: {e}")
        import traceback
        traceback.print_exc()
        RAG_INDEX = {}
        RAG_LOADED = False


def is_loaded() -> bool:
    """RAG 인덱스가 로드되었는지 확인"""
    return RAG_LOADED


class RAGRetriever:
    """하이브리드 RAG 검색기"""
    
    def __init__(self, openai_client: Optional[OpenAI] = None):
        self.client = openai_client
        self.chunk_weights = {
            "prescription": 1.2,  # 처방이 가장 중요
            "definition": 1.0,
            "connection": 0.8  # 기술적 설명은 덜 중요
        }
    
    def retrieve(
        self,
        query: str,
        user_context: Dict,
        search_mode: str = "hybrid",
        k: int = 3
    ) -> List[Dict]:
        """
        멀티 스테이지 하이브리드 검색
        
        Args:
            query: 검색 쿼리 텍스트
            user_context: 사용자 컨텍스트 (fomo_score, panic_score, volume_weight, market_regime 등)
            search_mode: "hybrid", "vector_only", "metadata_only"
            k: 반환할 최대 카드 수
        
        Returns:
            검색 결과 리스트 (card_id, chunk_type, similarity, final_score 등 포함)
        """
        if not RAG_LOADED:
            return []
        
        # Stage 1: 메타데이터 기반 필터링
        if search_mode in ["hybrid", "metadata_only"]:
            candidate_ids = self._metadata_filter(user_context)
        else:
            candidate_ids = list(RAG_INDEX.keys())
        
        if not candidate_ids:
            return []
        
        # Stage 2: 벡터 검색
        if search_mode in ["hybrid", "vector_only"]:
            vector_results = self._vector_search(query, candidate_ids, k=k*2)
        else:
            # metadata_only 모드: 메타데이터 점수만 사용
            vector_results = [
                {
                    "card_id": cid,
                    "chunk_type": "prescription",  # 기본값
                    "chunk_text": self._get_chunk_text(cid, "prescription"),
                    "similarity": 0.5,  # 기본 유사도
                    "card_metadata": RAG_INDEX[cid]["metadata"]
                }
                for cid in candidate_ids[:k*2]
            ]
        
        # Stage 3: 재랭킹
        reranked = self._rerank(vector_results, user_context, k=k)
        
        return reranked
    
    def _metadata_filter(self, context: Dict) -> List[Tuple[str, float]]:
        """사용자 메트릭 기반 스마트 필터링"""
        candidate_scores = []
        
        for card_id, card_data in RAG_INDEX.items():
            conditions = card_data.get("metadata", {}).get("search_conditions", {})
            score = 0.0
            
            # fomo_score 조건 매칭
            if "fomo_score_min" in conditions:
                user_fomo = context.get("fomo_score", 0)
                if user_fomo >= conditions["fomo_score_min"]:
                    # 초과 정도에 따라 보너스
                    excess = user_fomo - conditions["fomo_score_min"]
                    score += 10 + (excess * 5)
            
            # panic_score 조건 매칭
            if "panic_score_max" in conditions:
                user_panic = context.get("panic_score", 1.0)
                if user_panic <= conditions["panic_score_max"]:
                    # 낮을수록 더 매칭
                    deficit = conditions["panic_score_max"] - user_panic
                    score += 10 + (deficit * 5)
            
            # volume_weight 조건 매칭
            if "volume_weight_min" in conditions:
                user_vol = context.get("volume_weight", 1.0)
                if user_vol >= conditions["volume_weight_min"]:
                    excess = user_vol - conditions["volume_weight_min"]
                    score += 10 + (excess * 3)
            
            # disposition_ratio 조건 매칭
            if "disposition_ratio_min" in conditions:
                user_disp = context.get("disposition_ratio", 0)
                if user_disp >= conditions["disposition_ratio_min"]:
                    excess = user_disp - conditions["disposition_ratio_min"]
                    score += 10 + (excess * 2)
            
            # regret 조건 매칭
            if "regret_min" in conditions:
                user_regret = context.get("regret", 0)
                if user_regret >= conditions["regret_min"]:
                    score += 5
            
            # regime 매칭 (높은 가중치)
            if "regime_preferred" in conditions:
                user_regime = context.get("market_regime", "")
                if user_regime in conditions["regime_preferred"]:
                    score += 15  # 더 높은 가중치
            
            # is_revenge 조건 매칭
            if conditions.get("is_revenge", False):
                user_revenge = context.get("is_revenge", False)
                if user_revenge:
                    score += 10
            
            # 태그 매칭
            if "priority_tags" in conditions:
                user_tags = context.get("detected_tags", [])
                card_tags = card_data.get("metadata", {}).get("tags", [])
                matching_tags = set(conditions["priority_tags"]) & set(user_tags)
                if matching_tags:
                    score += len(matching_tags) * 5
            
            # primary_bias 매칭
            primary_bias = context.get("primary_bias", "")
            if primary_bias:
                card_tags = card_data.get("metadata", {}).get("tags", [])
                if primary_bias in card_tags:
                    score += 20  # 가장 높은 가중치
            
            if score > 0:
                candidate_scores.append((card_id, score))
        
        # 점수 순으로 정렬
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in candidate_scores]
    
    def _vector_search(
        self,
        query: str,
        candidate_ids: List[str],
        k: int
    ) -> List[Dict]:
        """벡터 검색 (여러 chunk 타입에서 검색)"""
        if not self.client:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY")
            if not api_key:
                return []
            self.client = OpenAI(api_key=api_key)
        
        # 쿼리 임베딩 생성
        query_embeddings = get_embeddings_batch([query], self.client)
        if not query_embeddings:
            return []
        
        query_embedding = np.array(query_embeddings[0])
        
        results = []
        
        for card_id in candidate_ids:
            if card_id not in RAG_INDEX:
                continue
            
            card_data = RAG_INDEX[card_id]
            chunks = card_data.get("chunks", {})
            
            # 각 chunk 타입별로 검색
            for chunk_type, chunk_data in chunks.items():
                chunk_embedding = np.array(chunk_data.get("embedding", []))
                if len(chunk_embedding) == 0:
                    continue
                
                similarity = cosine_similarity(query_embedding, chunk_embedding)
                
                results.append({
                    "card_id": card_id,
                    "chunk_type": chunk_type,
                    "chunk_text": chunk_data.get("text", ""),
                    "similarity": similarity,
                    "card_metadata": card_data.get("metadata", {})
                })
        
        # 상위 k개 반환
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]
    
    def _rerank(
        self,
        results: List[Dict],
        context: Dict,
        k: int
    ) -> List[Dict]:
        """컨텍스트 기반 재랭킹"""
        reranked = []
        
        for result in results:
            card_id = result["card_id"]
            card_meta = result.get("card_metadata", {})
            conditions = card_meta.get("search_conditions", {})
            
            # 기본 벡터 유사도 점수
            base_score = result["similarity"]
            
            # chunk_type별 가중치 적용
            chunk_type = result.get("chunk_type", "definition")
            chunk_weight = self.chunk_weights.get(chunk_type, 1.0)
            
            # 컨텍스트 매칭 보너스
            context_bonus = 0.0
            
            # 메타데이터 조건 재확인 (더 세밀한 보너스)
            if "fomo_score_min" in conditions:
                user_fomo = context.get("fomo_score", 0)
                if user_fomo >= conditions["fomo_score_min"]:
                    context_bonus += 0.05
            
            if "regime_preferred" in conditions:
                user_regime = context.get("market_regime", "")
                if user_regime in conditions["regime_preferred"]:
                    context_bonus += 0.1
            
            # 최종 점수
            final_score = base_score * chunk_weight + context_bonus
            
            reranked.append({
                **result,
                "final_score": final_score
            })
        
        # 최종 점수로 정렬
        reranked.sort(key=lambda x: x["final_score"], reverse=True)
        
        # 같은 카드 중복 제거 (최고 점수만 유지)
        seen_cards = {}
        for result in reranked:
            card_id = result["card_id"]
            if card_id not in seen_cards:
                seen_cards[card_id] = result
            elif seen_cards[card_id]["final_score"] < result["final_score"]:
                seen_cards[card_id] = result
        
        unique_results = list(seen_cards.values())
        return unique_results[:k]
    
    def _get_chunk_text(self, card_id: str, chunk_type: str) -> str:
        """카드의 특정 chunk 텍스트 가져오기"""
        if card_id not in RAG_INDEX:
            return ""
        
        chunks = RAG_INDEX[card_id].get("chunks", {})
        chunk_data = chunks.get(chunk_type, {})
        return chunk_data.get("text", "")
    
    def get_full_card(self, card_id: str) -> Optional[Dict]:
        """카드 전체 정보 가져오기 (원본 카드 데이터 포함)"""
        if card_id not in RAG_INDEX:
            return None
        
        # 구조화된 데이터
        structured = RAG_INDEX[card_id]
        
        # 원본 카드 데이터 찾기
        original_card = None
        for card in RAG_CARDS_RAW:
            if card.get("id") == card_id:
                original_card = card
                break
        
        return {
            "structured": structured,
            "original": original_card
        }


def get_chunk_text(card_id: str, chunk_type: str) -> str:
    """유틸리티 함수: 카드의 특정 chunk 텍스트 가져오기"""
    if card_id not in RAG_INDEX:
        return ""
    
    chunks = RAG_INDEX[card_id].get("chunks", {})
    chunk_data = chunks.get(chunk_type, {})
    return chunk_data.get("text", "")


