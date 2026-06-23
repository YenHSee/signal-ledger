export interface CompanyProfile {
  name: string;
  sector: string;
  industry: string;
}

export interface Fundamentals {
  latest_quarter: string;
  market_cap_usd: number;
  pe_ratio: number;
  peg_ratio: number;
  profit_margin: number;
  roe: number;
  revenue_growth_yoy: number;
}

export interface MarketTechnicals {
  current_price: number;
  change_percent: string;
  target_price: number;
  high_52_week: number;
  ma_50_day: number;
  ma_200_day: number;
  institutional_ownership: string;
}

export interface StockReportData {
  ticker: string;
  company_profile: CompanyProfile;
  fundamentals: Fundamentals;
  market_technicals: MarketTechnicals;
}
