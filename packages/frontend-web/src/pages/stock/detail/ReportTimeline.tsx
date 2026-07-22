import type { InvestmentReportHistoryItem } from "@signal-ledger/api-types";
import { formatDate, getConclusionColor } from "./utils";

interface ReportTimelineProps {
  history: InvestmentReportHistoryItem[];
  selectedReportId: number | null;
  onSelect: (reportId: number) => void;
}

export default function ReportTimeline({
  history,
  selectedReportId,
  onSelect,
}: ReportTimelineProps) {
  if (history.length === 0) return null;

  const latestReportId = history[0].id;
  const chronological = [...history].reverse();

  return (
    <section className="mb-6 rounded-xl border border-gray-700 bg-gray-800 p-5 shadow-xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-gray-300">
            Report Timeline
          </h2>
          <p className="mt-1 text-xs text-gray-500">
            Select the point-in-time analysis you want to review.
          </p>
        </div>
        <span className="text-xs text-gray-500">
          {history.length} frozen reports
        </span>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-1">
        {chronological.map((item) => {
          const selected = item.id === selectedReportId;
          const latest = item.id === latestReportId;

          return (
            <button
              key={item.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect(item.id)}
              className={`min-w-[132px] rounded-lg border px-4 py-3 text-left transition-colors ${
                selected
                  ? "border-blue-500 bg-blue-500/10 ring-1 ring-blue-500/40"
                  : "border-gray-700 bg-gray-900/40 hover:border-gray-500 hover:bg-gray-700/50"
              }`}
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-gray-200">
                  {formatDate(item.analysisAsOf ?? item.generatedAt)}
                </span>
                {latest && (
                  <span className="rounded bg-blue-900/50 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-blue-300">
                    Latest
                  </span>
                )}
              </div>
              <span
                className={`inline-flex rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${getConclusionColor(item.conclusion)}`}
              >
                {item.conclusion ?? "N/A"}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
