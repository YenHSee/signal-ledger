import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import {
  SCREENER_SAVED_PRESETS,
  type ScreenerColumnKey,
  type ScreenerIndexFilter,
  type ScreenerListMeta,
  type ScreenerSortField,
  type ScreenerStockItem,
} from "@stock-analyst/api-types";
import ColumnPicker from "./ColumnPicker";
import MoreFilters from "./MoreFilters";
import Pagination from "./Pagination";
import { getScreenerList } from "../../../api/stock";
import {
  buildQueryParams,
  countActiveFilters,
  DEFAULT_UI_STATE,
  formatMarketCap,
  formatPercent,
  formatRatio,
  getActiveFilterChips,
  getSignalColor,
  isPremiumMultiple,
  parseUiStateFromSearchParams,
  resetAllFilters,
  toApiQuery,
  type ScreenerUiState,
  COLUMN_LABELS,
} from "./utils";

const INDEX_OPTIONS: { value: ScreenerIndexFilter; label: string }[] = [
  { value: "all", label: "All (SPX + NDX)" },
  { value: "spx", label: "S&P 500" },
  { value: "ndx", label: "NASDAQ 100" },
];

const SORTABLE_COLUMNS: Partial<Record<ScreenerColumnKey, ScreenerSortField>> =
  {
    ticker: "ticker",
    price: "price",
    marketCap: "marketCap",
    forwardPe: "forwardPe",
    vsSpx: "vsSpx",
    revGrowth: "revenueGrowthYoy",
    analystUpside: "analystUpside",
    roe: "roe",
  };

export default function StockScreener() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [state, setState] = useState<ScreenerUiState>(() =>
    parseUiStateFromSearchParams(searchParams),
  );
  const [stocks, setStocks] = useState<ScreenerStockItem[]>([]);
  const [meta, setMeta] = useState<ScreenerListMeta>({
    totalStocks: 0,
    stocksWithReport: 0,
    spxFwdPe: null,
    sectors: [],
  });
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const patchState = useCallback((patch: Partial<ScreenerUiState>) => {
    setState((prev) => ({ ...prev, ...patch }));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      patchState({
        search: state.searchInput.trim() || undefined,
        page: 1,
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [state.searchInput, patchState]);

  useEffect(() => {
    setSearchParams(buildQueryParams(state), { replace: true });
  }, [state, setSearchParams]);

  const apiQuery = useMemo(
    () => toApiQuery(state),
    [
      state.page,
      state.limit,
      state.index,
      state.sector,
      state.search,
      state.sortBy,
      state.sortOrder,
      state.marketCapMin,
      state.marketCapMax,
      state.forwardPeMin,
      state.forwardPeMax,
      state.vsSpxMin,
      state.vsSpxMax,
      state.pegMax,
      state.revenueGrowthMin,
      state.earningsGrowthMin,
      state.roeMin,
      state.profitMarginMin,
      state.dividendYieldMin,
      state.ma50,
      state.ma200,
      state.nearExtreme,
      state.hasReport,
      state.conclusions?.join(","),
    ],
  );

  const fetchStocks = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();

      Object.entries(apiQuery).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") return;
        if (key === "conclusions" && Array.isArray(value)) {
          if (value.length > 0) params.set(key, value.join(","));
          return;
        }
        if (key === "sector" && value === "all") return;
        if (key === "index" && value === "all") return;
        if (key === "hasReport" && value === "all") return;
        if (key === "ma50" && value === "all") return;
        if (key === "ma200" && value === "all") return;
        if (key === "nearExtreme" && value === "all") return;
        params.set(key, String(value));
      });

      const result = await getScreenerList(params);
      setStocks(result.data || []);
      setMeta(
        result.meta || {
          totalStocks: 0,
          stocksWithReport: 0,
          spxFwdPe: null,
          sectors: [],
        },
      );
      setTotalPages(result.totalPages || 1);
      setTotal(result.total || 0);
    } catch (error) {
      console.error("Fetch error:", error);
    } finally {
      setLoading(false);
    }
  }, [apiQuery]);

  useEffect(() => {
    fetchStocks();
  }, [fetchStocks]);

  const handleSort = (field: ScreenerSortField) => {
    if (state.sortBy === field) {
      patchState({
        sortOrder: state.sortOrder === "desc" ? "asc" : "desc",
        page: 1,
      });
    } else {
      patchState({ sortBy: field, sortOrder: "desc", page: 1 });
    }
  };

  const clearAdvancedFilters = () => {
    // Full reset: presets can set tier-1 fields (index/sector/search/sort)
    // too, so "clear all" must wipe those as well, not just the tier-2
    // advanced filters, otherwise leftover preset filters silently remain.
    setState((prev) => resetAllFilters(prev));
  };

  const applyPreset = (presetId: string) => {
    const preset = SCREENER_SAVED_PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    patchState({
      ...DEFAULT_UI_STATE,
      ...preset.filters,
      page: 1,
      searchInput: state.searchInput,
      visibleColumns: state.visibleColumns,
      showMoreFilters: true,
    });
  };

  const activeFilterCount = countActiveFilters(state);
  const filterChips = getActiveFilterChips(state);

  const SortHeader = ({
    column,
    align = "left",
  }: {
    column: ScreenerColumnKey;
    align?: "left" | "right";
  }) => {
    const sortField = SORTABLE_COLUMNS[column];
    if (!sortField) {
      return (
        <th
          className={`py-3 px-4 ${align === "right" ? "text-right" : "text-left"}`}
        >
          {COLUMN_LABELS[column]}
        </th>
      );
    }

    return (
      <th
        className={`py-3 px-4 cursor-pointer select-none hover:text-gray-200 transition-colors ${
          align === "right" ? "text-right" : "text-left"
        }`}
        onClick={() => handleSort(sortField)}
      >
        <span className="inline-flex items-center gap-1">
          {COLUMN_LABELS[column]}
          {state.sortBy === sortField && (
            <ChevronDown
              size={14}
              className={`transition-transform ${state.sortOrder === "asc" ? "rotate-180" : ""}`}
            />
          )}
        </span>
      </th>
    );
  };

  const rightAlignedColumns = new Set<ScreenerColumnKey>([
    "price",
    "marketCap",
    "forwardEps",
    "forwardPe",
    "vsSpx",
    "revGrowth",
    "analystUpside",
    "roe",
    "pctFrom52wHigh",
  ]);

  return (
    <div className="w-full h-full text-gray-200">
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <div className="relative">
          <select
            value={state.index ?? "all"}
            onChange={(e) =>
              patchState({
                index: e.target.value as ScreenerIndexFilter,
                page: 1,
              })
            }
            className="appearance-none bg-gray-800 border border-gray-700 rounded-lg pl-3 pr-8 py-2 text-sm text-gray-200 focus:outline-none focus:border-gray-500 cursor-pointer"
          >
            {INDEX_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown
            size={14}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
          />
        </div>

        <div className="relative">
          <select
            value={state.sector ?? "all"}
            onChange={(e) => patchState({ sector: e.target.value, page: 1 })}
            className="appearance-none bg-gray-800 border border-gray-700 rounded-lg pl-3 pr-8 py-2 text-sm text-gray-200 focus:outline-none focus:border-gray-500 cursor-pointer"
          >
            <option value="all">All Sectors</option>
            {meta.sectors.map((sector) => (
              <option key={sector} value={sector}>
                {sector}
              </option>
            ))}
          </select>
          <ChevronDown
            size={14}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
          />
        </div>

        <input
          type="text"
          placeholder="Search ticker or name..."
          value={state.searchInput}
          onChange={(e) => patchState({ searchInput: e.target.value })}
          className="flex-1 min-w-[200px] bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-gray-500"
        />

        <div className="flex items-center gap-2">
          <ColumnPicker
            visibleColumns={state.visibleColumns}
            onChange={(columns) => patchState({ visibleColumns: columns })}
          />

          <div className="relative group">
            <button
              type="button"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Presets
              <ChevronDown size={14} />
            </button>
            <div className="absolute right-0 top-full mt-1 z-20 hidden group-hover:block group-focus-within:block">
              <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 min-w-[180px]">
                {SCREENER_SAVED_PRESETS.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => applyPreset(preset.id)}
                    className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white"
                  >
                    {preset.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="text-sm text-gray-400 whitespace-nowrap ml-auto">
          {meta.totalStocks.toLocaleString()} stocks
          <span> | {meta.stocksWithReport.toLocaleString()} w/ AI</span>
          {meta.spxFwdPe !== null && (
            <span> | SPX Fwd PE: {meta.spxFwdPe.toFixed(1)}x</span>
          )}
        </div>
      </div>

      <MoreFilters
        state={state}
        onChange={patchState}
        onClear={clearAdvancedFilters}
        activeCount={activeFilterCount}
      />

      {filterChips.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {filterChips.map((chip) => (
            <span
              key={chip}
              className="px-2.5 py-1 text-xs bg-gray-800 border border-gray-700 rounded-full text-gray-300"
            >
              {chip}
            </span>
          ))}
        </div>
      )}

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-xl overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[900px]">
          <thead>
            <tr className="border-b border-gray-700 bg-gray-900/40 text-gray-400 text-xs font-bold uppercase tracking-wider">
              {state.visibleColumns.map((column) => (
                <SortHeader
                  key={column}
                  column={column}
                  align={rightAlignedColumns.has(column) ? "right" : "left"}
                />
              ))}
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-700/60 text-sm">
            {loading ? (
              <tr>
                <td
                  colSpan={state.visibleColumns.length}
                  className="p-8 text-center text-gray-500"
                >
                  Scanning Markets...
                </td>
              </tr>
            ) : stocks.length === 0 ? (
              <tr>
                <td
                  colSpan={state.visibleColumns.length}
                  className="p-8 text-center text-gray-500"
                >
                  No stocks found
                </td>
              </tr>
            ) : (
              stocks.map((stock) => (
                <tr
                  key={stock.ticker}
                  onClick={() => navigate(`/stock/${stock.ticker}`)}
                  className="hover:bg-gray-700/60 cursor-pointer transition-all"
                >
                  {state.visibleColumns.map((column) => (
                    <RenderCell key={column} stock={stock} column={column} />
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        page={state.page ?? 1}
        totalPages={totalPages}
        limit={state.limit ?? 100}
        total={total}
        loading={loading}
        onPageChange={(page) => patchState({ page })}
        onLimitChange={(limit) => patchState({ limit, page: 1 })}
      />
    </div>
  );
}

function RenderCell({
  stock,
  column,
}: {
  stock: ScreenerStockItem;
  column: ScreenerColumnKey;
}) {
  const premium = isPremiumMultiple(stock.vsSpx);

  switch (column) {
    case "ticker":
      return (
        <td className="py-3 px-4 font-bold text-blue-400">{stock.ticker}</td>
      );
    case "company":
      return <td className="py-3 px-4 text-gray-300">{stock.name}</td>;
    case "sector":
      return <td className="py-3 px-4 text-gray-400">{stock.sector || "—"}</td>;
    case "price":
      return (
        <td className="py-3 px-4 text-right font-semibold text-white">
          {stock.price !== null ? stock.price.toFixed(2) : "—"}
        </td>
      );
    case "marketCap":
      return (
        <td className="py-3 px-4 text-right text-gray-300">
          {formatMarketCap(stock.marketCap)}
        </td>
      );
    case "forwardEps":
      return (
        <td className="py-3 px-4 text-right text-gray-300">
          {stock.forwardEps !== null ? `$${stock.forwardEps.toFixed(2)}` : "—"}
        </td>
      );
    case "forwardPe":
      return (
        <td
          className={`py-3 px-4 text-right font-medium ${
            premium ? "text-orange-400" : "text-gray-300"
          }`}
        >
          {formatRatio(stock.forwardPe)}
        </td>
      );
    case "vsSpx":
      return (
        <td
          className={`py-3 px-4 text-right font-medium ${
            premium ? "text-orange-400" : "text-gray-300"
          }`}
        >
          {formatRatio(stock.vsSpx)}
        </td>
      );
    case "ai":
      return (
        <td className="py-3 px-4">
          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded text-xs font-bold border ${getSignalColor(stock.aiSignal)}`}
            >
              {stock.aiSignal || "AWAITING"}
            </span>
            {stock.upsidePct && (
              <span
                className={`text-xs font-bold ${
                  stock.upsidePct.includes("-")
                    ? "text-red-400"
                    : "text-green-400"
                }`}
              >
                {stock.upsidePct}
              </span>
            )}
          </div>
        </td>
      );
    case "revGrowth":
      return (
        <td className="py-3 px-4 text-right text-gray-300">
          {formatPercent(stock.revenueGrowthYoy)}
        </td>
      );
    case "analystUpside":
      return (
        <td
          className={`py-3 px-4 text-right font-medium ${
            stock.analystUpside !== null && stock.analystUpside > 0
              ? "text-green-400"
              : stock.analystUpside !== null && stock.analystUpside < 0
                ? "text-red-400"
                : "text-gray-300"
          }`}
        >
          {formatPercent(stock.analystUpside)}
        </td>
      );
    case "roe":
      return (
        <td className="py-3 px-4 text-right text-gray-300">
          {formatPercent(stock.roe)}
        </td>
      );
    case "pctFrom52wHigh":
      return (
        <td className="py-3 px-4 text-right text-gray-300">
          {formatPercent(stock.pctFrom52wHigh)}
        </td>
      );
    default:
      return null;
  }
}
