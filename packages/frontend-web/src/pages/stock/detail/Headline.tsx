import type { StockProfile } from "@signal-ledger/api-types";

interface HeadlineProps {
  report: StockProfile;
}

export default function Headline({ report }: HeadlineProps) {
  const isUp = report.upside_downside_pct?.includes("+");
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6 flex justify-between items-center shadow-lg">
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
          {report.ticker}
          <span className="text-lg font-medium text-gray-400">
            {report.company_identity?.name || "-"}
          </span>
        </h1>
        <div className="mt-2 flex items-baseline gap-3">
          <span className="text-3xl font-bold text-white">
            {report.current_price !== null
              ? `$${Number(report.current_price).toFixed(2)}`
              : "Price Not Available"}
          </span>
          {report.dayChangePct !== null && (
            <span
              className={`text-sm font-bold ${report.dayChangePct >= 0 ? "text-green-400" : "text-red-400"}`}
            >
              {report.dayChangePct >= 0 ? "+" : ""}
              {report.dayChangePct.toFixed(2)}% today
            </span>
          )}
          {report.upside_downside_pct && (
            <span
              className={`text-lg font-bold ${isUp ? "text-green-400" : "text-red-400"}`}
            >
              Proj. Upside: {report.upside_downside_pct}
            </span>
          )}
        </div>
      </div>
      <div className="text-right">
        <div className="text-sm text-gray-400 font-medium mb-1">
          AI 12-Month Target
        </div>
        <div className="text-2xl font-bold text-blue-400">
          {report.target_price
            ? `$${Number(report.target_price).toFixed(2)}`
            : "Awaiting Calculation"}
        </div>
      </div>
    </div>
  );
}
