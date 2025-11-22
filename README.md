# Reflex - 투자 심리 분석 도구

<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

## 📖 프로젝트 소개

**Reflex**는 투자자의 거래 내역을 분석하여 심리적 편향을 감지하고 개선 방안을 제시하는 AI 기반 분석 도구입니다. 단순한 수익률 분석을 넘어서 **행동 금융학(Behavioral Finance)** 원칙에 기반하여 투자자의 심리적 패턴을 파악하고, AI 코치가 맞춤형 피드백을 제공합니다.

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
   - RAG (Retrieval-Augmented Generation) 기술로 행동 금융학 원칙 기반 조언
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
- **Tailwind CSS** (스타일링)
- **Lucide React** (아이콘)

### 백엔드
- **FastAPI** (Python 웹 프레임워크)
- **Pandas** (데이터 분석)
- **NumPy** (수치 계산)
- **yfinance** (시장 데이터 수집)
- **OpenAI API** (GPT-4o-mini 기반 AI 코칭)
- **OpenAI Embeddings** (RAG 임베딩)

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

### 4. AI 코칭 (`/coach` 엔드포인트)
- 사용자의 거래 패턴을 분석하여 맞춤형 피드백 제공
- RAG 기반 지식 베이스 활용 (`rag_cards.json`)
- Sandwich Feedback 방식:
  1. **Strengths**: 잘한 매매 (이달의 명장면) 먼저 언급
  2. **Diagnosis**: 패턴 기반 진단 (단일 거래가 아닌 반복 패턴)
  3. **Rule**: 기억하기 쉬운 거래 원칙
  4. **Bias**: 주요 심리적 편향 명명
  5. **Fix**: 즉시 실행 가능한 개선 방안
- **Personal Playbook**: 개인화된 투자 원칙 생성

## 🚀 실행 방법

### 사전 요구사항

1. **Node.js** (v18 이상 권장)
2. **Python** (v3.8 이상)
3. **OpenAI API Key** (AI 코칭 기능 사용 시)

### 1단계: 저장소 클론 및 의존성 설치

```bash
# 저장소 클론
git clone <repository-url>
cd REFLEX_1122

# 프론트엔드 의존성 설치
npm install

# 백엔드 의존성 설치
pip install -r requirements.txt
```

### 2단계: 환경 변수 설정

#### 백엔드 환경 변수
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="your-openai-api-key-here"

# Windows (CMD)
set OPENAI_API_KEY=your-openai-api-key-here

# Linux/Mac
export OPENAI_API_KEY="your-openai-api-key-here"
```

#### 프론트엔드 환경 변수 (선택사항)
`.env.local` 파일 생성 (Gemini API 사용 시):
```
GEMINI_API_KEY=your-gemini-api-key-here
```

### 3단계: RAG 임베딩 생성 (선택사항)

RAG 기능을 사용하려면 임베딩 파일을 먼저 생성해야 합니다:

```bash
# OPENAI_API_KEY가 설정되어 있어야 함
python generate_embeddings.py
```

이 스크립트는:
- `rag_cards.json` 파일을 읽어서
- 각 카드의 제목, 내용, 액션, 태그를 결합하여
- OpenAI Embeddings API로 벡터화하고
- `rag_embeddings.npy` 파일로 저장합니다

**참고**: `rag_embeddings.npy` 파일이 없어도 서버는 정상 작동하지만, RAG 기능은 비활성화됩니다.

### 4단계: 서버 실행

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

프론트엔드가 `http://localhost:5173` (또는 다른 포트)에서 실행됩니다.

### 5단계: 사용 방법

1. 브라우저에서 프론트엔드 URL 접속
2. CSV 파일 준비 (형식 참고 아래)
3. "Upload CSV" 버튼으로 파일 업로드
4. 분석 결과 확인:
   - 대시보드: 주요 메트릭 및 Truth Score
   - 차트: Equity Curve, FOMO/Panic 분포
   - AI 코치: 맞춤형 피드백 및 개선 방안
   - 거래 목록: 각 거래의 상세 메트릭

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
REFLEX_1122/
├── main.py                 # FastAPI 백엔드 서버
├── generate_embeddings.py  # RAG 임베딩 생성 스크립트
├── rag_cards.json          # RAG 지식 베이스 (행동 금융학 원칙)
├── rag_embeddings.npy      # 생성된 임베딩 파일 (Git에 커밋 권장)
├── requirements.txt        # Python 의존성
│
├── index.html              # HTML 진입점
├── index.tsx               # React 진입점
├── App.tsx                 # 메인 앱 컴포넌트
├── package.json            # Node.js 의존성
│
├── components/             # React 컴포넌트
│   ├── UploadView.tsx      # CSV 업로드 UI
│   ├── Dashboard.tsx       # 대시보드 (메트릭 표시)
│   ├── Charts.tsx          # 차트 시각화
│   ├── AICoach.tsx         # AI 코치 UI
│   └── StrategyTagModal.tsx # 전략 태그 모달
│
├── services/               # 비즈니스 로직
│   ├── analysisEngine.ts  # 프론트엔드 분석 엔진
│   └── openaiService.ts    # OpenAI API 래퍼
│
└── types.ts                # TypeScript 타입 정의
```

## 🎓 주요 개념 설명

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

## 🐛 문제 해결

### 백엔드 서버가 시작되지 않음
- Python 버전 확인: `python --version` (3.8 이상 필요)
- 의존성 설치 확인: `pip install -r requirements.txt`
- 포트 8000이 이미 사용 중인지 확인

### RAG 기능이 작동하지 않음
- `rag_embeddings.npy` 파일이 존재하는지 확인
- `python generate_embeddings.py` 실행하여 임베딩 생성
- `rag_cards.json` 파일이 올바른 형식인지 확인

### 시장 데이터를 가져오지 못함
- 인터넷 연결 확인
- yfinance API 제한 (너무 많은 요청 시 일시적 차단 가능)
- 티커 형식 확인 (한국 주식은 숫자만 입력해도 자동 변환 시도)

### AI 코치가 응답하지 않음
- `OPENAI_API_KEY` 환경 변수 설정 확인
- OpenAI API 크레딧 확인
- 네트워크 연결 확인
- 백엔드 로그 확인 (`main.py` 실행 터미널)

## 📝 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.

## 🤝 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

## 📧 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해주세요.

---

**Reflex** - 투자 심리 분석으로 더 나은 거래 습관 만들기
