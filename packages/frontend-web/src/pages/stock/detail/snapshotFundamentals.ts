import type {
  FundamentalsProfile,
  RawFinancialSnapshot,
} from "@signal-ledger/api-types";

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function fundamentalsFromSnapshot(
  snapshot: RawFinancialSnapshot | null,
): FundamentalsProfile | null {
  if (!snapshot) return null;

  const profitability = snapshot.profitability_and_scale;
  const valuation = snapshot.valuation_and_growth;
  const consensus = snapshot.smart_money_consensus;
  const technical = snapshot.technical_and_momentum;

  return {
    ticker: snapshot.company_identity.symbol ?? "",
    price: numberOrNull(consensus.current_price),
    marketCap: numberOrNull(profitability.market_cap),
    valuation: {
      trailingPe: numberOrNull(valuation.trailing_pe),
      forwardPe: numberOrNull(valuation.forward_pe),
      pegRatio: numberOrNull(valuation.peg_ratio),
      evToRevenue: null,
      evToEbitda: null,
      priceToBook: null,
      priceToSales: numberOrNull(valuation.price_to_sales),
    },
    profitability: {
      profitMargin: numberOrNull(
        profitability.profit_margin_pct ?? profitability.profit_margin,
      ),
      returnOnEquity: numberOrNull(
        profitability.return_on_equity_pct ??
          profitability.return_on_equity_ttm,
      ),
      revenueGrowthYoy: numberOrNull(
        valuation.revenue_growth_yoy_pct ?? valuation.revenue_growth_yoy,
      ),
      earningsGrowthYoy: numberOrNull(
        valuation.earnings_growth_yoy_pct ?? valuation.earnings_growth_yoy,
      ),
    },
    income: {
      dividendYield: null,
      dividendPerShare: null,
      exDividendDate: null,
    },
    ownership: {
      percentInsiders: null,
      percentInstitutions: numberOrNull(consensus.percent_institutions),
    },
    analystRatings: {
      strongBuy: 0,
      buy: 0,
      hold: 0,
      sell: 0,
      strongSell: 0,
    },
    technical: {
      week52High: numberOrNull(technical.week_52_range?.high),
      week52Low: numberOrNull(technical.week_52_range?.low),
      ma50: numberOrNull(technical.moving_averages?.day_50_ma),
      ma200: numberOrNull(technical.moving_averages?.day_200_ma),
      beta: null,
    },
  };
}
