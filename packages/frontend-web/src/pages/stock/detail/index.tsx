import MarkdownReport from "./MarkdownReport";
import { useState, useEffect, useMemo, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
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
import ReportTimeline from "./ReportTimeline";
import PriceChart from "./PriceChart";
import NewsSection from "./NewsSection";
import { computeDailyChanges, formatDate, formatDateTime } from "./utils";
import { fundamentalsFromSnapshot } from "./snapshotFundamentals";
import {
  getReport,
  getFundamentals,
  getReportHistory,
} from "../../../api/investmentReport";
import { getDailyPrices, getStockNews } from "../../../api/stock";

export default function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const reportSectionRef = useRef<HTMLDivElement>(null);

  const reportIdParam = searchParams.get("report");
  const parsedReportId =
    reportIdParam === null ? undefined : Number(reportIdParam);
  const requestedReportId =
    parsedReportId !== undefined &&
    Number.isInteger(parsedReportId) &&
    parsedReportId > 0
      ? parsedReportId
      : undefined;

  const [report, setReport] = useState<StockProfile | null>(null);
  const [fundamentals, setFundamentals] = useState<FundamentalsProfile | null>(
    null,
  );
  const [history, setHistory] = useState<InvestmentReportHistoryItem[]>([]);
  const [prices, setPrices] = useState<DailyPricePoint[]>([]);
  const [news, setNews] = useState<StockNewsItem[]>([]);
  const [scrollToNewsDate, setScrollToNewsDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (reportIdParam !== null && requestedReportId === undefined) {
      const next = new URLSearchParams(searchParams);
      next.delete("report");
      setSearchParams(next, { replace: true });
    }
  }, [reportIdParam, requestedReportId, searchParams, setSearchParams]);

  useEffect(() => {
    let ignore = false;

    const fetchPageData = async () => {
      if (!ticker) return;

      setLoading(true);
      setError(null);
      try {
        const [fundamentalsResult, historyResult, pricesResult, newsResult] =
          await Promise.allSettled([
            getFundamentals(ticker),
            getReportHistory(ticker),
            getDailyPrices(ticker),
            getStockNews(ticker),
          ]);

        if (ignore) return;
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
          setError(
            err instanceof Error ? err.message : "Unable to load report",
          );
        }
      } finally {
        if (!ignore) setLoading(false);
      }
    };

    if (ticker) {
      fetchPageData();
    }

    return () => {
      ignore = true;
    };
  }, [ticker]);

  useEffect(() => {
    let ignore = false;

    const fetchSelectedReport = async () => {
      if (!ticker) return;
      setReportLoading(true);
      setError(null);
      try {
        const selected = await getReport(ticker, requestedReportId);
        if (!ignore) setReport(selected);
      } catch (err: unknown) {
        if (!ignore) {
          setReport(null);
          setError(
            err instanceof Error ? err.message : "Unable to load report",
          );
        }
      } finally {
        if (!ignore) setReportLoading(false);
      }
    };

    fetchSelectedReport();
    return () => {
      ignore = true;
    };
  }, [ticker, requestedReportId]);

  const dailyChanges = useMemo(() => computeDailyChanges(prices), [prices]);
  const latestPrice =
    prices.length > 0 ? prices[prices.length - 1].close : null;
  const displayProfile: StockProfile = report ?? {
    report_id: 0,
    report_schema_version: null,
    ticker: ticker ?? "",
    analysis_as_of: null,
    generation_mode: null,
    model_tier: null,
    model_provider: null,
    model_name: null,
    prompt_version: null,
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
    raw_financial_data: null,
    agent_outputs: null,
    generation_metadata: null,
    provenance_status: "legacy_incomplete",
  };
  const activeReportId = report?.report_id ?? null;
  const latestReportId = history[0]?.id ?? activeReportId;
  const isLatestReport =
    activeReportId !== null && activeReportId === latestReportId;
  const reportFundamentals =
    fundamentalsFromSnapshot(report?.raw_financial_data ?? null) ??
    fundamentals;

  const handleReportSelect = (reportId: number) => {
    const next = new URLSearchParams(searchParams);
    if (reportId === latestReportId) {
      next.delete("report");
    } else {
      next.set("report", String(reportId));
    }
    setSearchParams(next);
    requestAnimationFrame(() => {
      reportSectionRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  };

  const returnNavigate = () => {
    navigate("/stock/screener");
  };

  const handleNewsMarkerClick = (date: string) => {
    // Changing the value triggers NewsSection's internal scroll logic.
    // Reset to null first so the same date can be re-triggered.
    setScrollToNewsDate(null);
    requestAnimationFrame(() => setScrollToNewsDate(date));
  };

  if (loading || (reportLoading && !report)) {
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
          onClick={() => returnNavigate()}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm font-bold"
        >
          <span>←</span> Back to Screener
        </button>
        <div className="flex gap-3">
          <div className="text-xs text-gray-500 flex items-center mr-4">
            {report
              ? `Generated: ${formatDateTime(report.generated_at)}`
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

      <ReportTimeline
        history={history}
        selectedReportId={activeReportId}
        onSelect={handleReportSelect}
      />

      <div
        ref={reportSectionRef}
        className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0 scroll-mt-6"
      >
        <div
          className={`lg:w-2/3 bg-gray-800 rounded-xl border border-gray-700 p-8 shadow-xl overflow-y-auto transition-opacity ${reportLoading ? "opacity-60" : "opacity-100"}`}
        >
          <div className="flex items-center justify-between border-b border-gray-700 pb-4 mb-6">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-bold text-white">
                  Institutional AI Report
                </h2>
                <span
                  className={`rounded px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${
                    isLatestReport
                      ? "bg-blue-900/50 text-blue-300"
                      : "bg-purple-900/40 text-purple-300"
                  }`}
                >
                  {isLatestReport ? "Latest Report" : "Historical Report"}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                <span>
                  Analysis as of {formatDate(displayProfile.analysis_as_of)}
                </span>
                {!isLatestReport && latestReportId !== null && (
                  <button
                    type="button"
                    onClick={() => handleReportSelect(latestReportId)}
                    className="font-semibold text-blue-400 hover:text-blue-300"
                  >
                    Back to Latest
                  </button>
                )}
              </div>
            </div>
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
            fundamentalsProfile={reportFundamentals}
            riskLevel={displayProfile.risk_level}
            contextLabel={`Point-in-time · ${formatDate(displayProfile.analysis_as_of)}`}
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
          selectedReportId={activeReportId}
          onSelect={handleReportSelect}
        />
      </div>
    </div>
  );
}
