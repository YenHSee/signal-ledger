import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";

// 🌟 定义与你 NestJS InvestmentReport Entity 匹配的 TypeScript 接口
interface ReportData {
  ticker: string;
  target_price: number | null;
  conclusion: string | null;
  conviction_level: string | null;
  upside_downside_pct: string | null;
  risk_level: string | null;
  full_report: string;
  reasoning: string;
  generated_at: string;
  raw_financial_data: any; // PostgreSQL jsonb 字段
}

export default function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 🌟 API Fetch 逻辑
  useEffect(() => {
    let ignore = false;

    const fetchReportDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        // 假设你的 NestJS 后端提供了一个根据 ticker 拿最新报告的 API
        // 例如: /api/investment-report/:ticker
        const response = await fetch(
          `http://localhost:4000/api/investment-report/${ticker}`,
        );
        if (!response.ok) throw new Error("Failed to fetch report");

        const data = await response.json();
        if (!ignore) {
          setReport(data);
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

  // 如果正在加载，显示一个酷炫的极客加载状态
  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center text-blue-400 font-mono">
        Retrieving Quantum AI Intel for {ticker}...
      </div>
    );
  }

  // 如果找不到报告（比如用户输入了错的 URL）
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

  // 从 raw_financial_data 提取股票的基础信息 (依赖于你在 Python 里塞进去的数据格式)
  const companyName = report.raw_financial_data?.name || report.ticker;
  const currentPrice =
    report.raw_financial_data?.smart_money_consensus.current_price || "N/A"; // 假设你存了当前价
  const isUp = report.upside_downside_pct?.includes("+"); // 简单的涨跌判断

  // 提取需要展示的 Metrics
  const peRatio =
    report.raw_financial_data?.valuation_and_growth.trailing_pe || "N/A";
  const pegRatio =
    report.raw_financial_data?.valuation_and_growth.peg_ratio || "N/A";
  const marketCap = report.raw_financial_data?.profitability_and_scale
    .market_cap
    ? `$${(report.raw_financial_data.profitability_and_scale.market_cap / 1e9).toFixed(2)}B`
    : "N/A";

  return (
    <div className="w-full min-h-full flex flex-col animate-fade-in text-gray-200">
      {/* ================= Header & Actions ================= */}
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

      {/* ================= 顶层数据面板 (Top Summary) ================= */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6 flex justify-between items-center shadow-lg">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            {report.ticker}
            <span className="text-lg font-medium text-gray-400">
              {companyName}
            </span>
          </h1>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="text-3xl font-bold text-white">
              {currentPrice !== "N/A"
                ? `$${Number(currentPrice).toFixed(2)}`
                : "Price Not Available"}
            </span>
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

      {/* ================= 下方左右分栏 (Markdown vs Lists) ================= */}
      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        {/* 左侧：AI Markdown 研报 */}
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

          {/* 🌟 核心：渲染真实的 Markdown 内容 */}
          {/* 建议以后引入 react-markdown 库来渲染，现在先用 pre 标签保持格式 */}
          <pre className="text-gray-300 font-mono text-sm whitespace-pre-wrap leading-relaxed">
            {report.full_report ||
              report.reasoning ||
              "No detailed report generated yet."}
          </pre>
        </div>

        {/* 右侧：高度结构化的数据列表 */}
        <div className="lg:w-1/3 flex flex-col gap-6">
          {/* 列表 1：Key Financial Metrics */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b border-gray-700 pb-2">
              Extracted Fundamentals
            </h3>
            <ul className="space-y-4">
              <li className="flex justify-between items-center text-sm">
                <span className="text-gray-400">P/E Ratio</span>
                <span className="font-mono font-bold text-white">
                  {peRatio}
                </span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="text-gray-400">PEG Ratio</span>
                <span
                  className={`font-mono font-bold ${Number(pegRatio) > 2 ? "px-2 py-0.5 rounded text-xs bg-red-900/50 text-red-400 border border-red-800" : "text-white"}`}
                >
                  {pegRatio}
                </span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="text-gray-400">Market Cap</span>
                <span className="font-mono font-bold text-white">
                  {marketCap}
                </span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="text-gray-400">Risk Profile</span>
                <span className="font-mono font-bold text-yellow-400 uppercase">
                  {report.risk_level || "Unknown"}
                </span>
              </li>
            </ul>
          </div>

          {/* 列表 2：AI Reasoning Summary */}
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
        </div>
      </div>
    </div>
  );
}
