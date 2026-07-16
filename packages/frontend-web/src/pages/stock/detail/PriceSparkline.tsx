import { useMemo, useState } from "react";
import type { DailyPricePoint } from "@signal-ledger/api-types";
import { formatCurrency, formatDate } from "./utils";

interface PriceSparklineProps {
  prices: DailyPricePoint[];
  width?: number;
  height?: number;
}

export default function PriceSparkline({
  prices,
  width = 160,
  height = 48,
}: PriceSparklineProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const chart = useMemo(() => {
    if (prices.length < 2) return null;

    const closes = prices.map((p) => p.close);
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const range = max - min || 1;

    const points = prices.map((point, index) => {
      const x = (index / (prices.length - 1)) * width;
      const y = height - ((point.close - min) / range) * height;
      return { x, y, point };
    });

    const isUp = closes[closes.length - 1] >= closes[0];
    const linePath = points
      .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
      .join(" ");
    const areaPath = `${linePath} L${width},${height} L0,${height} Z`;

    return { points, isUp, linePath, areaPath };
  }, [prices, width, height]);

  if (!chart) {
    return (
      <div
        style={{ width, height }}
        className="flex items-center justify-center text-[10px] text-gray-600"
      >
        No chart data
      </div>
    );
  }

  const { points, isUp, linePath, areaPath } = chart;
  const strokeColor = isUp ? "#4ade80" : "#f87171";
  const hovered = hoverIndex !== null ? points[hoverIndex] : null;

  return (
    <div className="relative" style={{ width, height }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        className="overflow-visible"
        onMouseLeave={() => setHoverIndex(null)}
      >
        <defs>
          <linearGradient id="sparkline-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.25" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#sparkline-fill)" />
        <path
          d={linePath}
          fill="none"
          stroke={strokeColor}
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {hovered && (
          <>
            <line
              x1={hovered.x}
              x2={hovered.x}
              y1={0}
              y2={height}
              stroke="#4b5563"
              strokeWidth={1}
              strokeDasharray="2,2"
            />
            <circle cx={hovered.x} cy={hovered.y} r={2.5} fill={strokeColor} />
          </>
        )}
        {points.map((p, index) => (
          <rect
            key={p.point.date}
            x={p.x - width / points.length / 2}
            y={0}
            width={width / points.length}
            height={height}
            fill="transparent"
            onMouseEnter={() => setHoverIndex(index)}
          />
        ))}
      </svg>
      {hovered && (
        <div className="absolute -top-9 left-0 -translate-x-1/2 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-[10px] whitespace-nowrap shadow-lg z-10 pointer-events-none"
          style={{ left: hovered.x }}
        >
          <div className="text-white font-bold">
            {formatCurrency(hovered.point.close)}
          </div>
          <div className="text-gray-500">{formatDate(hovered.point.date)}</div>
        </div>
      )}
    </div>
  );
}
