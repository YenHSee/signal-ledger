import type { DailyPricePoint } from "@signal-ledger/api-types";

export interface DailyChangeInfo {
  date: string;
  close: number;
  volume?: number;
  changePct: number | null;
  avgVolume30d: number | null;
  isAnomaly: boolean;
}

/**
 * Flags "anomaly" days used to surface news markers on the price chart:
 * a single-day move of >= 2% or volume >= 2x the trailing 30-day average.
 */
export function computeDailyChanges(
  prices: DailyPricePoint[],
): DailyChangeInfo[] {
  return prices.map((point, index) => {
    const prev = index > 0 ? prices[index - 1] : null;
    const changePct =
      prev && prev.close
        ? ((point.close - prev.close) / prev.close) * 100
        : null;

    const volumeWindow = prices
      .slice(Math.max(0, index - 29), index + 1)
      .map((p) => p.volume)
      .filter((v): v is number => typeof v === "number");
    const avgVolume30d =
      volumeWindow.length > 0
        ? volumeWindow.reduce((sum, v) => sum + v, 0) / volumeWindow.length
        : null;

    const isBigMove = changePct !== null && Math.abs(changePct) >= 2;
    const isVolumeSpike =
      point.volume !== undefined &&
      avgVolume30d !== null &&
      point.volume >= avgVolume30d * 2;

    return {
      date: point.date,
      close: point.close,
      volume: point.volume,
      changePct,
      avgVolume30d,
      isAnomaly: isBigMove || isVolumeSpike,
    };
  });
}

export function formatCurrency(value: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value}`;
  // return `$${value.toFixed(decimals)}`;
}

export function formatPercent(value: number | null, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatRatio(value: number | null, suffix = "x"): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(2)}${suffix}`;
}

export function formatMarketCap(value: number | null): string {
  if (value === null || value === undefined) return "—";
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  return `$${value.toLocaleString()}`;
}

export function formatDate(value: string | Date | null): string {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    // Report and market-data dates are calendar dates. Formatting them in the
    // browser timezone turns a 21:00Z analysis timestamp into the next day in
    // Asia, so always preserve the UTC calendar date here.
    timeZone: "UTC",
  });
}

export function formatDateTime(value: string | Date | null): string {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString();
}

export function getConclusionColor(conclusion: string | null): string {
  if (!conclusion) return "text-gray-400 bg-gray-800 border-gray-600";
  const c = conclusion.toUpperCase();
  if (c.includes("BUY"))
    return "text-green-400 bg-green-900/30 border-green-800";
  if (c.includes("SELL")) return "text-red-400 bg-red-900/30 border-red-800";
  return "text-yellow-400 bg-yellow-900/30 border-yellow-800";
}

export function getConvictionColor(conviction: string | null): string {
  if (!conviction) return "text-yellow-400";
  const c = conviction.toUpperCase();
  if (c.includes("HIGH")) return "text-green-400";
  if (c.includes("LOW")) return "text-red-400";
  return "text-yellow-400";
}

export function getChangeColor(value: number | null): string {
  if (value === null || value === undefined) return "text-gray-400";
  if (value > 0) return "text-green-400";
  if (value < 0) return "text-red-400";
  return "text-gray-400";
}

/**
 * Returns 0-100: where `value` sits between `low` and `high`.
 * Used for the 52-week range progress bar.
 */
export function getRangePosition(
  value: number | null,
  low: number | null,
  high: number | null,
): number | null {
  if (value === null || low === null || high === null || high <= low) {
    return null;
  }
  const pct = ((value - low) / (high - low)) * 100;
  return Math.min(100, Math.max(0, pct));
}

export function getMaStatus(
  price: number | null,
  ma: number | null,
): { label: string; color: string } {
  if (price === null || ma === null) {
    return { label: "N/A", color: "text-gray-500" };
  }
  return price >= ma
    ? { label: "Above", color: "text-green-400" }
    : { label: "Below", color: "text-red-400" };
}
