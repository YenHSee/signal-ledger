import type {
  DailyPricePoint,
  ScreenerListResponse,
  StockNewsItem,
} from "@signal-ledger/api-types";
import { apiGet } from "./client";

export function getScreenerList(
  params: URLSearchParams,
): Promise<ScreenerListResponse> {
  return apiGet<ScreenerListResponse>(`/stock?${params.toString()}`);
}

export function getDailyPrices(ticker: string): Promise<DailyPricePoint[]> {
  return apiGet<DailyPricePoint[]>(`/stock/${ticker}/prices?days=365`);
}

export function getStockNews(ticker: string): Promise<StockNewsItem[]> {
  return apiGet<StockNewsItem[]>(`/stock/${ticker}/news`);
}
