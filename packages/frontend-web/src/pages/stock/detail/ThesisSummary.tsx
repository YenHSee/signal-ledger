import type { StockProfile } from "@stock-analyst/api-types";

interface ThesisSummaryProps {
  report: StockProfile;
}

export default function ThesisSummary({ report }: ThesisSummaryProps) {
  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl flex-1">
      <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b border-gray-700 pb-2">
        AI Thesis Summary
      </h3>
      <div className="flex flex-col gap-4">
        <div className="text-sm text-gray-300 leading-relaxed italic">
          "{report.reasoning}"
        </div>

        <div className="mt-auto pt-4 border-t border-gray-700/50">
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500">Conviction Level</span>
            <span
              className={`font-bold uppercase tracking-widest
              ${
                report.conviction_level?.includes("High")
                  ? "text-green-400"
                  : report.conviction_level?.includes("Low")
                    ? "text-red-400"
                    : "text-yellow-400"
              }`}
            >
              {report.conviction_level || "N/A"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
