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

/**
 * Mirrors the JSON snapshot produced by `build_ai_context()` in
 * packages/data-python/utils/storage.py at the moment a report was
 * generated. This is frozen historical data — it will not match live
 * `StockProfile` values for old reports.
 */
export interface RawFinancialSnapshotCompanyIdentity {
  symbol?: string;
  name?: string;
  sector?: string;
  business_summary?: string;
}

export interface RawFinancialSnapshotProfitabilityAndScale {
  market_cap: number;
  profit_margin: number;
  return_on_equity_ttm: number;
}

export interface RawFinancialSnapshotValuationAndGrowth {
  trailing_pe: number;
  forward_pe: number;
  peg_ratio: number;
  earnings_growth_yoy: number;
  revenue_growth_yoy?: number;
}

export interface RawFinancialSnapshotSmartMoneyConsensus {
  percent_institutions: number;
  analyst_target_price: number;
  current_price: number;
}

export interface RawFinancialSnapshotWeek52Range {
  high: number;
  low: number;
  current_position_pct: number;
}

export interface RawFinancialSnapshotTechnicalAndMomentum {
  price_3_weeks_ago?: number;
  moving_averages?: {
    day_50_ma: number;
    day_200_ma: number;
  };
  week_52_range: RawFinancialSnapshotWeek52Range;
  recent_3_weeks_action?: {
    price_change_pct: number;
  };
}

export interface RawFinancialSnapshot {
  company_identity: RawFinancialSnapshotCompanyIdentity;
  profitability_and_scale: RawFinancialSnapshotProfitabilityAndScale;
  valuation_and_growth: RawFinancialSnapshotValuationAndGrowth;
  smart_money_consensus: RawFinancialSnapshotSmartMoneyConsensus;
  technical_and_momentum: RawFinancialSnapshotTechnicalAndMomentum;
}

export interface InvestmentReportDetail {
  ticker: string;
  target_price: number | null;
  conclusion: string | null;
  conviction_level: string | null;
  upside_downside_pct: string | null;
  risk_level: string | null;
  full_report: string;
  reasoning: string;
  generated_at: string;
  raw_financial_data: RawFinancialSnapshot | null;
}

export interface StockProfile {
  ticker: string;
  current_price: number | null;
  target_price: number | null;
  conclusion: string | null;
  conviction_level: string | null;
  upside_downside_pct: string | null;
  risk_level: string | null;
  full_report: string;
  reasoning: string;
  generated_at: Date;
  dayChangePct: number | null;
  company_identity: RawFinancialSnapshotCompanyIdentity | null;
}

export interface InvestmentReportHistoryItem {
  id: number;
  generatedAt: string;
  conclusion: string | null;
  convictionLevel: string | null;
  targetPrice: number | null;
  upsideDownsidePct: string | null;
  riskLevel: string | null;
  priceAtGeneration: number | null;
}

export interface AnalystRatingBreakdown {
  strongBuy: number;
  buy: number;
  hold: number;
  sell: number;
  strongSell: number;
}

export interface FundamentalsProfile {
  ticker: string;
  price: number | null;
  marketCap: number | null;
  valuation: {
    trailingPe: number | null;
    forwardPe: number | null;
    pegRatio: number | null;
    evToRevenue: number | null;
    evToEbitda: number | null;
    priceToBook: number | null;
    priceToSales: number | null;
  };
  profitability: {
    profitMargin: number | null;
    returnOnEquity: number | null;
    revenueGrowthYoy: number | null;
    earningsGrowthYoy: number | null;
  };
  income: {
    dividendYield: number | null;
    dividendPerShare: number | null;
    exDividendDate: string | null;
  };
  ownership: {
    percentInsiders: number | null;
    percentInstitutions: number | null;
  };
  analystRatings: AnalystRatingBreakdown;
  // analystTargetPrice: number | null;
  technical: {
    week52High: number | null;
    week52Low: number | null;
    ma50: number | null;
    ma200: number | null;
    beta: number | null;
  };
}

export interface StockNewsItem {
  id: number;
  date: string;
  datetime: number;
  headline: string;
  summary: string;
  source: string;
  url: string;
}

export interface DailyPricePoint {
  date: string;
  close: number;
  volume?: number;
}

export type ScreenerIndexFilter = "all" | "spx" | "ndx";

export type ScreenerHasReportFilter = "all" | "yes" | "no";

export type ScreenerConclusionFilter = "BUY" | "HOLD" | "SELL";

export type ScreenerMaFilter = "all" | "above" | "below";

export type ScreenerNearExtremeFilter = "all" | "high" | "low";

export type ScreenerSortField =
  | "marketCap"
  | "forwardPe"
  | "price"
  | "vsSpx"
  | "ticker"
  | "revenueGrowthYoy"
  | "analystUpside"
  | "roe";

export type ScreenerSortOrder = "asc" | "desc";

export type ScreenerColumnKey =
  | "ticker"
  | "company"
  | "sector"
  | "price"
  | "marketCap"
  | "forwardEps"
  | "forwardPe"
  | "vsSpx"
  | "ai"
  | "revGrowth"
  | "analystUpside"
  | "roe"
  | "pctFrom52wHigh";

export const DEFAULT_SCREENER_COLUMNS: ScreenerColumnKey[] = [
  "ticker",
  "company",
  "sector",
  "price",
  "marketCap",
  "forwardEps",
  "forwardPe",
  "vsSpx",
  "ai",
  "revGrowth",
];

export const ALL_SCREENER_COLUMNS: ScreenerColumnKey[] = [
  ...DEFAULT_SCREENER_COLUMNS,
  "analystUpside",
  "roe",
  "pctFrom52wHigh",
];

export interface ScreenerStockItem {
  ticker: string;
  name: string;
  sector: string | null;
  price: number | null;
  marketCap: number | null;
  forwardEps: number | null;
  forwardPe: number | null;
  vsSpx: number | null;
  hasReport: boolean;
  aiSignal: string | null;
  upsidePct: string | null;
  revenueGrowthYoy: number | null;
  roe: number | null;
  analystUpside: number | null;
  pctFrom52wHigh: number | null;
}

export interface ScreenerListMeta {
  totalStocks: number;
  stocksWithReport: number;
  spxFwdPe: number | null;
  sectors: string[];
}

export interface ScreenerListResponse {
  data: ScreenerStockItem[];
  meta: ScreenerListMeta;
  total: number;
  page: number;
  totalPages: number;
}

export interface ScreenerAdvancedFilters {
  marketCapMin?: number;
  marketCapMax?: number;
  forwardPeMin?: number;
  forwardPeMax?: number;
  vsSpxMin?: number;
  vsSpxMax?: number;
  pegMax?: number;
  revenueGrowthMin?: number;
  earningsGrowthMin?: number;
  roeMin?: number;
  profitMarginMin?: number;
  dividendYieldMin?: number;
  ma50?: ScreenerMaFilter;
  ma200?: ScreenerMaFilter;
  nearExtreme?: ScreenerNearExtremeFilter;
  hasReport?: ScreenerHasReportFilter;
  conclusions?: ScreenerConclusionFilter[];
}

export interface ScreenerListQuery extends ScreenerAdvancedFilters {
  page?: number;
  limit?: number;
  index?: ScreenerIndexFilter;
  sector?: string;
  search?: string;
  sortBy?: ScreenerSortField;
  sortOrder?: ScreenerSortOrder;
}

export interface ScreenerSavedPreset {
  id: string;
  name: string;
  filters: Partial<ScreenerListQuery>;
}

export const SCREENER_SAVED_PRESETS: ScreenerSavedPreset[] = [
  {
    id: "deep-value",
    name: "Deep Value",
    filters: {
      vsSpxMax: 0.9,
      forwardPeMax: 15,
      marketCapMin: 10_000_000_000,
    },
  },
  {
    id: "high-growth-tech",
    name: "High Growth Tech",
    filters: {
      sector: "Information Technology",
      revenueGrowthMin: 15,
    },
  },
  {
    id: "dividend-income",
    name: "Dividend Income",
    filters: {
      dividendYieldMin: 2,
      marketCapMin: 10_000_000_000,
    },
  },
  {
    id: "ai-intel-ready",
    name: "AI Intel Ready",
    filters: {
      hasReport: "yes",
    },
  },
];
