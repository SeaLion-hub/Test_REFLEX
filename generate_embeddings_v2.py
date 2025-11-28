"""
RAG 임베딩 생성 스크립트 v2.0 (구조화된 Chunking)

이 스크립트는 rag_cards.json을 읽어서 구조화된 임베딩을 생성합니다.
각 카드의 definition, connection, prescription을 분리하여 별도 임베딩을 생성하고,
메타데이터와 검색 조건을 함께 저장합니다.

사용법:
    python generate_embeddings_v2.py

요구사항:
    - OPENAI_API_KEY 환경 변수 설정
    - rag_cards.json 파일 존재
"""
import os
import json
import re
import numpy as np
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드
env_files = ['.env', '.env.local', '.env.development.local', '.env.production.local']
loaded = False
for env_file in env_files:
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path, override=True)
        loaded = True
        print(f"[OK] Loaded environment variables from {env_file}")
        break

if not loaded:
    load_dotenv()
    print("[INFO] Tried to load .env files (may not exist, using environment variables if available)")

BASE_DIR = Path(__file__).parent
RAG_FILE_PATH = BASE_DIR / "rag_cards.json"
RAG_EMBED_PATH = BASE_DIR / "rag_embeddings_v2.json"

def get_embeddings_batch(texts: list[str], client: OpenAI) -> list[list[float]]:
    """한 번의 API 호출로 여러 텍스트의 임베딩을 생성"""
    try:
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"[ERROR] Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def parse_search_conditions(card: dict) -> dict:
    """
    connection 텍스트에서 검색 조건을 파싱합니다.
    예: "fomo_score가 0.7 이상" -> {"fomo_score_min": 0.7}
    """
    connection = card.get("connection", "")
    conditions = {}
    
    # fomo_score 패턴
    fomo_patterns = [
        r'fomo_score[가\s]*([0-9.]+)\s*이상',
        r'fomo_score[가\s]*([0-9.]+)\s*초과',
        r'fomo_score\s*([0-9.]+)\s*이상',
    ]
    for pattern in fomo_patterns:
        match = re.search(pattern, connection, re.IGNORECASE)
        if match:
            conditions["fomo_score_min"] = float(match.group(1))
            break
    
    # panic_score 패턴
    panic_patterns = [
        r'panic_score[가\s]*([0-9.]+)\s*이하',
        r'panic_score[가\s]*([0-9.]+)\s*미만',
        r'panic_score\s*([0-9.]+)\s*이하',
    ]
    for pattern in panic_patterns:
        match = re.search(pattern, connection, re.IGNORECASE)
        if match:
            conditions["panic_score_max"] = float(match.group(1))
            break
    
    # volume_weight 패턴
    vol_patterns = [
        r'volume_weight[가\s]*([0-9.]+)\s*이상',
        r'volume_weight[가\s]*([0-9.]+)\s*초과',
        r'volume_weight\s*([0-9.]+)\s*이상',
    ]
    for pattern in vol_patterns:
        match = re.search(pattern, connection, re.IGNORECASE)
        if match:
            conditions["volume_weight_min"] = float(match.group(1))
            break
    
    # disposition_ratio 패턴
    disp_patterns = [
        r'disposition_ratio[가\s]*([0-9.]+)\s*이상',
        r'disposition_ratio[가\s]*([0-9.]+)\s*초과',
        r'disposition_ratio\s*([0-9.]+)\s*이상',
    ]
    for pattern in disp_patterns:
        match = re.search(pattern, connection, re.IGNORECASE)
        if match:
            conditions["disposition_ratio_min"] = float(match.group(1))
            break
    
    # regret 패턴
    regret_match = re.search(r'regret[가\s]*\$?([0-9.]+)\s*이상', connection, re.IGNORECASE)
    if regret_match:
        conditions["regret_min"] = float(regret_match.group(1))
    
    # regime 패턴
    if "BEAR" in connection or "하락장" in connection:
        conditions["regime_preferred"] = ["BEAR"]
    elif "BULL" in connection or "상승장" in connection:
        conditions["regime_preferred"] = ["BULL"]
    
    # is_revenge 패턴
    if "is_revenge=true" in connection or "revenge" in connection.lower():
        conditions["is_revenge"] = True
    
    # 태그에서 우선순위 태그 추출 (일반적인 bias 태그 제외)
    bias_tags = ["FOMO", "Panic Sell", "Revenge Trading", "Disposition Effect"]
    tags = card.get("tags", [])
    priority_tags = [t for t in tags if t not in bias_tags]
    if priority_tags:
        conditions["priority_tags"] = priority_tags
    
    return conditions

def main():
    # 1. Check API Key
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY environment variable not set.")
        print("   Please set it before running this script.")
        return 1
    
    # 2. Load RAG Cards
    if not RAG_FILE_PATH.exists():
        print(f"[ERROR] {RAG_FILE_PATH} not found.")
        return 1
    
    with open(RAG_FILE_PATH, "r", encoding="utf-8") as f:
        RAG_CARDS = json.load(f)
    
    if not RAG_CARDS:
        print("[ERROR] RAG cards file is empty.")
        return 1
    
    print(f"[OK] Loaded {len(RAG_CARDS)} RAG cards from {RAG_FILE_PATH}")
    
    # 3. Generate Structured Embeddings
    client = OpenAI(api_key=api_key)
    
    structured_data = {
        "metadata": {
            "version": "2.0",
            "model": "text-embedding-3-small",
            "created_at": datetime.now().isoformat(),
            "total_cards": len(RAG_CARDS)
        },
        "cards": {}
    }
    
    print("\n[INFO] Generating structured embeddings...")
    print("       Each card will have 3 separate embeddings: definition, connection, prescription")
    
    # 모든 텍스트를 수집하여 배치로 임베딩 생성
    all_texts = []
    text_mapping = []  # (card_id, chunk_type) 매핑
    
    for card in RAG_CARDS:
        card_id = card["id"]
        
        for chunk_type in ["definition", "connection", "prescription"]:
            text = card.get(chunk_type, "").strip()
            if text:
                all_texts.append(text)
                text_mapping.append((card_id, chunk_type))
    
    print(f"[INFO] Generating {len(all_texts)} embeddings in batches...")
    
    # 배치로 임베딩 생성
    batch_size = 100
    all_embeddings = []
    
    for i in range(0, len(all_texts), batch_size):
        batch = all_texts[i:i+batch_size]
        print(f"[INFO] Processing batch {i//batch_size + 1}/{(len(all_texts)-1)//batch_size + 1}...")
        embeddings = get_embeddings_batch(batch, client)
        all_embeddings.extend(embeddings)
    
    if len(all_embeddings) != len(all_texts):
        print(f"[ERROR] Embedding count mismatch: {len(all_embeddings)} != {len(all_texts)}")
        return 1
    
    # 임베딩을 카드 구조에 매핑 (순서대로 매핑)
    embedding_idx = 0
    for card in RAG_CARDS:
        card_id = card["id"]
        chunks = {}
        
        for chunk_type in ["definition", "connection", "prescription"]:
            text = card.get(chunk_type, "").strip()
            if text:
                # text_mapping과 all_embeddings는 같은 순서로 생성되었으므로 순차적으로 매핑
                if embedding_idx < len(text_mapping):
                    mapped_card_id, mapped_chunk_type = text_mapping[embedding_idx]
                    if mapped_card_id == card_id and mapped_chunk_type == chunk_type:
                        chunks[chunk_type] = {
                            "embedding": all_embeddings[embedding_idx],
                            "text": text,
                            "type": chunk_type
                        }
                        embedding_idx += 1
                    else:
                        # 순서가 맞지 않으면 에러
                        print(f"[ERROR] Embedding mapping mismatch for {card_id}.{chunk_type}")
                        return 1
        
        # 검색 조건 파싱
        search_conditions = parse_search_conditions(card)
        
        structured_data["cards"][card_id] = {
            "chunks": chunks,
            "metadata": {
                "id": card_id,
                "category": card.get("category"),
                "tags": card.get("tags", []),
                "title": card.get("title"),
                "search_conditions": search_conditions
            }
        }
    
    # 4. Save Structured Embeddings
    print(f"\n[INFO] Saving structured embeddings to {RAG_EMBED_PATH}...")
    
    # NumPy 배열을 리스트로 변환 (JSON 직렬화를 위해)
    def convert_numpy(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(item) for item in obj]
        return obj
    
    structured_data = convert_numpy(structured_data)
    
    with open(RAG_EMBED_PATH, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=2)
    
    file_size = RAG_EMBED_PATH.stat().st_size / 1024
    print(f"[OK] Generated and saved structured embeddings to {RAG_EMBED_PATH}")
    print(f"[OK] File size: {file_size:.2f} KB")
    print(f"[OK] Total cards: {len(structured_data['cards'])}")
    print(f"[OK] Total chunks: {sum(len(card['chunks']) for card in structured_data['cards'].values())}")
    
    print("\n[INFO] Next steps:")
    print("   1. Commit rag_embeddings_v2.json to Git repository")
    print("   2. Update app/services/rag_v2.py to use this new format")
    print("   3. Update main.py to load rag_v2 instead of rag")
    
    return 0

if __name__ == "__main__":
    exit(main())

