# PRISM (프리즘) - 투자 심리 분석 도구

<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

## 📖 프로젝트 소개

**PRISM (프리즘)**은 투자자의 거래 내역을 분석하여 심리적 편향을 감지하고 개선 방안을 제시하는 AI 기반 분석 도구입니다. 단순한 수익률 분석을 넘어서 **행동 금융학(Behavioral Finance)** 원칙에 기반하여 투자자의 심리적 패턴을 파악하고, AI 코치가 맞춤형 피드백을 제공합니다.

### 🎯 핵심 아이디어

1. **과정 평가 (Process Evaluation)**: 단일 거래의 결과가 아닌 반복되는 패턴에 집중
   - "한두 번은 운 탓일 수 있지만, 10번 반복되면 실력(편향)입니다"
   - 최근 N번 거래 중 X번이나 특정 편향이 발생하는 패턴 분석

2. **4가지 주요 편향 감지**:
   - **FOMO (Fear of Missing Out)**: 고점 매수 경향
   - **Panic Sell**: 저점 매도 경향
   - **Revenge Trading**: 손실 직후 즉시 재매수
   - **Disposition Effect**: 손실 종목을 수익 종목보다 오래 보유

3. **AI 기반 개인화 코칭**:
   - **RAG v2.0 (구조화된 하이브리드 검색)** 기술로 행동 금융학 원칙 기반 조언
   - 각 카드의 definition, connection, prescription을 분리하여 의미적 희석 문제 해결
   - 메타데이터 필터링 + 벡터 검색 + 재랭킹을 통한 정확한 검색
   - 사용자의 거래 패턴에 맞춘 구체적이고 실행 가능한 개선 방안 제시
   - Sandwich Feedback 방식 (칭찬 → 비판 → 격려)

4. **고급 패턴 분석**:
   - 시간대별 클러스터링 (예: "MAE 큰 포지션은 오후 2-3시에 집중")
   - 시장 환경별 편향 분석 (상승장/하락장/횡보장)
   - Revenge Trading 연쇄 패턴 감지

## 🏗️ 기술 스택

### 프론트엔드
- **React 19** + **TypeScript**
- **Vite** (빌드 도구)
- **Recharts** (차트 시각화)
- **Tailwind CSS** (CDN, 스타일링)
- **Lucide React** (아이콘)

### 백엔드
- **FastAPI** (Python 웹 프레임워크)
- **Pandas** (데이터 분석)
- **NumPy** (수치 계산)
- **yfinance** (시장 데이터 수집)
- **OpenAI API** (GPT-4o-mini 기반 AI 코칭)
- **OpenAI Embeddings** (RAG v2.0 구조화된 임베딩)
- **DuckDuckGo Search** (뉴스 검색)
- **SQLAlchemy** + **Alembic** (데이터베이스 ORM 및 마이그레이션)
- **PostgreSQL** (데이터베이스)

## 📋 주요 기능

### 1. 거래 내역 분석 (`/analyze` 엔드포인트)
- CSV 파일 업로드로 거래 내역 분석
- 필수 컬럼: `ticker`, `entry_date`, `entry_price`, `exit_date`, `exit_price` (선택: `qty`)
- 각 거래에 대한 상세 메트릭 계산:
  - **FOMO Score**: 진입 가격이 당일 고가에 얼마나 가까운지 (0-1, 높을수록 FOMO)
  - **Panic Score**: 청산 가격이 당일 저가에 얼마나 가까운지 (0-1, 낮을수록 Panic)
  - **MAE (Max Adverse Excursion)**: 보유 기간 중 최대 손실
  - **MFE (Max Favorable Excursion)**: 보유 기간 중 최대 수익
  - **Efficiency**: 실제 수익 / 최대 잠재 수익
  - **Regret**: 청산 후 3일 내 최대 고가 대비 놓친 수익

### 2. 행동 메트릭 계산
- **Win Rate**: 승률
- **Profit Factor**: 평균 수익 / 평균 손실
- **Disposition Ratio**: 손실 종목 보유 기간 / 수익 종목 보유 기간
- **Revenge Trading Count**: 손실 직후 24시간 내 재매수 횟수
- **Truth Score**: 종합 점수 (0-100)
- **Sharpe Ratio**, **Sortino Ratio**, **Alpha**: 고급 성과 지표
- **Luck Percentile**: 몬테카를로 시뮬레이션 기반 운 요소 분석

### 3. Perfect Edition 기능
- **Personal Baseline**: 개인 평균 기준선 (FOMO, Panic, MAE, Disposition Ratio)
- **Bias Loss Mapping**: 편향별 금전적 피해 계산
- **Bias Priority**: 편향 우선순위 (금전적 피해 + 빈도 + 심각도)
- **Behavior Shift**: 최근 3건 vs 기준선 비교 (개선/악화/안정)
- **Equity Curve**: 시간순 누적 손익 곡선
- **Deep Pattern Analysis**: AI 기반 고급 패턴 추출

### 3-1. MVP 필살기 기능 (핵심 차별화 요소)

#### Causal Chain 추론 (인과 사슬 생성)
- **"핵폭탄급 차별화"**: 단순 통계를 넘어서 사건의 순서(Sequence)를 통해 인과관계를 설명
- 4단계 이벤트 시퀀스 감지: High MAE (물림) → Long Hold (비자발적 장기보유) → Market Drop (시장 하락) → Panic Sell (저점 매도)
- LLM 기반 내러티브 생성: 타임스탬프를 분석하여 "오후 2시 고점에 진입했으나, 3시경 급락이 발생했고..." 형식의 인과관계 설명
- 시간 정보가 있는 거래만 분석 (샘플링: FOMO 높은 거래 또는 손실 큰 거래)

#### 3중 분석 구조 (Behavior → Regime → Narrative)
- **시스템의 '깊이'를 보여주는 구조**: 단순 지표 나열이 아닌 입체적 진단
- **Layer 1 (Behavior)**: FOMO, Panic, Revenge 점수 (팩트)
- **Layer 2 (Regime)**: Market Regime (BULL/BEAR/SIDEWAYS) 분석 (맥락)
- **Layer 3 (Narrative)**: AI Judge의 뉴스 분석 결과 또는 메트릭 기반 Fallback Narrative (해석)
- 시각적으로 3단계를 분리하여 표시: 1단계 팩트 → 2단계 맥락 → 3단계 해석

#### 편향 프로필 (Bias DNA) 시각화
- **시각적 임팩트가 가장 큰 기능**: 프레젠테이션 화면에 띄워놓기 가장 좋은 자료
- 기존 BehavioralRadar를 "Bias DNA Signature"로 리브랜딩
- 새로운 축 매핑:
  - **Impulse (충동)**: (1 - FOMO Index) × 100
  - **Fear (공포)**: Panic Index × 100
  - **Greed (탐욕)**: FOMO Index × 100
  - **Resilience (회복력)**: 100 - (Revenge Trading Count × 25)
  - **Discipline (절제)**: (1 - Disposition Ratio) × 50
- **투자자 유형(Persona) 분류**: 메트릭 기반으로 "유리멘탈 스캘퍼", "FOMO 중독자", "과도한 신중파", "균형잡힌 트레이더" 등 자동 분류

### 4. AI 코칭 (`/coach` 엔드포인트)
- 사용자의 거래 패턴을 분석하여 맞춤형 피드백 제공
- **RAG v2.0 하이브리드 검색** 기반 지식 베이스 활용 (`rag_cards.json`)
  - 메타데이터 필터링: 사용자 메트릭(fomo_score, volume_weight, regime 등) 기반 후보군 축소
  - 벡터 검색: 필터링된 후보군에서 의미적 유사도 검색
  - 재랭킹: 컨텍스트 기반 점수 조정으로 관련성 높은 결과 우선 반환
- Sandwich Feedback 방식:
  1. **Strengths**: 잘한 매매 (이달의 명장면) 먼저 언급
  2. **Diagnosis**: 패턴 기반 진단 (단일 거래가 아닌 반복 패턴)
  3. **Rule**: 기억하기 쉬운 거래 원칙
  4. **Bias**: 주요 심리적 편향 명명
  5. **Fix**: 즉시 실행 가능한 개선 방안
- **Personal Playbook**: 개인화된 투자 원칙 생성 (3단계 액션 플랜)

### 5. 하이브리드 AI 뉴스 검증 (`/verify-news` 엔드포인트)
- **GenAI 프로젝트의 핵심 차별화 기능**
- FOMO 점수가 높은 거래에 대해 뉴스를 검색하고 AI가 판단
- 수식 기반 점수만으로는 놓칠 수 있는 시장 맥락을 AI가 분석
- **캐시 우선 전략**: 시연용 고품질 데이터 우선 사용 (`force_cache=True`), 없으면 Fallback Narrative 생성
- **2단계 판단 프로세스**:
  1. 뉴스 적합성 판단 (Relevance Filter): 주가 변동과 관련된 뉴스인지 확인
  2. FOMO 판단 (Main Judge): 뉴스 내용을 바탕으로 "유죄(뇌동매매)" / "무죄(전략적 진입)" / "보류(증거 불충분)" 판결
- **AI Judge Modal**: 법정 판결문 스타일의 UI로 판결 결과 표시
- 판결 근거, 확신도, 참조한 뉴스 헤드라인 제공
- **Fallback Narrative**: 뉴스 데이터가 없을 때 메트릭 기반 대체 Narrative 자동 생성 (FOMO/Panic 점수와 Market Regime 조합)

### 6. 스마트 컷 소명 기능
- Panic Score가 낮은 거래에 대해 "계획된 손절(Planned Cut)" 소명 가능
- 사용자가 의도적인 손절임을 명시하면 Panic Score 계산에서 제외
- Truth Score 자동 재계산으로 즉시 반영
- FOMO 거래 소명과 동일한 UX 패턴 (BREAKOUT, AGGRESSIVE_ENTRY 옵션)

### 7. 맥락 기반 점수 고도화
- **Volume Weight**: 거래량 폭발 시 FOMO/Panic 점수 가중치 적용
  - 평소 거래량의 2.5배 이상: 1.2배 가중치
  - 평소 거래량의 5배 이상: 1.5배 가중치
- **Regime Weight**: 시장 국면에 따른 가중치 적용
  - 상승장에서 공포 매도: 1.5배 페널티
  - 하락장에서 반등 추격 매수: 1.5배 페널티
  - 상승장에서 FOMO 매수: 0.8배 완화
- **Contextual Score**: Base Score × Volume Weight × Regime Weight
- 단순 고점 매수와 "거래량이 터진 고점 매수"를 구분

### 8. 전략 태그 관리 (`/strategy-tag` 엔드포인트)
- 각 거래에 전략 태그를 저장하고 관리
- 지원 태그:
  - `BREAKOUT`: 돌파 매매 전략
  - `AGGRESSIVE_ENTRY`: 공격적 진입 전략
  - `PLANNED_CUT`: 계획된 손절
  - `FOMO`: 뇌동매매 인정
- 데이터베이스에 영구 저장
- 태그 선택 시 Truth Score 자동 재계산

## 🚀 실행 방법

### 사전 요구사항

1. **Node.js** (v18 이상 권장)
2. **Python** (v3.8 이상)
3. **PostgreSQL** (데이터베이스)
4. **OpenAI API Key** (AI 코칭 기능 사용 시)

### 1단계: 저장소 클론 및 의존성 설치

```bash
# 저장소 클론
git clone <repository-url>
cd PRISM

# 프론트엔드 의존성 설치
npm install

# 백엔드 의존성 설치
pip install -r requirements.txt
```

### 2단계: 환경 변수 설정

#### 백엔드 환경 변수

`.env` 파일을 생성하거나 환경 변수로 설정:

```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="your-openai-api-key-here"
$env:DATABASE_URL="postgresql://user:password@localhost:5432/dbname"

# Windows (CMD)
set OPENAI_API_KEY=your-openai-api-key-here
set DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Linux/Mac
export OPENAI_API_KEY="your-openai-api-key-here"
export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
```

**필수 환경 변수**:
- `OPENAI_API_KEY`: OpenAI API 키 (AI 코칭 기능 사용 시)
- `DATABASE_URL`: PostgreSQL 데이터베이스 연결 URL

#### 프론트엔드 환경 변수 (선택사항)

프론트엔드에서 직접 OpenAI API를 사용하는 경우 `.env.local` 파일 생성:

```
VITE_OPENAI_API_KEY=your-openai-api-key-here
```

### 3단계: 데이터베이스 설정

```bash
# Alembic 마이그레이션 실행
alembic upgrade head
```

### 4단계: RAG 임베딩 생성 (선택사항)

RAG 기능을 사용하려면 구조화된 임베딩 파일을 먼저 생성해야 합니다:

```bash
# OPENAI_API_KEY가 설정되어 있어야 함
python generate_embeddings_v2.py
```

이 스크립트는:
- `rag_cards.json` 파일을 읽어서
- 각 카드의 `definition`, `connection`, `prescription`을 분리하여
- 각각 별도 임베딩 생성 (의미적 희석 문제 해결)
- 검색 조건을 자동 파싱하여 메타데이터에 저장
- `rag_embeddings_v2.json` 파일로 저장합니다

**참고**: 
- `rag_embeddings_v2.json` 파일이 없어도 서버는 정상 작동하지만, RAG 기능은 비활성화됩니다.
- 이 파일은 대용량이므로 Git에 커밋하지 않습니다 (`.gitignore`에 포함됨).
- **RAG v2.0의 주요 개선사항**: 하이브리드 검색 파이프라인 (메타데이터 필터링 → 벡터 검색 → 재랭킹)으로 더 정확한 검색 결과 제공
- 자세한 내용은 `RAG_V2_IMPLEMENTATION.md` 참조

### 4-1단계: 뉴스 캐시 준비 (시연용, 선택사항)

뉴스 검증 기능의 시연 안정성을 위해 캐시 파일을 준비할 수 있습니다:

```bash
# 프로젝트 루트에 news_cache.json 파일 생성
```

**캐시 파일 형식**:
```json
{
  "086520": {
    "2023-07-26": {
      "news": [
        "에코프로 150만원 돌파... 증권가 '과열 경고'",
        "2차전지 광풍, 묻지마 투자 주의보",
        "공매도 숏스퀴즈로 인한 단기 급등 분석"
      ],
      "verdict": "GUILTY",
      "reasoning": "과열 경고 뉴스가 지배적이었습니다.",
      "confidence": "HIGH"
    }
  }
}
```

**참고**: 
- 시연 모드에서는 `force_cache=True`로 설정되어 캐시만 사용하며, 실시간 검색은 스킵됩니다
- 캐시가 없으면 "뉴스 데이터 없음 (캐시 미등록)" 메시지와 함께 Fallback Narrative가 자동 생성됩니다
- 프로덕션 환경에서는 환경 변수 `DEMO_MODE=false`로 설정하여 실시간 검색을 활성화할 수 있습니다

### 5단계: 서버 실행

#### 백엔드 서버 실행
```bash
# 방법 1: Python 직접 실행
python main.py

# 방법 2: uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 `http://localhost:8000`에서 실행됩니다.

#### 프론트엔드 개발 서버 실행
```bash
npm run dev
```

프론트엔드가 `http://localhost:3000` (또는 다른 포트)에서 실행됩니다.

### 6단계: 사용 방법

1. 브라우저에서 프론트엔드 URL 접속
2. CSV 파일 준비 (형식 참고 아래)
3. "Upload CSV" 버튼으로 파일 업로드
4. 분석 결과 확인:
   - 대시보드: 주요 메트릭 및 Truth Score
   - 차트: Equity Curve, FOMO/Panic 분포
   - AI 코치: 맞춤형 피드백 및 개선 방안
   - 거래 목록: 각 거래의 상세 메트릭
   - AI 검증: FOMO 점수 높은 거래에 "⚖️ AI 검증" 버튼 클릭하여 뉴스 기반 판단 확인
   - 소명하기: 전략적 진입이었거나 계획된 손절이었을 경우 소명하여 점수 보정

## 📄 CSV 파일 형식

CSV 파일은 다음 컬럼을 포함해야 합니다:

| 컬럼명 | 설명 | 필수 | 예시 |
|--------|------|------|------|
| `ticker` | 종목 코드 | ✅ | `AAPL`, `005930` |
| `entry_date` | 진입일 | ✅ | `2024-01-15` |
| `entry_price` | 진입 가격 | ✅ | `150.50` |
| `exit_date` | 청산일 | ✅ | `2024-01-20` |
| `exit_price` | 청산 가격 | ✅ | `155.30` |
| `qty` | 수량 | ❌ (기본값: 1) | `10` |

**예시 CSV**:
```csv
ticker,entry_date,entry_price,exit_date,exit_price,qty
AAPL,2024-01-15,150.50,2024-01-20,155.30,10
TSLA,2024-01-16,240.00,2024-01-18,235.00,5
```

**참고사항**:
- 날짜 형식: `YYYY-MM-DD`
- 가격은 숫자 형식
- 한국 주식의 경우 티커만 숫자로 입력해도 자동으로 `.KS` (코스피) 또는 `.KQ` (코스닥)를 시도합니다

## 🔧 프로젝트 구조

```
PRISM/
├── main.py                      # FastAPI 백엔드 서버
├── generate_embeddings_v2.py   # RAG v2.0 임베딩 생성 스크립트
├── rag_cards.json               # RAG 지식 베이스 (행동 금융학 원칙)
├── rag_embeddings_v2.json      # 구조화된 RAG 임베딩 (생성 필요)
├── RAG_V2_IMPLEMENTATION.md    # RAG v2.0 구현 가이드
├── requirements.txt             # Python 의존성
├── alembic.ini                   # Alembic 설정
│
├── alembic/                      # 데이터베이스 마이그레이션
│   ├── env.py
│   └── versions/                 # 마이그레이션 파일들
│
├── app/                          # 백엔드 애플리케이션
│   ├── core/
│   │   └── database.py           # 데이터베이스 연결 설정
│   ├── routers/                  # API 라우터
│   │   ├── analysis.py          # 거래 분석 엔드포인트
│   │   └── coach.py             # AI 코칭 및 뉴스 검증 엔드포인트
│   ├── services/                 # 비즈니스 로직
│   │   ├── market.py            # 시장 데이터 수집
│   │   ├── patterns.py          # 패턴 분석
│   │   ├── rag_v2.py            # RAG v2.0 서비스 (하이브리드 검색)
│   │   └── news.py              # 뉴스 검색 서비스
│   ├── models.py                # Pydantic 모델
│   └── orm.py                   # SQLAlchemy ORM 모델
│
├── index.html                    # HTML 진입점
├── index.tsx                     # React 진입점
├── App.tsx                       # 메인 앱 컴포넌트
├── package.json                  # Node.js 의존성
│
├── components/                   # React 컴포넌트
│   ├── UploadView.tsx           # CSV 업로드 UI
│   ├── Dashboard.tsx            # 대시보드 (메트릭 표시)
│   ├── Charts.tsx               # 차트 시각화
│   ├── AICoach.tsx              # AI 코치 UI
│   ├── StrategyTagModal.tsx     # 전략 태그 모달
│   ├── AIJudgeModal.tsx         # AI 판사 모달 (뉴스 검증)
│   ├── Threads.tsx              # 스레드 UI
│   └── Toast.tsx                # 토스트 알림
│
├── services/                     # 프론트엔드 비즈니스 로직
│   ├── analysisEngine.ts        # 프론트엔드 분석 엔진
│   └── openaiService.ts         # OpenAI API 래퍼
│
└── types.ts                      # TypeScript 타입 정의
```

## 🎓 주요 개념 설명

### Behavior Ontology (계층적 구조화)
- **LLM을 왜 썼는지 설명하는 '치트키'**: 막연하게 텍스트를 생성하는 게 아니라, 행동 경제학적 분류 체계(Ontology)에 따라 데이터를 구조화
- **계층적 구조**:
  - Level 1: Cognitive Bias (인지 편향)
  - Level 2: Emotional Bias (감정 편향)
  - Level 3: FOMO, Panic Sell, Revenge Trading, Disposition Effect
  - Level 4: Chasing Behavior, Loss Aversion, Tilt 등 구체적 행동 패턴
- `rag_cards.json`의 태그 구조가 이 Ontology에 맞춰 재정비됨
- 백서의 'AI Architecture' 파트에 다이어그램으로 설명

### FOMO Score
진입 가격이 당일 고가-저가 범위에서 어느 위치인지를 나타냅니다.
- **0.0**: 당일 최저가 근처 매수 (완벽한 진입)
- **0.5**: 당일 중간가 매수
- **1.0**: 당일 최고가 근처 매수 (FOMO)
- **임계값**: >0.7이면 임상적 FOMO로 간주

### Panic Score
청산 가격이 당일 고가-저가 범위에서 어느 위치인지를 나타냅니다.
- **0.0**: 당일 최저가 근처 매도 (Panic Sell)
- **0.5**: 당일 중간가 매도
- **1.0**: 당일 최고가 근처 매도 (완벽한 청산)
- **임계값**: <0.3이면 임상적 Panic Sell로 간주

### Disposition Ratio
손실 종목 보유 기간 / 수익 종목 보유 기간
- **1.0**: 손익 무관하게 동일 기간 보유 (이상적)
- **>1.5**: 손실 종목을 더 오래 보유 (Disposition Effect)
- **<1.0**: 수익 종목을 더 오래 보유 (반대 편향)

### Revenge Trading
손실 거래 직후 24시간 이내 동일 종목 재매수
- 감정적 복수 매매로 간주
- 즉시 손절 후 재진입하는 패턴

### Truth Score
종합 점수 (0-100)
- Win Rate, FOMO, Panic, Disposition Ratio, Revenge Trading을 종합
- 높을수록 심리적 편향이 적고, 거래 습관이 좋음
- 전략 태그(BREAKOUT, AGGRESSIVE_ENTRY, PLANNED_CUT) 선택 시 자동 재계산

### Contextual Score
맥락 기반 점수 (0-150)
- Base Score × Volume Weight × Regime Weight
- 단순 고점 매수와 "거래량이 터진 고점 매수"를 구분
- 시장 국면에 따른 편향의 심각도를 반영

## 🐛 문제 해결

### 백엔드 서버가 시작되지 않음
- Python 버전 확인: `python --version` (3.8 이상 필요)
- 의존성 설치 확인: `pip install -r requirements.txt`
- 포트 8000이 이미 사용 중인지 확인
- `DATABASE_URL` 환경 변수가 설정되어 있는지 확인

### 데이터베이스 연결 오류
- PostgreSQL이 실행 중인지 확인
- `DATABASE_URL` 환경 변수가 올바른지 확인
- Alembic 마이그레이션이 실행되었는지 확인: `alembic upgrade head`

### RAG 기능이 작동하지 않음
- `rag_embeddings_v2.json` 파일이 존재하는지 확인
- `python generate_embeddings_v2.py` 실행하여 임베딩 생성
- `rag_cards.json` 파일이 올바른 형식인지 확인
- `OPENAI_API_KEY` 환경 변수가 설정되어 있는지 확인
- 자세한 내용은 `RAG_V2_IMPLEMENTATION.md` 참조

### 시장 데이터를 가져오지 못함
- 인터넷 연결 확인
- yfinance API 제한 (너무 많은 요청 시 일시적 차단 가능)
- 티커 형식 확인 (한국 주식은 숫자만 입력해도 자동 변환 시도)

### AI 코치가 응답하지 않음
- `OPENAI_API_KEY` 환경 변수 설정 확인
- OpenAI API 크레딧 확인
- 네트워크 연결 확인
- 백엔드 로그 확인 (`main.py` 실행 터미널)

### 뉴스 검증이 작동하지 않음
- `duckduckgo-search` 패키지가 설치되어 있는지 확인: `pip install duckduckgo-search`
- 인터넷 연결 확인 (실시간 검색 시)
- `news_cache.json` 파일이 올바른 형식인지 확인 (캐시 사용 시)
- 백엔드 로그에서 검색 오류 확인

## 📝 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.

## 🤝 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

## 📧 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해주세요.

---

**PRISM (프리즘)** - 투자 심리 분석으로 더 나은 거래 습관 만들기
