import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from duckduckgo_search import DDGS

# 경로 설정 (프로젝트 루트 기준)
BASE_DIR = Path(__file__).parent.parent.parent
NEWS_CACHE_PATH = BASE_DIR / "news_cache.json"

# 캐시 로드 (전역 변수)
NEWS_CACHE: Dict = {}

def load_news_cache():
    """뉴스 캐시 파일 로드"""
    global NEWS_CACHE
    try:
        if not NEWS_CACHE_PATH.exists():
            print(f"⚠ Warning: {NEWS_CACHE_PATH} not found. News cache will be empty.")
            NEWS_CACHE = {}
            return
        
        with open(NEWS_CACHE_PATH, "r", encoding="utf-8") as f:
            NEWS_CACHE = json.load(f)
        
        print(f"✓ Loaded news cache from {NEWS_CACHE_PATH}")
    except Exception as e:
        print(f"❌ Error loading news cache: {e}")
        NEWS_CACHE = {}

def build_search_queries(ticker: str, date: str) -> List[str]:
    """
    다중 검색 쿼리 생성
    여러 쿼리를 시도하여 최적 결과 찾기
    """
    # 날짜에서 YYYY-MM-DD 형식만 추출
    date_only = date.split(' ')[0] if ' ' in date else date
    
    queries = [
        f'"{ticker}" 주가 "{date_only}"',  # 따옴표로 정확도 향상
        f'"{ticker}" 급등 "{date_only}"',
        f'"{ticker}" 특징주 "{date_only}"',
        f'"{ticker}" stock news "{date_only}"',  # 해외 종목용
    ]
    return queries

def validate_news_relevance(news_titles: List[str], ticker: str, date: str) -> Tuple[bool, str]:
    """
    키워드 기반 뉴스 적합성 사전 필터링
    
    Returns:
        (is_relevant, reason): 적합한 뉴스가 2개 이상이면 True
    """
    relevant_keywords = ["급등", "급락", "과열", "경고", "실적", "공시", "주가", "특징주", "투기", "공매도", "숏스퀴즈"]
    irrelevant_keywords = ["광고", "추천", "무료", "방문", "발표"]  # 제품 발표는 장기적
    
    relevant_count = 0
    for title in news_titles:
        title_lower = title.lower()
        has_relevant = any(kw in title for kw in relevant_keywords)
        has_irrelevant = any(kw in title for kw in irrelevant_keywords)
        
        if has_relevant and not has_irrelevant:
            relevant_count += 1
    
    if relevant_count >= 2:
        return True, f"{relevant_count}개 뉴스가 주가 변동과 관련됨"
    elif relevant_count == 1:
        return False, "관련 뉴스가 부족함 (1개만 발견)"
    else:
        return False, "주가 변동과 무관한 뉴스만 발견됨"

def fetch_news_context(ticker: str, date: str, force_cache: bool = True) -> Tuple[List[str], str]:
    """
    뉴스 검색 (캐시 우선, 없으면 실시간 검색)
    
    Args:
        ticker: 종목 코드
        date: 거래 날짜 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS)
        force_cache: True일 때 캐시만 사용, 실시간 검색 스킵 (시연용)
    
    Returns:
        (news_titles, source): 뉴스 헤드라인 리스트와 출처 (cache/search/none)
    """
    # 날짜에서 YYYY-MM-DD 형식만 추출
    date_only = date.split(' ')[0] if ' ' in date else date
    
    # 1. 캐시 우선 확인 (시연용 안정성)
    if ticker in NEWS_CACHE and date_only in NEWS_CACHE[ticker]:
        cached = NEWS_CACHE[ticker][date_only]
        if isinstance(cached, dict) and "news" in cached:
            return cached["news"], "cache"
        elif isinstance(cached, list):
            return cached, "cache"
    
    # 2. 시연 모드: 캐시가 없으면 빈 배열 반환 (실시간 검색 스킵)
    if force_cache:
        return ["뉴스 데이터 없음 (캐시 미등록)"], "none"
    
    # 3. 실제 검색 (프로덕션용, 시연에서는 호출 안 됨)
    try:
        queries = build_search_queries(ticker, date_only)
        all_results = []
        
        ddgs = DDGS()
        for query in queries:
            try:
                results = ddgs.text(query, max_results=2)
                all_results.extend([r.get('title', '') for r in results if r.get('title')])
                
                if len(all_results) >= 3:
                    break
            except Exception as e:
                print(f"Search query failed for '{query}': {e}")
                continue
        
        # 중복 제거 및 최대 3개로 제한
        seen = set()
        unique_results = []
        for result in all_results:
            if result and result not in seen:
                seen.add(result)
                unique_results.append(result)
                if len(unique_results) >= 3:
                    break
        
        if unique_results:
            return unique_results, "search"
        else:
            return ["뉴스 검색 데이터 없음"], "none"
            
    except Exception as e:
        print(f"News search error: {e}")
        return ["뉴스 검색 실패"], "none"

# 앱 시작 시 캐시 로드
load_news_cache()

