"""
RAG 임베딩 생성 스크립트 (관리자용)

이 스크립트는 rag_cards.json을 읽어서 rag_embeddings.npy 파일을 생성합니다.
배포 시 매번 생성하는 것을 방지하기 위해 관리자만 실행합니다.

사용법:
    python generate_embeddings.py

요구사항:
    - OPENAI_API_KEY 환경 변수 설정
    - rag_cards.json 파일 존재
"""
import os
import json
import numpy as np
from pathlib import Path
from openai import OpenAI

BASE_DIR = Path(__file__).parent
RAG_FILE_PATH = BASE_DIR / "rag_cards.json"
RAG_EMBED_PATH = BASE_DIR / "rag_embeddings.npy"

def get_embeddings_batch(texts: list[str], client: OpenAI) -> list[list[float]]:
    """한 번의 API 호출로 여러 텍스트의 임베딩을 생성"""
    try:
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    # 1. Check API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set.")
        print("   Please set it before running this script.")
        return 1
    
    # 2. Load RAG Cards
    if not RAG_FILE_PATH.exists():
        print(f"❌ Error: {RAG_FILE_PATH} not found.")
        return 1
    
    with open(RAG_FILE_PATH, "r", encoding="utf-8") as f:
        RAG_CARDS = json.load(f)
    
    if not RAG_CARDS:
        print("❌ Error: RAG cards file is empty.")
        return 1
    
    print(f"✓ Loaded {len(RAG_CARDS)} RAG cards from {RAG_FILE_PATH}")
    
    # 3. Generate Embeddings
    client = OpenAI(api_key=api_key)
    
    print("Generating embeddings...")
    texts = [
        f"{c['title']} {c['content']} {c.get('action', '')} {' '.join(c['tags'])}" 
        for c in RAG_CARDS
    ]
    
    embeddings = get_embeddings_batch(texts, client)
    
    if not embeddings:
        print("❌ Failed to generate embeddings.")
        return 1
    
    # 4. Save Embeddings
    RAG_EMBEDDINGS = np.array(embeddings)
    np.save(RAG_EMBED_PATH, RAG_EMBEDDINGS)
    
    print(f"✓ Generated and saved {len(RAG_EMBEDDINGS)} embeddings to {RAG_EMBED_PATH}")
    print(f"✓ File size: {RAG_EMBED_PATH.stat().st_size / 1024:.2f} KB")
    print("\n💡 Next steps:")
    print("   1. Commit rag_embeddings.npy to Git repository")
    print("   2. Deploy with the pre-generated embeddings file")
    
    return 0

if __name__ == "__main__":
    exit(main())

