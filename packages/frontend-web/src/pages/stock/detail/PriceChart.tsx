import { useEffect, useMemo, useRef, useState } from "react";
import type {
  DailyPricePoint,
  InvestmentReportHistoryItem,
  StockNewsItem,
} from "@stock-analyst/api-types";
import { formatDate, type DailyChangeInfo } from "./utils";
import { rankDayNews } from "./newsRanking";

interface PriceChartProps {
  prices: DailyPricePoint[];
  history: InvestmentReportHistoryItem[];
  news: StockNewsItem[];
  targetPrice: number | null;
  dailyChanges: DailyChangeInfo[];
  onNewsMarkerClick?: (date: string) => void;
  height?: number;
}

type ConclusionKind = "BUY" | "SELL" | "HOLD";

const PADDING = { top: 28, right: 16, bottom: 28, left: 64 };
// If the target price sits further than this from the last close, it would
// distort the y-axis too much to plot inline — show a text callout instead.
const TARGET_MAX_DEVIATION = 0.3;

const CONCLUSION_COLORS: Record<ConclusionKind, string> = {
  BUY: "#4ade80",
  SELL: "#f87171",
  HOLD: "#facc15",
};

function formatPrice(value: number): string {
  // Decimal columns can arrive from the API as numeric strings (TypeORM
  // quirk), so coerce defensively rather than trusting the declared type.
  return `$${Number(value).toFixed(2)}`;
}

function getConclusionKind(conclusion: string | null): ConclusionKind {
  const c = (conclusion || "").toUpperCase();
  if (c.includes("BUY")) return "BUY";
  if (c.includes("SELL")) return "SELL";
  return "HOLD";
}

/** Rounds a [min, max] domain to human-friendly gridline values. */
function niceTicks(min: number, max: number, count = 5): number[] {
  if (min === max) return [min];
  const range = max - min;
  const roughStep = range / (count - 1);
  const magnitude = 10 ** Math.floor(Math.log10(roughStep));
  const residual = roughStep / magnitude;

  let niceStep: number;
  if (residual > 5) niceStep = 10 * magnitude;
  else if (residual > 2) niceStep = 5 * magnitude;
  else if (residual > 1) niceStep = 2 * magnitude;
  else niceStep = magnitude;

  const niceMin = Math.floor(min / niceStep) * niceStep;
  const niceMax = Math.ceil(max / niceStep) * niceStep;

  const ticks: number[] = [];
  for (let v = niceMin; v <= niceMax + niceStep / 2; v += niceStep) {
    ticks.push(Number(v.toFixed(6)));
  }
  return ticks;
}

function LegendDot({
  color,
  label,
  outline = false,
}: {
  color: string;
  label: string;
  outline?: boolean;
}) {
  return (
    <span className="flex items-center gap-1 whitespace-nowrap">
      <span
        className="inline-block w-2 h-2 rounded-full"
        style={
          outline
            ? { border: `1.5px solid ${color}`, background: "#111827" }
            : { background: color }
        }
      />
      {label}
    </span>
  );
}

export default function PriceChart({
  prices,
  history,
  news,
  targetPrice,
  dailyChanges,
  onNewsMarkerClick,
  height = 260,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [hoveredSignalId, setHoveredSignalId] = useState<number | null>(null);
  const [hoveredAnomalyDate, setHoveredAnomalyDate] = useState<string | null>(
    null,
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setWidth(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const newsByDate = useMemo(() => {
    const map = new Map<string, StockNewsItem[]>();
    for (const item of news) {
      const list = map.get(item.date) ?? [];
      list.push(item);
      map.set(item.date, list);
    }
    return map;
  }, [news]);

  const changeByDate = useMemo(() => {
    const map = new Map<string, DailyChangeInfo>();
    for (const info of dailyChanges) map.set(info.date, info);
    return map;
  }, [dailyChanges]);

  const chart = useMemo(() => {
    if (prices.length < 2 || width <= 0) return null;

    const innerWidth = Math.max(0, width - PADDING.left - PADDING.right);
    const innerHeight = Math.max(0, height - PADDING.top - PADDING.bottom);

    const closes = prices.map((p) => p.close);
    let min = Math.min(...closes);
    let max = Math.max(...closes);

    const lastClose = closes[closes.length - 1];
    const targetPctDiff =
      targetPrice !== null && lastClose > 0
        ? ((targetPrice - lastClose) / lastClose) * 100
        : null;
    const targetWithinRange =
      targetPctDiff !== null &&
      Math.abs(targetPctDiff) / 100 <= TARGET_MAX_DEVIATION;

    if (targetWithinRange && targetPrice !== null) {
      min = Math.min(min, targetPrice);
      max = Math.max(max, targetPrice);
    }

    // Breathing room so the line/markers don't hug the plot edges.
    const range = max - min || Math.max(max, 1) * 0.1;
    min -= range * 0.08;
    max += range * 0.08;

    const xForIndex = (index: number) =>
      PADDING.left + (index / (prices.length - 1)) * innerWidth;
    const yForPrice = (price: number) =>
      PADDING.top + innerHeight - ((price - min) / (max - min)) * innerHeight;

    const points = prices.map((point, index) => ({
      x: xForIndex(index),
      y: yForPrice(point.close),
      point,
    }));

    const bottomY = PADDING.top + innerHeight;
    const linePath = points
      .map(
        (p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`,
      )
      .join(" ");
    const areaPath = `${linePath} L${points[points.length - 1].x.toFixed(1)},${bottomY.toFixed(1)} L${points[0].x.toFixed(1)},${bottomY.toFixed(1)} Z`;

    const isUp = lastClose >= closes[0];

    const priceTicks = niceTicks(min, max, 5).filter(
      (t) => t >= min && t <= max,
    );

    const dateTickCount = Math.min(6, prices.length);
    const dateTickIndices = Array.from({ length: dateTickCount }, (_, i) =>
      Math.round((i / (dateTickCount - 1 || 1)) * (prices.length - 1)),
    ).filter((v, i, arr) => arr.indexOf(v) === i);

    // AI signal markers: map each history entry to the nearest trading day
    // in the visible window, tolerating a few days of slop for
    // weekends/holidays around the report's generatedAt timestamp.
    const maxSignalDiffMs = 4 * 24 * 60 * 60 * 1000;
    const signalMarkers = history
      .map((item) => {
        const generatedTime = new Date(item.generatedAt.slice(0, 10)).getTime();
        if (Number.isNaN(generatedTime)) return null;

        let closestIndex = -1;
        let closestDiff = Infinity;
        prices.forEach((p, index) => {
          const diff = Math.abs(new Date(p.date).getTime() - generatedTime);
          if (diff < closestDiff) {
            closestDiff = diff;
            closestIndex = index;
          }
        });

        if (closestIndex === -1 || closestDiff > maxSignalDiffMs) return null;

        return {
          history: item,
          kind: getConclusionKind(item.conclusion),
          x: points[closestIndex].x,
          y: points[closestIndex].y,
        };
      })
      .filter((m): m is NonNullable<typeof m> => m !== null);

    const anomalyMarkers = points
      .filter((p) => changeByDate.get(p.point.date)?.isAnomaly)
      .map((p) => ({
        ...p,
        hasNews: (newsByDate.get(p.point.date)?.length ?? 0) > 0,
      }));

    return {
      points,
      linePath,
      areaPath,
      isUp,
      min,
      max,
      priceTicks,
      dateTickIndices,
      yForPrice,
      signalMarkers,
      anomalyMarkers,
      targetWithinRange,
      targetPctDiff,
      innerWidth,
      innerHeight,
      bottomY,
    };
  }, [prices, width, height, targetPrice, history, changeByDate, newsByDate]);

  const handleMouseMove = (event: React.MouseEvent<SVGSVGElement>) => {
    if (!chart || width <= 0) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const relativeX = ((event.clientX - rect.left) / rect.width) * width;

    let closestIndex = 0;
    let closestDist = Infinity;
    chart.points.forEach((p, i) => {
      const dist = Math.abs(p.x - relativeX);
      if (dist < closestDist) {
        closestDist = dist;
        closestIndex = i;
      }
    });
    setHoverIndex(closestIndex);
  };

  const strokeColor = chart?.isUp ? "#4ade80" : "#f87171";
  const hoveredPoint = hoverIndex !== null ? chart?.points[hoverIndex] : null;
  const hoveredSignal =
    hoveredSignalId !== null
      ? chart?.signalMarkers.find((m) => m.history.id === hoveredSignalId)
      : null;
  const hoveredAnomaly =
    hoveredAnomalyDate !== null
      ? chart?.anomalyMarkers.find((m) => m.point.date === hoveredAnomalyDate)
      : null;

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
          30-Day Price Action
        </h3>
        <div className="flex items-center gap-3 text-[10px] text-gray-500">
          <LegendDot color={CONCLUSION_COLORS.BUY} label="AI Buy" />
          <LegendDot color={CONCLUSION_COLORS.HOLD} label="AI Hold" />
          <LegendDot color={CONCLUSION_COLORS.SELL} label="AI Sell" />
          <LegendDot color="#a78bfa" label="Move + News" outline />
          <LegendDot color="#6b7280" label="Move (no news)" outline />
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 border-t border-dashed border-blue-400" />
            Target
          </span>
        </div>
      </div>

      {targetPrice !== null &&
        chart &&
        !chart.targetWithinRange &&
        chart.targetPctDiff !== null && (
          <div className="mb-3 text-xs bg-blue-950/40 border border-blue-900 text-blue-300 rounded px-3 py-1.5 inline-block">
            AI Target {formatPrice(targetPrice)} is{" "}
            {chart.targetPctDiff > 0 ? "+" : ""}
            {chart.targetPctDiff.toFixed(0)}% away — off-chart
          </div>
        )}

      <div ref={containerRef} className="relative w-full" style={{ height }}>
        {chart ? (
          <svg
            viewBox={`0 0 ${width} ${height}`}
            width={width}
            height={height}
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoverIndex(null)}
          >
            <defs>
              <linearGradient
                id="price-chart-fill"
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor={strokeColor} stopOpacity="0.25" />
                <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
              </linearGradient>
            </defs>

            {chart.priceTicks.map((tick) => {
              const y = chart.yForPrice(tick);
              return (
                <g key={tick}>
                  <line
                    x1={PADDING.left}
                    x2={width - PADDING.right}
                    y1={y}
                    y2={y}
                    stroke="#374151"
                    strokeWidth={1}
                    strokeDasharray="2,3"
                  />
                  <text
                    x={PADDING.left - 8}
                    y={y}
                    textAnchor="end"
                    dominantBaseline="middle"
                    fontSize={10}
                    fill="#6b7280"
                  >
                    {formatPrice(tick)}
                  </text>
                </g>
              );
            })}

            {chart.dateTickIndices.map((index) => (
              <text
                key={index}
                x={chart.points[index].x}
                y={height - 8}
                textAnchor="middle"
                fontSize={10}
                fill="#6b7280"
              >
                {formatDate(chart.points[index].point.date)}
              </text>
            ))}

            {targetPrice !== null && chart.targetWithinRange && (
              <g>
                <line
                  x1={PADDING.left}
                  x2={width - PADDING.right}
                  y1={chart.yForPrice(targetPrice)}
                  y2={chart.yForPrice(targetPrice)}
                  stroke="#60a5fa"
                  strokeWidth={1.5}
                  strokeDasharray="5,4"
                />
                <text
                  x={width - PADDING.right}
                  y={chart.yForPrice(targetPrice) - 4}
                  textAnchor="end"
                  fontSize={10}
                  fontWeight="bold"
                  fill="#60a5fa"
                >
                  Target {formatPrice(targetPrice)}
                </text>
              </g>
            )}

            <path d={chart.areaPath} fill="url(#price-chart-fill)" />
            <path
              d={chart.linePath}
              fill="none"
              stroke={strokeColor}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />

            {chart.anomalyMarkers.map((m) => (
              <circle
                key={`anomaly-${m.point.date}`}
                cx={m.x}
                cy={m.y}
                r={hoveredAnomalyDate === m.point.date ? 6 : 4}
                fill="#111827"
                stroke={m.hasNews ? "#a78bfa" : "#6b7280"}
                strokeWidth={2}
                strokeDasharray={m.hasNews ? undefined : "2,2"}
                className={m.hasNews ? "cursor-pointer" : undefined}
                onMouseEnter={() => setHoveredAnomalyDate(m.point.date)}
                onMouseLeave={() => setHoveredAnomalyDate(null)}
                onClick={
                  m.hasNews
                    ? () => onNewsMarkerClick?.(m.point.date)
                    : undefined
                }
              />
            ))}

            {chart.signalMarkers.map((m) => {
              const badgeY = PADDING.top - 10;
              const color = CONCLUSION_COLORS[m.kind];
              return (
                <g
                  key={`signal-${m.history.id}`}
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredSignalId(m.history.id)}
                  onMouseLeave={() => setHoveredSignalId(null)}
                >
                  <line
                    x1={m.x}
                    x2={m.x}
                    y1={badgeY + 8}
                    y2={m.y}
                    stroke={color}
                    strokeWidth={1}
                    strokeDasharray="2,2"
                    opacity={0.6}
                  />
                  <circle
                    cx={m.x}
                    cy={badgeY}
                    r={8}
                    fill="#111827"
                    stroke={color}
                    strokeWidth={2}
                  />
                  <text
                    x={m.x}
                    y={badgeY}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={9}
                    fontWeight="bold"
                    fill={color}
                  >
                    {m.kind[0]}
                  </text>
                </g>
              );
            })}

            {hoveredPoint && (
              // pointerEvents="none": this decorative overlay sits exactly on
              // top of the AI signal / anomaly markers at the hovered index,
              // so it must not steal their mouseenter/click handling.
              <g pointerEvents="none">
                <line
                  x1={hoveredPoint.x}
                  x2={hoveredPoint.x}
                  y1={PADDING.top}
                  y2={chart.bottomY}
                  stroke="#4b5563"
                  strokeWidth={1}
                  strokeDasharray="2,2"
                />
                <circle
                  cx={hoveredPoint.x}
                  cy={hoveredPoint.y}
                  r={3.5}
                  fill={strokeColor}
                  stroke="#111827"
                  strokeWidth={1.5}
                />
              </g>
            )}
          </svg>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-sm text-gray-600">
            Not enough price history to chart.
          </div>
        )}

        {hoveredAnomaly ? (
          <div
            className={`absolute pointer-events-none bg-gray-900 border rounded px-3 py-2 text-xs shadow-lg z-20 max-w-[240px] ${
              hoveredAnomaly.hasNews ? "border-purple-700" : "border-gray-600"
            }`}
            style={{
              left: hoveredAnomaly.x,
              top: hoveredAnomaly.y,
              transform: "translate(-50%, -100%) translateY(-10px)",
            }}
          >
            <div className="flex items-center justify-between gap-3 mb-1">
              <span className="font-bold text-white">
                {formatDate(hoveredAnomalyDate)}
              </span>
              {(() => {
                const info = hoveredAnomalyDate
                  ? changeByDate.get(hoveredAnomalyDate)
                  : null;
                if (!info || info.changePct === null) return null;
                return (
                  <span
                    className={`font-bold ${info.changePct >= 0 ? "text-green-400" : "text-red-400"}`}
                  >
                    {info.changePct >= 0 ? "+" : ""}
                    {info.changePct.toFixed(1)}%
                  </span>
                );
              })()}
            </div>
            {(() => {
              const topNews = rankDayNews(
                newsByDate.get(hoveredAnomalyDate ?? "") ?? [],
                3,
              );
              if (topNews.length === 0) {
                return (
                  <div className="text-gray-500">
                    No news captured for this move.
                  </div>
                );
              }
              return (
                <ul className="space-y-1">
                  {topNews.map((n) => (
                    <li
                      key={n.id}
                      className="text-gray-300 leading-snug line-clamp-2"
                    >
                      {n.headline}
                    </li>
                  ))}
                </ul>
              );
            })()}
            {hoveredAnomaly.hasNews && (
              <div className="text-gray-600 mt-1.5 italic">
                Click to jump to news
              </div>
            )}
          </div>
        ) : hoveredSignal ? (
          <div
            className="absolute pointer-events-none bg-gray-900 border rounded px-3 py-2 text-xs shadow-lg z-20 whitespace-nowrap"
            style={{
              left: hoveredSignal.x,
              top: PADDING.top - 10 + 14,
              borderColor: CONCLUSION_COLORS[hoveredSignal.kind],
              transform: "translateX(-50%)",
            }}
          >
            <div
              className="font-bold uppercase tracking-wide"
              style={{ color: CONCLUSION_COLORS[hoveredSignal.kind] }}
            >
              {hoveredSignal.history.conclusion || hoveredSignal.kind}
            </div>
            <div className="text-gray-400">
              {formatDate(hoveredSignal.history.generatedAt)}
            </div>
            <div className="text-gray-300">
              Price then:{" "}
              {hoveredSignal.history.priceAtGeneration !== null
                ? formatPrice(hoveredSignal.history.priceAtGeneration)
                : "—"}
            </div>
            {hoveredSignal.history.convictionLevel && (
              <div className="text-gray-500">
                Conviction: {hoveredSignal.history.convictionLevel}
              </div>
            )}
          </div>
        ) : (
          hoveredPoint && (
            <div
              className="absolute pointer-events-none bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs shadow-lg z-10 whitespace-nowrap"
              style={{
                left: hoveredPoint.x,
                top: hoveredPoint.y,
                transform: "translate(-50%, -100%) translateY(-10px)",
              }}
            >
              <div className="text-white font-bold font-mono">
                {formatPrice(hoveredPoint.point.close)}
              </div>
              <div className="text-gray-500">
                {formatDate(hoveredPoint.point.date)}
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
