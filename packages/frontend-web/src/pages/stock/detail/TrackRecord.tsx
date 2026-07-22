import type { InvestmentReportHistoryItem } from "@signal-ledger/api-types";
import {
  formatCurrency,
  formatDate,
  getChangeColor,
  getConclusionColor,
} from "./utils";

interface TrackRecordProps {
  history: InvestmentReportHistoryItem[];
  selectedReportId: number | null;
  onSelect: (reportId: number) => void;
}

function verdictStyle(verdict: InvestmentReportHistoryItem["verdict"]): string {
  if (verdict === "FAVORABLE") return "text-green-400";
  if (verdict === "ADVERSE" || verdict === "DOWNSIDE_BREAKDOWN") {
    return "text-red-400";
  }
  if (verdict === "UPSIDE_BREAKOUT") return "text-blue-400";
  return "text-gray-400";
}

export default function TrackRecord({
  history,
  selectedReportId,
  onSelect,
}: TrackRecordProps) {
  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
          AI Track Record
        </h3>
        <span className="text-xs text-gray-500">
          Past calls vs. actual outcome
        </span>
      </div>

      {history.length === 0 ? (
        <div className="text-sm text-gray-500 py-6 text-center">
          This is the first generated report — no track record yet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left text-gray-500 text-xs uppercase tracking-wider border-b border-gray-700">
                <th className="py-2 pr-4 font-medium">Date</th>
                <th className="py-2 pr-4 font-medium">Signal</th>
                <th className="py-2 pr-4 font-medium">Conviction</th>
                <th className="py-2 pr-4 font-medium text-right">Price Then</th>
                <th className="py-2 pr-4 font-medium text-right">
                  Target Price
                </th>
                <th className="py-2 pr-4 font-medium text-right">
                  Performance Since
                </th>
                <th className="py-2 font-medium text-center">
                  Interim Verdict
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/60">
              {history.map((item) => {
                const performancePct = item.performanceSincePct;

                return (
                  <tr
                    key={item.id}
                    role="button"
                    tabIndex={0}
                    aria-current={
                      item.id === selectedReportId ? "true" : undefined
                    }
                    onClick={() => onSelect(item.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onSelect(item.id);
                      }
                    }}
                    className={`cursor-pointer text-gray-300 transition-colors hover:bg-gray-700/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500 ${
                      item.id === selectedReportId ? "bg-blue-500/10" : ""
                    }`}
                    title="Open this historical report"
                  >
                    <td className="py-3 pr-4 whitespace-nowrap text-gray-400">
                      {formatDate(item.analysisAsOf ?? item.generatedAt)}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={`text-xs font-bold px-2 py-1 rounded border uppercase tracking-wider ${getConclusionColor(item.conclusion)}`}
                      >
                        {item.conclusion || "N/A"}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-gray-400 whitespace-nowrap">
                      {item.convictionLevel || "—"}
                    </td>
                    <td className="py-3 pr-4 text-right font-mono">
                      {formatCurrency(item.priceAtGeneration)}
                    </td>
                    <td className="py-3 pr-4 text-right font-mono text-blue-400">
                      {formatCurrency(item.targetPrice)}
                    </td>
                    <td
                      className={`py-3 pr-4 text-right font-mono font-bold ${getChangeColor(performancePct)}`}
                    >
                      {performancePct !== null && performancePct !== 0 ? (
                        `${performancePct > 0 ? "+" : ""}${performancePct.toFixed(1)}%`
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                    <td className="py-3 text-center">
                      {item.verdict === null ? (
                        <span className="text-gray-500">—</span>
                      ) : (
                        <span
                          className={`text-xs font-bold ${verdictStyle(item.verdict)}`}
                          title={`${item.verdictStatus ?? "interim"}; ${item.verdictMethod ?? "method unavailable"}`}
                        >
                          {item.verdict.replaceAll("_", " ")}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
