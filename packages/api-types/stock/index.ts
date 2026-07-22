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
  market_cap?: number | null;
  profit_margin?: number | null;
  profit_margin_pct?: number | null;
  return_on_equity_ttm?: number | null;
  return_on_equity_pct?: number | null;
  [key: string]: unknown;
}

export interface RawFinancialSnapshotValuationAndGrowth {
  trailing_pe?: number | null;
  forward_pe?: number | null;
  peg_ratio?: number | null;
  earnings_growth_yoy?: number | null;
  earnings_growth_yoy_pct?: number | null;
  revenue_growth_yoy?: number | null;
  revenue_growth_yoy_pct?: number | null;
  price_to_sales?: number | null;
  [key: string]: unknown;
}

export interface RawFinancialSnapshotSmartMoneyConsensus {
  percent_institutions?: number | null;
  analyst_target_price?: number | null;
  current_price?: number | null;
  price_trade_date?: string;
  [key: string]: unknown;
}

export interface RawFinancialSnapshotWeek52Range {
  high: number;
  low: number;
  current_position_pct: number;
}

export interface RawFinancialSnapshotTechnicalAndMomentum {
  price_3_weeks_ago?: number;
  moving_averages?: {
    day_50_ma: number | null;
    day_200_ma: number | null;
  };
  week_52_range?: RawFinancialSnapshotWeek52Range;
  available_range?: RawFinancialSnapshotWeek52Range & {
    start?: string;
    end?: string;
  };
  recent_3_weeks_action?: {
    price_change_pct: number;
  };
}

export type PreviousCallVerdict =
  | "FAVORABLE"
  | "ADVERSE"
  | "FLAT"
  | "STABLE"
  | "UPSIDE_BREAKOUT"
  | "DOWNSIDE_BREAKDOWN"
  | "UNCLASSIFIED";

export interface PreviousCallReview {
  report_schema_version: number | null;
  analysis_as_of: string;
  conclusion: string;
  conviction_level: string | null;
  target_price: number | null;
  price_then: number;
  evaluation_as_of: string;
  evaluation_price: number;
  days_elapsed: number;
  performance_since_pct: number;
  verdict: PreviousCallVerdict;
  verdict_status: "interim";
  verdict_method: string;
}

export interface RawFinancialSnapshot {
  company_identity: RawFinancialSnapshotCompanyIdentity;
  profitability_and_scale: RawFinancialSnapshotProfitabilityAndScale;
  valuation_and_growth: RawFinancialSnapshotValuationAndGrowth;
  smart_money_consensus: RawFinancialSnapshotSmartMoneyConsensus;
  technical_and_momentum: RawFinancialSnapshotTechnicalAndMomentum;
  balance_sheet_and_cash_flow?: Record<string, unknown>;
  recent_catalysts?: Array<Record<string, unknown>>;
  previous_report?: PreviousCallReview | null;
  snapshot_metadata?: Record<string, unknown>;
}

export type ProvenanceStatus = "complete" | "partial" | "legacy_incomplete";

export interface ModelUsage {
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
}

export interface AgentOutput {
  run_id: string;
  agent_key: string;
  agent_version: string;
  output_schema_version: number;
  status: string;
  output: {
    stance: string;
    confidence: string;
    summary: string;
    evidence_refs: string[];
  };
}

export interface AgentRun {
  run_id: string;
  agent_key: string;
  agent_version: string;
  sequence: number;
  depends_on: string[];
  provider: string;
  tier: string;
  requested_model: string;
  response_model: string | null;
  system_fingerprint: string | null;
  local_model_digest: string | null;
  prompt_version: string;
  temperature: number;
  response_format: string;
  finish_reason: string | null;
  usage: ModelUsage;
}

export interface GenerationMetadata {
  schema_version: number;
  workflow_name: string;
  workflow_version: string;
  final_run_id: string;
  provenance_status: Exclude<ProvenanceStatus, "legacy_incomplete">;
  aggregate_usage: ModelUsage & {
    calls: number;
    by_model: Array<
      ModelUsage & { provider: string; model: string; calls: number }
    >;
  };
  agent_runs: AgentRun[];
}

export interface InvestmentReportDetail {
  report_schema_version: number | null;
  ticker: string;
  analysis_as_of: string | null;
  generation_mode: string | null;
  model_tier: string | null;
  model_provider: string | null;
  model_name: string | null;
  prompt_version: string | null;
  target_price: number | null;
  conclusion: string | null;
  conviction_level: string | null;
  upside_downside_pct: string | null;
  risk_level: string | null;
  full_report: string;
  reasoning: string;
  generated_at: string;
  raw_financial_data: RawFinancialSnapshot | null;
  agent_outputs: AgentOutput[] | null;
  generation_metadata: GenerationMetadata | null;
  provenance_status: ProvenanceStatus;
}

export interface StockProfile {
  report_id: number;
  report_schema_version: number | null;
  ticker: string;
  analysis_as_of: string | null;
  generation_mode: string | null;
  model_tier: string | null;
  model_provider: string | null;
  model_name: string | null;
  prompt_version: string | null;
  current_price: number | null;
  target_price: number | null;
  conclusion: string | null;
  conviction_level: string | null;
  upside_downside_pct: string | null;
  risk_level: string | null;
  full_report: string;
  reasoning: string;
  generated_at: string | Date;
  dayChangePct: number | null;
  company_identity: RawFinancialSnapshotCompanyIdentity | null;
  raw_financial_data: RawFinancialSnapshot | null;
  agent_outputs: AgentOutput[] | null;
  generation_metadata: GenerationMetadata | null;
  provenance_status: ProvenanceStatus;
}

export interface InvestmentReportHistoryItem {
  id: number;
  generatedAt: string;
  analysisAsOf: string | null;
  conclusion: string | null;
  convictionLevel: string | null;
  targetPrice: number | null;
  upsideDownsidePct: string | null;
  riskLevel: string | null;
  priceAtGeneration: number | null;
  modelProvider: string | null;
  modelName: string | null;
  promptVersion: string | null;
  provenanceStatus: ProvenanceStatus;
  evaluationAsOf: string | null;
  evaluationPrice: number | null;
  performanceSincePct: number | null;
  verdict: PreviousCallVerdict | null;
  verdictStatus: "interim" | null;
  verdictMethod: string | null;
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
