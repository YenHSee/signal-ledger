import {
  ALL_SCREENER_COLUMNS,
  type ScreenerColumnKey,
  type ScreenerConclusionFilter,
  type ScreenerHasReportFilter,
  type ScreenerIndexFilter,
  type ScreenerListQuery,
  type ScreenerMaFilter,
  type ScreenerNearExtremeFilter,
  type ScreenerSortField,
  type ScreenerSortOrder,
} from "@stock-analyst/api-types";

export function formatMarketCap(value: number | null): string {
  if (value === null) return "—";
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toLocaleString()}`;
}

export function formatRatio(value: number | null, suffix = "x"): string {
  if (value === null) return "—";
  return `${value.toFixed(1)}${suffix}`;
}

export function formatPercent(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function isPremiumMultiple(vsSpx: number | null): boolean {
  return vsSpx !== null && vsSpx >= 1.5;
}

export function getSignalColor(signal: string | null): string {
  if (!signal) return "text-gray-400 bg-gray-800 border-gray-600";
  const s = signal.toUpperCase();
  if (s.includes("BUY"))
    return "text-green-400 bg-green-900/30 border-green-800";
  if (s.includes("HOLD"))
    return "text-yellow-400 bg-yellow-900/30 border-yellow-800";
  return "text-red-400 bg-red-900/30 border-red-800";
}

export const COLUMN_LABELS: Record<ScreenerColumnKey, string> = {
  ticker: "#",
  company: "Company",
  sector: "Sector",
  price: "Price",
  marketCap: "MCap",
  forwardEps: "Fwd EPS",
  forwardPe: "Fwd P/E",
  vsSpx: "vs SPX",
  ai: "AI",
  revGrowth: "Rev Gr",
  analystUpside: "Analyst Upside",
  roe: "ROE",
  pctFrom52wHigh: "vs 52W High",
};

export function sortColumnsByCanonicalOrder(
  columns: ScreenerColumnKey[],
): ScreenerColumnKey[] {
  return [...columns].sort(
    (a, b) => ALL_SCREENER_COLUMNS.indexOf(a) - ALL_SCREENER_COLUMNS.indexOf(b),
  );
}

export interface ScreenerUiState extends ScreenerListQuery {
  searchInput: string;
  visibleColumns: ScreenerColumnKey[];
  showMoreFilters: boolean;
}

export const DEFAULT_UI_STATE: ScreenerUiState = {
  page: 1,
  limit: 100,
  index: "all",
  sector: "all",
  searchInput: "",
  search: undefined,
  sortBy: "marketCap",
  sortOrder: "desc",
  hasReport: "all",
  ma50: "all",
  ma200: "all",
  nearExtreme: "all",
  visibleColumns: [
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
  ],
  showMoreFilters: false,
};

const NUMERIC_FILTER_KEYS: (keyof ScreenerListQuery)[] = [
  "marketCapMin",
  "marketCapMax",
  "forwardPeMin",
  "forwardPeMax",
  "vsSpxMin",
  "vsSpxMax",
  "pegMax",
  "revenueGrowthMin",
  "earningsGrowthMin",
  "roeMin",
  "profitMarginMin",
  "dividendYieldMin",
];

export function buildQueryParams(state: ScreenerUiState): URLSearchParams {
  const params = new URLSearchParams();

  if (state.page && state.page > 1) params.set("page", String(state.page));
  if (state.limit && state.limit !== DEFAULT_UI_STATE.limit)
    params.set("limit", String(state.limit));
  if (state.index && state.index !== "all") params.set("index", state.index);
  if (state.sector && state.sector !== "all") params.set("sector", state.sector);
  if (state.search) params.set("search", state.search);
  if (state.sortBy && state.sortBy !== "marketCap")
    params.set("sortBy", state.sortBy);
  if (state.sortOrder && state.sortOrder !== "desc")
    params.set("sortOrder", state.sortOrder);

  for (const key of NUMERIC_FILTER_KEYS) {
    const value = state[key];
    if (value !== undefined && value !== null) {
      params.set(key, String(value));
    }
  }

  if (state.ma50 && state.ma50 !== "all") params.set("ma50", state.ma50);
  if (state.ma200 && state.ma200 !== "all") params.set("ma200", state.ma200);
  if (state.nearExtreme && state.nearExtreme !== "all")
    params.set("nearExtreme", state.nearExtreme);
  if (state.hasReport && state.hasReport !== "all")
    params.set("hasReport", state.hasReport);
  if (state.conclusions && state.conclusions.length > 0)
    params.set("conclusions", state.conclusions.join(","));

  if (
    state.visibleColumns.length > 0 &&
    state.visibleColumns.join(",") !==
      DEFAULT_UI_STATE.visibleColumns.join(",")
  ) {
    params.set("columns", state.visibleColumns.join(","));
  }

  return params;
}

export function parseUiStateFromSearchParams(
  searchParams: URLSearchParams,
): ScreenerUiState {
  const state: ScreenerUiState = {
    ...DEFAULT_UI_STATE,
    page: Number(searchParams.get("page") || 1),
    limit: Number(searchParams.get("limit") || DEFAULT_UI_STATE.limit),
    index: (searchParams.get("index") as ScreenerIndexFilter) || "all",
    sector: searchParams.get("sector") || "all",
    searchInput: searchParams.get("search") || "",
    search: searchParams.get("search") || undefined,
    sortBy: (searchParams.get("sortBy") as ScreenerSortField) || "marketCap",
    sortOrder: (searchParams.get("sortOrder") as ScreenerSortOrder) || "desc",
    hasReport:
      (searchParams.get("hasReport") as ScreenerHasReportFilter) || "all",
    ma50: (searchParams.get("ma50") as ScreenerMaFilter) || "all",
    ma200: (searchParams.get("ma200") as ScreenerMaFilter) || "all",
    nearExtreme:
      (searchParams.get("nearExtreme") as ScreenerNearExtremeFilter) || "all",
  };

  for (const key of NUMERIC_FILTER_KEYS) {
    const raw = searchParams.get(key);
    if (raw !== null && raw !== "") {
      const value = Number(raw);
      switch (key) {
        case "marketCapMin":
          state.marketCapMin = value;
          break;
        case "marketCapMax":
          state.marketCapMax = value;
          break;
        case "forwardPeMin":
          state.forwardPeMin = value;
          break;
        case "forwardPeMax":
          state.forwardPeMax = value;
          break;
        case "vsSpxMin":
          state.vsSpxMin = value;
          break;
        case "vsSpxMax":
          state.vsSpxMax = value;
          break;
        case "pegMax":
          state.pegMax = value;
          break;
        case "revenueGrowthMin":
          state.revenueGrowthMin = value;
          break;
        case "earningsGrowthMin":
          state.earningsGrowthMin = value;
          break;
        case "roeMin":
          state.roeMin = value;
          break;
        case "profitMarginMin":
          state.profitMarginMin = value;
          break;
        case "dividendYieldMin":
          state.dividendYieldMin = value;
          break;
      }
    }
  }

  const conclusions = searchParams.get("conclusions");
  if (conclusions) {
    state.conclusions = conclusions
      .split(",")
      .map((item) => item.trim().toUpperCase())
      .filter((item): item is ScreenerConclusionFilter =>
        ["BUY", "HOLD", "SELL"].includes(item),
      );
  }

  const columns = searchParams.get("columns");
  if (columns) {
    state.visibleColumns = sortColumnsByCanonicalOrder(
      columns.split(",").filter(Boolean) as ScreenerColumnKey[],
    );
  }

  return state;
}

export function countActiveFilters(state: ScreenerUiState): number {
  let count = 0;

  if (state.index && state.index !== "all") count++;
  if (state.sector && state.sector !== "all") count++;

  for (const key of NUMERIC_FILTER_KEYS) {
    if (state[key] !== undefined && state[key] !== null) count++;
  }

  if (state.ma50 && state.ma50 !== "all") count++;
  if (state.ma200 && state.ma200 !== "all") count++;
  if (state.nearExtreme && state.nearExtreme !== "all") count++;
  if (state.hasReport && state.hasReport !== "all") count++;
  if (state.conclusions && state.conclusions.length > 0) count++;

  return count;
}

export function getActiveFilterChips(state: ScreenerUiState): string[] {
  const chips: string[] = [];

  if (state.index && state.index !== "all")
    chips.push(
      `Index: ${state.index === "spx" ? "S&P 500" : "NASDAQ 100"}`,
    );
  if (state.sector && state.sector !== "all")
    chips.push(`Sector: ${state.sector}`);
  if (state.marketCapMin !== undefined)
    chips.push(`MCap ≥ $${(state.marketCapMin / 1e9).toFixed(0)}B`);
  if (state.marketCapMax !== undefined)
    chips.push(`MCap ≤ $${(state.marketCapMax / 1e9).toFixed(0)}B`);
  if (state.forwardPeMin !== undefined)
    chips.push(`Fwd P/E ≥ ${state.forwardPeMin}x`);
  if (state.forwardPeMax !== undefined)
    chips.push(`Fwd P/E ≤ ${state.forwardPeMax}x`);
  if (state.vsSpxMin !== undefined) chips.push(`vs SPX ≥ ${state.vsSpxMin}x`);
  if (state.vsSpxMax !== undefined) chips.push(`vs SPX ≤ ${state.vsSpxMax}x`);
  if (state.pegMax !== undefined) chips.push(`PEG ≤ ${state.pegMax}`);
  if (state.revenueGrowthMin !== undefined)
    chips.push(`Rev Gr ≥ ${state.revenueGrowthMin}%`);
  if (state.earningsGrowthMin !== undefined)
    chips.push(`EPS Gr ≥ ${state.earningsGrowthMin}%`);
  if (state.roeMin !== undefined) chips.push(`ROE ≥ ${state.roeMin}%`);
  if (state.profitMarginMin !== undefined)
    chips.push(`Margin ≥ ${state.profitMarginMin}%`);
  if (state.dividendYieldMin !== undefined)
    chips.push(`Div Yield ≥ ${state.dividendYieldMin}%`);
  if (state.ma50 === "above") chips.push("Above MA50");
  if (state.ma50 === "below") chips.push("Below MA50");
  if (state.ma200 === "above") chips.push("Above MA200");
  if (state.ma200 === "below") chips.push("Below MA200");
  if (state.nearExtreme === "high") chips.push("Near 52W High");
  if (state.nearExtreme === "low") chips.push("Near 52W Low");
  if (state.hasReport === "yes") chips.push("Has AI Report");
  if (state.hasReport === "no") chips.push("No AI Report");
  if (state.conclusions && state.conclusions.length > 0)
    chips.push(`AI: ${state.conclusions.join(", ")}`);

  return chips;
}

export function toApiQuery(state: ScreenerUiState): ScreenerListQuery {
  const {
    searchInput: _searchInput,
    visibleColumns: _visibleColumns,
    showMoreFilters: _showMoreFilters,
    ...query
  } = state;
  return query;
}

export function getApiQueryKey(state: ScreenerUiState): string {
  return JSON.stringify(toApiQuery(state));
}

/**
 * Fully resets every filter/search/sort field back to defaults.
 * Display preferences (visible columns, more-filters panel open state)
 * are preserved since they aren't "filters" in the user's mental model.
 */
export function resetAllFilters(state: ScreenerUiState): ScreenerUiState {
  return {
    ...DEFAULT_UI_STATE,
    visibleColumns: state.visibleColumns,
    showMoreFilters: state.showMoreFilters,
  };
}

export type PageRangeItem = number | "ellipsis";

export function getPageRange(current: number, total: number): PageRangeItem[] {
  if (total <= 1) return [1];

  const delta = 1;
  const range: PageRangeItem[] = [];
  const left = Math.max(2, current - delta);
  const right = Math.min(total - 1, current + delta);

  range.push(1);
  if (left > 2) range.push("ellipsis");
  for (let i = left; i <= right; i++) range.push(i);
  if (right < total - 1) range.push("ellipsis");
  if (total > 1) range.push(total);

  return range;
}
