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
# [추가됨] .env 파일 로드
from dotenv import load_dotenv

# .env 또는 .env.local 파일의 내용을 환경 변수로 로드합니다.
# 여러 가능한 경로를 시도
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
    # 파일이 없어도 기본 load_dotenv() 시도 (환경 변수에서 직접 읽을 수 있음)
    load_dotenv()
    print("[INFO] Tried to load .env files (may not exist, using environment variables if available)")

# 디버깅: 로드된 환경 변수 확인 (키 값은 숨김)
api_key_debug = os.getenv("OPENAI_API_KEY")
if api_key_debug:
    print(f"[DEBUG] OPENAI_API_KEY found (length: {len(api_key_debug)})")
else:
    print("[DEBUG] OPENAI_API_KEY not found in environment variables")

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
        print(f"[ERROR] Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    # 1. Check API Key (VITE_OPENAI_API_KEY도 확인 - 프론트엔드와 공유)
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY environment variable not set.")
        print("   Please set it before running this script.")
        print("\n[INFO] 해결 방법:")
        print("   1. .env 또는 .env.local 파일을 프로젝트 루트에 생성")
        print("   2. 파일 내용: OPENAI_API_KEY=your-api-key-here")
        print("   3. 또는 환경 변수로 직접 설정: $env:OPENAI_API_KEY='your-api-key' (PowerShell)")
        print(f"\n   현재 디렉토리: {Path.cwd()}")
        print(f"   찾은 .env 파일: {[f for f in ['.env', '.env.local'] if Path(f).exists()]}")
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
    
    # 3. Generate Embeddings
    client = OpenAI(api_key=api_key)
    
    print("Generating embeddings...")
    texts = [
        f"{c['title']} {c.get('definition', '')} {c.get('connection', '')} {c.get('prescription', '')} {' '.join(c.get('tags', []))}" 
        for c in RAG_CARDS
    ]
    
    embeddings = get_embeddings_batch(texts, client)
    
    if not embeddings:
        print("[ERROR] Failed to generate embeddings.")
        return 1
    
    # 4. Save Embeddings
    RAG_EMBEDDINGS = np.array(embeddings)
    np.save(RAG_EMBED_PATH, RAG_EMBEDDINGS)
    
    print(f"[OK] Generated and saved {len(RAG_EMBEDDINGS)} embeddings to {RAG_EMBED_PATH}")
    print(f"[OK] File size: {RAG_EMBED_PATH.stat().st_size / 1024:.2f} KB")
    print("\n[INFO] Next steps:")
    print("   1. Commit rag_embeddings.npy to Git repository")
    print("   2. Deploy with the pre-generated embeddings file")
    
    return 0

if __name__ == "__main__":
    exit(main())