import MarkdownReport from "./MarkdownReport";
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import FundamentalsPanel from "./FundamentalsPanel";
import type {
  DailyPricePoint,
  FundamentalsProfile,
  InvestmentReportHistoryItem,
  StockProfile,
} from "@stock-analyst/api-types";
import ThesisSummary from "./ThesisSummary";
import Headline from "./Headline";
import TrackRecord from "./TrackRecord";

const API_BASE = "http://localhost:4000/api";

export default function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<StockProfile | null>(null);
  const [fundamentals, setFundamentals] = useState<FundamentalsProfile | null>(
    null,
  );
  const [history, setHistory] = useState<InvestmentReportHistoryItem[]>([]);
  const [prices, setPrices] = useState<DailyPricePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let ignore = false;

    const fetchReportDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const [profileResult, fundamentalsResult, historyResult, pricesResult] =
          await Promise.allSettled([
            fetch(`${API_BASE}/investment-report/${ticker}`),
            fetch(`${API_BASE}/investment-report/${ticker}/fundamentals`),
            fetch(`${API_BASE}/investment-report/${ticker}/history`),
            fetch(`${API_BASE}/stock/${ticker}/prices`),
          ]);

        if (ignore) return;
        if (profileResult.status === "fulfilled" && profileResult.value.ok) {
          setReport(await profileResult.value.json());
        } else {
          setReport(null);
        }

        if (
          fundamentalsResult.status === "fulfilled" &&
          fundamentalsResult.value.ok
        ) {
          setFundamentals(await fundamentalsResult.value.json());
        } else {
          setFundamentals(null);
        }

        if (historyResult.status === "fulfilled" && historyResult.value.ok) {
          setHistory(await historyResult.value.json());
        } else {
          setHistory(null);
        }

        if (pricesResult.status === "fulfilled" && pricesResult.value.ok) {
          setPrices(await pricesResult.value.json());
        } else {
          setPrices([]);
        }
      } catch (err: any) {
        if (!ignore) setError(err.message);
      } finally {
        if (!ignore) setLoading(false);
      }
    };

    if (ticker) {
      fetchReportDetail();
    }

    return () => {
      ignore = true;
    };
  }, [ticker]);

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center text-blue-400 font-mono">
        Retrieving Quantum AI Intel for {ticker}...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-red-400 font-mono gap-4">
        <div>Error: Signal Lost for {ticker}</div>
        <button
          onClick={() => navigate(-1)}
          className="text-gray-400 hover:text-white underline"
        >
          Return to Base
        </button>
      </div>
    );
  }

  return (
    <div className="w-full min-h-full flex flex-col animate-fade-in text-gray-200">
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm font-bold"
        >
          <span>←</span> Back to Screener
        </button>
        <div className="flex gap-3">
          <div className="text-xs text-gray-500 flex items-center mr-4">
            Last Generated: {new Date(report.generated_at).toLocaleString()}
          </div>
          <button className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm border border-gray-700 shadow-sm transition-all">
            Export PDF
          </button>
          <button className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-md shadow-blue-900/20 transition-all">
            Force AI Refresh
          </button>
        </div>
      </div>

      <Headline report={report} />

      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        <div className="lg:w-2/3 bg-gray-800 rounded-xl border border-gray-700 p-8 shadow-xl overflow-y-auto">
          <div className="flex items-center justify-between border-b border-gray-700 pb-4 mb-6">
            <h2 className="text-xl font-bold text-white">
              Institutional AI Report
            </h2>
            <span
              className={`text-xs font-bold px-2 py-1 rounded border uppercase tracking-wider
              ${
                report.conclusion?.includes("BUY")
                  ? "bg-green-900/30 text-green-400 border-green-800"
                  : report.conclusion?.includes("SELL")
                    ? "bg-red-900/30 text-red-400 border-red-800"
                    : "bg-yellow-900/30 text-yellow-400 border-yellow-800"
              }`}
            >
              Signal: {report.conclusion || "PENDING"}
            </span>
          </div>

          <MarkdownReport
            content={report.full_report || "No detailed report generated yet."}
          />
        </div>

        <div className="lg:w-1/3 flex flex-col gap-6">
          <FundamentalsPanel
            fundamentalsProfile={fundamentals}
            riskLevel={report.risk_level}
          />

          <ThesisSummary report={report} />
        </div>
      </div>
      <div className="mt-6">
        <TrackRecord history={history} currentPrice={report.current_price} />
      </div>
    </div>
  );
}
