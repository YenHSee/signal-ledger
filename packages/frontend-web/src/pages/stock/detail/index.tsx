import MarkdownReport from "./MarkdownReport";
import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import FundamentalsPanel from "./FundamentalsPanel";
import type {
  DailyPricePoint,
  FundamentalsProfile,
  InvestmentReportHistoryItem,
  StockNewsItem,
  StockProfile,
} from "@signal-ledger/api-types";
import ThesisSummary from "./ThesisSummary";
import Headline from "./Headline";
import TrackRecord from "./TrackRecord";
import PriceChart from "./PriceChart";
import NewsSection from "./NewsSection";
import { computeDailyChanges } from "./utils";
import {
  getReport,
  getFundamentals,
  getReportHistory,
} from "../../../api/investmentReport";
import { getDailyPrices, getStockNews } from "../../../api/stock";

export default function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<StockProfile | null>(null);
  const [fundamentals, setFundamentals] = useState<FundamentalsProfile | null>(
    null,
  );
  const [history, setHistory] = useState<InvestmentReportHistoryItem[]>([]);
  const [prices, setPrices] = useState<DailyPricePoint[]>([]);
  const [news, setNews] = useState<StockNewsItem[]>([]);
  const [scrollToNewsDate, setScrollToNewsDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let ignore = false;

    const fetchReportDetail = async () => {
      if (!ticker) return;

      setLoading(true);
      setError(null);
      try {
        const [
          profileResult,
          fundamentalsResult,
          historyResult,
          pricesResult,
          newsResult,
        ] = await Promise.allSettled([
          getReport(ticker),
          getFundamentals(ticker),
          getReportHistory(ticker),
          getDailyPrices(ticker),
          getStockNews(ticker),
        ]);

        if (ignore) return;
        if (profileResult.status === "fulfilled") {
          setReport(profileResult.value);
        } else {
          setReport(null);
        }

        if (fundamentalsResult.status === "fulfilled") {
          setFundamentals(fundamentalsResult.value);
        } else {
          setFundamentals(null);
        }

        if (historyResult.status === "fulfilled") {
          setHistory(historyResult.value);
        } else {
          setHistory([]);
        }

        if (pricesResult.status === "fulfilled") {
          setPrices(pricesResult.value);
        } else {
          setPrices([]);
        }

        if (newsResult.status === "fulfilled") {
          setNews(newsResult.value);
        } else {
          setNews([]);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Unable to load report");
        }
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

  const dailyChanges = useMemo(() => computeDailyChanges(prices), [prices]);
  const latestPrice = prices.length > 0 ? prices[prices.length - 1].close : null;
  const displayProfile: StockProfile = report ?? {
    ticker: ticker ?? "",
    current_price: latestPrice ?? fundamentals?.price ?? null,
    target_price: null,
    conclusion: null,
    conviction_level: null,
    upside_downside_pct: null,
    risk_level: null,
    full_report: "No investment report generated yet.",
    reasoning: "Report backfill has not been run for this sample ticker yet.",
    generated_at: new Date(prices[prices.length - 1]?.date ?? 0),
    dayChangePct:
      dailyChanges.length > 0
        ? dailyChanges[dailyChanges.length - 1].changePct
        : null,
    company_identity: { symbol: ticker },
  };

  const handleNewsMarkerClick = (date: string) => {
    // Changing the value triggers NewsSection's internal scroll logic.
    // Reset to null first so the same date can be re-triggered.
    setScrollToNewsDate(null);
    requestAnimationFrame(() => setScrollToNewsDate(date));
  };

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center text-blue-400 font-mono">
        Loading equity research for {ticker}...
      </div>
    );
  }

  if (error || (!report && !fundamentals && prices.length === 0)) {
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
            {report
              ? `Last Generated: ${new Date(report.generated_at).toLocaleString()}`
              : "Report not generated yet"}
          </div>
        </div>
      </div>

      <Headline report={displayProfile} />

      <div className="mb-6">
        <PriceChart
          prices={prices}
          history={history}
          news={news}
          targetPrice={displayProfile.target_price}
          dailyChanges={dailyChanges}
          onNewsMarkerClick={handleNewsMarkerClick}
        />
      </div>

      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        <div className="lg:w-2/3 bg-gray-800 rounded-xl border border-gray-700 p-8 shadow-xl overflow-y-auto">
          <div className="flex items-center justify-between border-b border-gray-700 pb-4 mb-6">
            <h2 className="text-xl font-bold text-white">
              Institutional AI Report
            </h2>
            <span
              className={`text-xs font-bold px-2 py-1 rounded border uppercase tracking-wider
              ${
                displayProfile.conclusion?.includes("BUY")
                  ? "bg-green-900/30 text-green-400 border-green-800"
                  : displayProfile.conclusion?.includes("SELL")
                    ? "bg-red-900/30 text-red-400 border-red-800"
                    : "bg-yellow-900/30 text-yellow-400 border-yellow-800"
              }`}
            >
              Signal: {displayProfile.conclusion || "PENDING"}
            </span>
          </div>

          <MarkdownReport
            content={
              displayProfile.full_report || "No detailed report generated yet."
            }
          />
        </div>

        <div className="lg:w-1/3 flex flex-col gap-6">
          <FundamentalsPanel
            fundamentalsProfile={fundamentals}
            riskLevel={displayProfile.risk_level}
          />

          <ThesisSummary report={displayProfile} />
        </div>
      </div>
      <div className="mt-6">
        <NewsSection
          news={news}
          dailyChanges={dailyChanges}
          scrollToDate={scrollToNewsDate}
        />
      </div>
      <div className="mt-6">
        <TrackRecord
          history={history}
          currentPrice={displayProfile.current_price}
        />
      </div>
    </div>
  );
}
