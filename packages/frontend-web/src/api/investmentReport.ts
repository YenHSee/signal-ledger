import type {
  FundamentalsProfile,
  InvestmentReportHistoryItem,
  StockProfile,
} from "@signal-ledger/api-types";
import { apiGet } from "./client";

export function getReport(ticker: string): Promise<StockProfile> {
  return apiGet<StockProfile>(`/investment-report/${ticker}`);
}

export function getFundamentals(ticker: string): Promise<FundamentalsProfile> {
  return apiGet<FundamentalsProfile>(
    `/investment-report/${ticker}/fundamentals`,
  );
}

export function getReportHistory(
  ticker: string,
): Promise<InvestmentReportHistoryItem[]> {
  return apiGet<InvestmentReportHistoryItem[]>(
    `/investment-report/${ticker}/history`,
  );
}
