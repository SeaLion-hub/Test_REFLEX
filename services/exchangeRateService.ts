// 환율 API 서비스
// exchangerate-api.com 사용 (무료, API 키 불필요)

type Currency = 'USD' | 'KRW';

interface ExchangeRateResponse {
  rates: {
    KRW: number;
  };
  base: string;
  date: string;
}

// 환율 캐시 (1시간 동안 유효)
let cachedRate: { rate: number; timestamp: number } | null = null;
const CACHE_DURATION = 60 * 60 * 1000; // 1시간

export const fetchExchangeRate = async (): Promise<number> => {
  // 캐시 확인
  if (cachedRate && Date.now() - cachedRate.timestamp < CACHE_DURATION) {
    return cachedRate.rate;
  }

  try {
    // exchangerate-api.com 사용 (무료, API 키 불필요)
    const response = await fetch('https://api.exchangerate-api.com/v4/latest/USD');
    
    if (!response.ok) {
      throw new Error(`환율 API 오류: ${response.statusText}`);
    }

    const data: ExchangeRateResponse = await response.json();
    const rate = data.rates.KRW;

    // 캐시 저장
    cachedRate = {
      rate,
      timestamp: Date.now()
    };

    return rate;
  } catch (error) {
    console.error('환율 조회 실패:', error);
    
    // 캐시된 값이 있으면 사용
    if (cachedRate) {
      console.warn('캐시된 환율 사용:', cachedRate.rate);
      return cachedRate.rate;
    }

    // 기본값 사용 (1 USD = 1300 KRW)
    console.warn('기본 환율 사용: 1300');
    return 1300;
  }
};

// 통화 포맷팅 함수 (수정됨: 한국 단위 버그 수정)
export const formatCurrency = (amount: number, currency: Currency, exchangeRate: number): string => {
  if (currency === 'KRW') {
    const krwAmount = amount * exchangeRate;
    const absAmount = Math.abs(krwAmount);
    
    // 1억 이상
    if (absAmount >= 100000000) {
      return `${(krwAmount / 100000000).toFixed(2)}억원`;
    } 
    // 1만 이상 (10,000원 -> 1만원, 1,300,000원 -> 130만원)
    else if (absAmount >= 10000) {
      return `${(krwAmount / 10000).toFixed(0)}만원`;
    } 
    // 그 외 (천원 단위 등) -> 그냥 원화로 표시
    else {
      return `${Math.round(krwAmount).toLocaleString()}원`;
    }
  } else {
    // USD 포맷팅
    const absAmount = Math.abs(amount);
    if (absAmount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`;
    } else if (absAmount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}k`;
    }
    return `$${amount.toFixed(0)}`;
  }
};