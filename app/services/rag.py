import json
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from openai import OpenAI

# 경로 설정 (프로젝트 루트 기준)
BASE_DIR = Path(__file__).parent.parent.parent
RAG_FILE_PATH = BASE_DIR / "rag_cards.json"
RAG_EMBED_PATH = BASE_DIR / "rag_embeddings.npy"

RAG_CARDS: List[dict] = []
RAG_EMBEDDINGS: Optional[np.ndarray] = None

def get_embeddings_batch(texts: List[str], client: OpenAI) -> List[List[float]]:
    try:
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return []

def cosine_similarity_top_k(
    query_vec: np.ndarray, 
    target_vecs: np.ndarray, 
    k: int = 2, 
    threshold: float = 0.4
) -> Tuple[List[int], List[float]]:
    if target_vecs is None or len(target_vecs) == 0:
        return [], []
    
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    target_norms = target_vecs / (np.linalg.norm(target_vecs, axis=1, keepdims=True) + 1e-9)
    
    similarities = np.dot(target_norms, query_norm)
    top_k_indices = np.argsort(similarities)[-k:][::-1]
    
    results = []
    scores = []
    
    for idx in top_k_indices:
        score = float(similarities[idx])
        if score >= threshold:
            results.append(int(idx))
            scores.append(score)
    
    return results, scores

def load_rag_index():
    global RAG_CARDS, RAG_EMBEDDINGS
    
    try:
        if not RAG_FILE_PATH.exists():
            print(f"⚠ Warning: {RAG_FILE_PATH} not found. RAG feature disabled.")
            RAG_CARDS = []
            RAG_EMBEDDINGS = None
            return
        
        with open(RAG_FILE_PATH, "r", encoding="utf-8") as f:
            RAG_CARDS = json.load(f)
        
        if not RAG_CARDS:
            print("⚠ Warning: RAG cards file is empty. RAG feature disabled.")
            RAG_EMBEDDINGS = None
            return
        
        print(f"✓ Loaded {len(RAG_CARDS)} RAG cards from {RAG_FILE_PATH}")
        
        if RAG_EMBED_PATH.exists():
            try:
                RAG_EMBEDDINGS = np.load(RAG_EMBED_PATH)
                if len(RAG_EMBEDDINGS) != len(RAG_CARDS):
                    print(f"⚠ Warning: Embeddings count ({len(RAG_EMBEDDINGS)}) doesn't match cards count ({len(RAG_CARDS)}).")
                    RAG_EMBEDDINGS = None
                else:
                    print(f"✓ Loaded {len(RAG_EMBEDDINGS)} embeddings from {RAG_EMBED_PATH}")
            except Exception as e:
                print(f"⚠ Error loading embeddings file: {e}")
                RAG_EMBEDDINGS = None
        else:
            print(f"⚠ Warning: {RAG_EMBED_PATH} not found. RAG feature disabled.")
                
    except Exception as e:
        print(f"❌ Error loading RAG index: {e}")
        RAG_CARDS = []
        RAG_EMBEDDINGS = None