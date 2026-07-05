import type { InvestmentReportHistoryItem } from "@stock-analyst/api-types";
import {
  formatCurrency,
  formatDate,
  getChangeColor,
  getConclusionColor,
} from "./utils";

interface TrackRecordProps {
  history: InvestmentReportHistoryItem[];
  currentPrice: number | null;
}

function computePerformance(
  item: InvestmentReportHistoryItem,
  currentPrice: number | null,
): number | null {
  console.warn("computePerformance", item.priceAtGeneration, currentPrice);
  if (item.priceAtGeneration === null || currentPrice === null) return null;
  if (item.priceAtGeneration === 0) return null;
  return (
    ((currentPrice - item.priceAtGeneration) / item.priceAtGeneration) * 100
  );
}

function isCallCorrect(
  conclusion: string | null,
  performancePct: number | null,
): boolean | null {
  if (!conclusion || performancePct === null) return null;
  const c = conclusion.toUpperCase();
  if (c.includes("BUY")) return performancePct > 0;
  if (c.includes("SELL")) return performancePct < 0;
  return null;
}

export default function TrackRecord({
  history,
  currentPrice,
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
                <th className="py-2 font-medium text-center">Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/60">
              {history.map((item) => {
                const performancePct = computePerformance(item, currentPrice);
                const correct = isCallCorrect(item.conclusion, performancePct);
                console.warn("performancePct", performancePct, correct);

                return (
                  <tr key={item.id} className="text-gray-300">
                    <td className="py-3 pr-4 whitespace-nowrap text-gray-400">
                      {formatDate(item.generatedAt)}
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
                      {correct === null ||
                      (performancePct === 0 && !correct) ? (
                        <span className="text-gray-500">—</span>
                      ) : correct ? (
                        <span
                          className="text-green-400"
                          title="Call played out correctly"
                        >
                          ✓
                        </span>
                      ) : (
                        <span
                          className="text-red-400"
                          title="Call did not play out"
                        >
                          ✕
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
