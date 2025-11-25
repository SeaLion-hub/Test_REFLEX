# RAG v2.0 구현 가이드

## 개요

구조화된 하이브리드 검색을 지원하는 새로운 RAG 시스템이 구현되었습니다.

## 주요 개선사항

### 1. 구조화된 Chunking
- 각 카드의 `definition`, `connection`, `prescription`을 분리하여 별도 임베딩 생성
- 의미적 희석 문제 해결

### 2. 하이브리드 검색 파이프라인
- **Stage 1**: 메타데이터 필터링 (사용자 메트릭 기반)
- **Stage 2**: 벡터 검색 (필터링된 후보군에서)
- **Stage 3**: 재랭킹 (컨텍스트 기반 점수 조정)

### 3. 스마트 필터링
- `fomo_score`, `panic_score`, `volume_weight`, `disposition_ratio` 등 사용자 메트릭 기반 필터링
- `market_regime` (BEAR/BULL) 매칭
- 태그 기반 우선순위 검색

## 파일 구조

```
프로젝트 루트/
├── generate_embeddings_v2.py    # 새로운 임베딩 생성 스크립트
├── rag_cards.json               # 원본 카드 데이터 (기존 유지)
├── rag_embeddings_v2.json       # 구조화된 임베딩 (생성 필요)
├── app/
│   ├── services/
│   │   ├── rag.py               # 기존 (deprecated)
│   │   └── rag_v2.py            # 새로운 RAG 서비스
│   └── routers/
│       └── coach.py             # rag_v2 사용하도록 수정됨
└── main.py                      # rag_v2 로드하도록 수정됨
```

## 사용 방법

### 1. 임베딩 생성

먼저 새로운 형식의 임베딩을 생성해야 합니다:

```bash
python generate_embeddings_v2.py
```

이 스크립트는:
- `rag_cards.json`을 읽어서
- 각 카드의 `definition`, `connection`, `prescription`을 분리
- 각각 별도 임베딩 생성
- 검색 조건을 파싱하여 메타데이터에 저장
- `rag_embeddings_v2.json` 파일 생성

### 2. 서버 시작

```bash
python main.py
```

서버 시작 시 자동으로 `rag_embeddings_v2.json`을 로드합니다.

### 3. API 사용

기존 `/coach` API는 그대로 사용하되, 내부적으로 새로운 하이브리드 검색을 사용합니다.

## 검색 로직

### 메타데이터 필터링 예시

사용자 컨텍스트:
```python
{
    "fomo_score": 0.85,
    "volume_weight": 1.3,
    "market_regime": "BEAR",
    "primary_bias": "FOMO"
}
```

이 경우:
- `bias_fomo_01`: fomo_score_min=0.7, volume_weight_min=1.2, regime_preferred=["BEAR"] → **높은 점수**
- `bias_fomo_02`: fomo_score_min=0.7, volume_weight_min=1.5 → **중간 점수**
- `bias_fomo_03`: fomo_score_min=0.8, volume_weight_min=1.2 → **높은 점수**

### 벡터 검색

필터링된 후보군에서 벡터 유사도 검색:
- 쿼리: "FOMO high volatility risk fomo_score 0.85 volume_weight 1.3 chasing"
- 각 chunk 타입별로 검색 (definition, connection, prescription)
- `prescription`에 더 높은 가중치 (1.2x)

### 재랭킹

최종 점수 = 벡터 유사도 × chunk 가중치 + 컨텍스트 보너스

## 검색 조건 파싱

`generate_embeddings_v2.py`는 `connection` 텍스트에서 다음 패턴을 자동으로 파싱합니다:

- `fomo_score가 0.7 이상` → `{"fomo_score_min": 0.7}`
- `panic_score가 0.3 이하` → `{"panic_score_max": 0.3}`
- `volume_weight가 1.2 이상` → `{"volume_weight_min": 1.2}`
- `disposition_ratio가 1.5 이상` → `{"disposition_ratio_min": 1.5}`
- `BEAR` 또는 `하락장` → `{"regime_preferred": ["BEAR"]}`
- `BULL` 또는 `상승장` → `{"regime_preferred": ["BULL"]}`

## 마이그레이션

기존 시스템에서 마이그레이션:

1. ✅ `generate_embeddings_v2.py` 작성 완료
2. ✅ `app/services/rag_v2.py` 작성 완료
3. ✅ `app/routers/coach.py` 수정 완료
4. ✅ `main.py` 수정 완료
5. ⏳ `python generate_embeddings_v2.py` 실행 필요
6. ⏳ 테스트 및 검증

## 성능

- 임베딩 생성: 배치 처리로 효율적 (100개씩)
- 검색 속도: 메타데이터 필터링으로 후보군 축소 → 빠른 벡터 검색
- 정확도: 컨텍스트 기반 재랭킹으로 관련성 높은 결과 반환

## 주의사항

- `rag_embeddings_v2.json` 파일이 없으면 RAG 기능이 비활성화됩니다
- 기존 `rag_embeddings.npy`는 더 이상 사용되지 않습니다
- `rag_cards.json`이 변경되면 임베딩을 재생성해야 합니다


