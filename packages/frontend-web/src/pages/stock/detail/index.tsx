import React, { useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";

// ============================================================================
// 🧱 1. 全量 Mock Data Dictionary (模拟真实后端的 JSON 响应)
// ============================================================================
const MOCK_DB: Record<string, any> = {
  NVDA: {
    name: "NVIDIA Corporation",
    price: 127.4,
    change: "+3.4%",
    isUp: true,
    targetPrice: 150.0,
    metrics: [
      { label: "P/E Ratio", value: "65.20" },
      {
        label: "PEG Ratio",
        value: "0.85",
        highlight: "bg-green-900/50 text-green-400 border border-green-800",
      },
      { label: "Market Cap", value: "$3.1T" },
      { label: "Volume", value: "45.2M" },
    ],
    catalysts: [
      {
        time: "2 hours ago",
        text: "Blackwell chip production capacity increased by 15%.",
        sentiment: "Bullish",
      },
      {
        time: "1 day ago",
        text: "New export restrictions rumored, minimal impact expected.",
        sentiment: "Neutral",
      },
    ],
    markdown: `
# NVIDIA (NVDA) - Quantitative AI Analysis

## Executive Summary
Based on the latest macroeconomic data and our proprietary AI models, **NVIDIA** shows a highly favorable PEG ratio of 0.85, indicating that the stock is undervalued relative to its explosive earnings growth.

## Key Technical Indicators
* **Support Level:** $115.20
* **Resistance Level:** $132.50
* **RSI (14-day):** 62.4 (Neutral-Bullish)

## Supply Chain & Alpha Radar
Our AI radar has detected an accelerated supply chain resolution in the TSMC CoWoS packaging line. We project a 12% beat on Q3 consensus revenue.
    `,
  },
  AAPL: {
    name: "Apple Inc.",
    price: 214.32,
    change: "-0.8%",
    isUp: false,
    targetPrice: 230.0,
    metrics: [
      { label: "P/E Ratio", value: "31.50" },
      {
        label: "PEG Ratio",
        value: "2.10",
        highlight: "bg-red-900/50 text-red-400 border border-red-800",
      },
      { label: "Market Cap", value: "$3.2T" },
      { label: "Volume", value: "38.1M" },
    ],
    catalysts: [
      {
        time: "1 hour ago",
        text: "iPhone 16 supply chain checks show stable demand.",
        sentiment: "Neutral",
      },
      {
        time: "2 days ago",
        text: "DOJ antitrust lawsuit developments.",
        sentiment: "Bearish",
      },
    ],
    markdown: `
# Apple (AAPL) - Quantitative AI Analysis

## Executive Summary
Apple's current PEG ratio of 2.10 suggests a premium valuation. While the moat remains strong, short-term AI integrations in iOS 18 are fully priced in.

## Key Technical Indicators
* **Support Level:** $205.00
* **Resistance Level:** $220.00
* **RSI (14-day):** 55.1 (Neutral)
    `,
  },
  MSFT: {
    name: "Microsoft Corporation",
    price: 420.55,
    change: "+1.1%",
    isUp: true,
    targetPrice: 480.0,
    metrics: [
      { label: "P/E Ratio", value: "35.80" },
      { label: "PEG Ratio", value: "1.45" },
      { label: "Market Cap", value: "$3.1T" },
      { label: "Volume", value: "22.4M" },
    ],
    catalysts: [
      {
        time: "4 hours ago",
        text: "Azure cloud growth accelerates due to OpenAI integrations.",
        sentiment: "Bullish",
      },
    ],
    markdown: `
# Microsoft (MSFT) - Quantitative AI Analysis

## Executive Summary
Microsoft continues to lead the enterprise AI monetization cycle. Copilot adoption rates are exceeding initial Wall Street estimates by 18%.

## Key Technical Indicators
* **Support Level:** $410.00
* **Resistance Level:** $430.50
    `,
  },
  AMZN: {
    name: "Amazon.com Inc.",
    price: 189.08,
    change: "+2.3%",
    isUp: true,
    targetPrice: 220.0,
    metrics: [
      { label: "P/E Ratio", value: "41.20" },
      {
        label: "PEG Ratio",
        value: "0.95",
        highlight: "bg-green-900/50 text-green-400 border border-green-800",
      },
      { label: "Market Cap", value: "$1.9T" },
      { label: "Volume", value: "31.2M" },
    ],
    catalysts: [
      {
        time: "30 mins ago",
        text: "AWS announces new custom silicon for AI training.",
        sentiment: "Bullish",
      },
    ],
    markdown: `
# Amazon (AMZN) - Quantitative AI Analysis

## Executive Summary
With a PEG ratio of 0.95, Amazon presents a compelling growth-at-a-reasonable-price (GARP) opportunity. Retail margins are expanding significantly.
    `,
  },
  TSLA: {
    name: "Tesla Inc.",
    price: 178.45,
    change: "-4.2%",
    isUp: false,
    targetPrice: 150.0,
    metrics: [
      { label: "P/E Ratio", value: "58.00" },
      {
        label: "PEG Ratio",
        value: "2.80",
        highlight: "bg-red-900/50 text-red-400 border border-red-800",
      },
      { label: "Market Cap", value: "$560B" },
      { label: "Volume", value: "85.6M" },
    ],
    catalysts: [
      {
        time: "5 hours ago",
        text: "Q1 Delivery numbers miss consensus estimates.",
        sentiment: "Bearish",
      },
      {
        time: "1 day ago",
        text: "Price cuts announced in the European market.",
        sentiment: "Bearish",
      },
    ],
    markdown: `
# Tesla (TSLA) - Quantitative AI Analysis

## Executive Summary
Tesla faces near-term macroeconomic headwinds and intensifying competition in China. The high PEG ratio of 2.80 prices in Robotaxi expectations that may be delayed.
    `,
  },
  JPM: {
    name: "JPMorgan Chase & Co.",
    price: 198.2,
    change: "+0.5%",
    isUp: true,
    targetPrice: 215.0,
    metrics: [
      { label: "P/E Ratio", value: "11.80" },
      { label: "PEG Ratio", value: "1.20" },
      { label: "Market Cap", value: "$570B" },
      { label: "Volume", value: "12.3M" },
    ],
    catalysts: [
      {
        time: "1 day ago",
        text: "Net Interest Income (NII) guidance revised upward.",
        sentiment: "Bullish",
      },
    ],
    markdown: `
# JPMorgan (JPM) - Quantitative AI Analysis

## Executive Summary
A fortress balance sheet and sustained high interest rates keep JPM as the premier holding in the financials sector.
    `,
  },
  GS: {
    name: "The Goldman Sachs Group",
    price: 450.12,
    change: "-1.3%",
    isUp: false,
    targetPrice: 470.0,
    metrics: [
      { label: "P/E Ratio", value: "13.40" },
      { label: "PEG Ratio", value: "1.10" },
      { label: "Market Cap", value: "$150B" },
      { label: "Volume", value: "3.1M" },
    ],
    catalysts: [
      {
        time: "2 days ago",
        text: "M&A advisory revenue slightly below expectations.",
        sentiment: "Neutral",
      },
    ],
    markdown: `
# Goldman Sachs (GS) - Quantitative AI Analysis

## Executive Summary
Investment banking deal flow is showing signs of recovery, but ECM/DCM activities remain highly sensitive to Fed rate cut timing.
    `,
  },
};

// ============================================================================
// 🚀 2. 核心详情页视图组件
// ============================================================================
export default function StockDetail() {
  const { ticker } = useParams();
  const navigate = useNavigate();

  // ⭐️ 核心路由寻址：从 MOCK_DB 提取对应 Ticker 的数据
  const stockData = useMemo(() => {
    // 如果用户输入的 URL ticker 在库里找不到，默认用 NVDA 兜底防崩溃
    return MOCK_DB[ticker || "NVDA"] || MOCK_DB["NVDA"];
  }, [ticker]);

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
          <button className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm border border-gray-700 shadow-sm transition-all">
            Export PDF
          </button>
          <button className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-md shadow-blue-900/20 transition-all">
            Refresh AI Report
          </button>
        </div>
      </div>

      {/* ================= 顶层数据面板 (Top Summary) ================= */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6 flex justify-between items-center shadow-lg">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            {ticker}
            <span className="text-lg font-medium text-gray-400">
              {stockData.name}
            </span>
          </h1>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="text-3xl font-bold text-white">
              ${stockData.price.toFixed(2)}
            </span>
            <span
              className={`text-lg font-bold ${stockData.isUp ? "text-green-400" : "text-red-400"}`}
            >
              {stockData.change} Today
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400 font-medium mb-1">
            AI 12-Month Price Target
          </div>
          <div className="text-2xl font-bold text-blue-400">
            ${stockData.targetPrice.toFixed(2)}
          </div>
        </div>
      </div>

      {/* ================= 下方左右分栏 (Markdown vs Lists) ================= */}
      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        {/* 左侧：AI Markdown 研报 (宽 2/3) */}
        <div className="lg:w-2/3 bg-gray-800 rounded-xl border border-gray-700 p-8 shadow-xl overflow-y-auto">
          <div className="flex items-center justify-between border-b border-gray-700 pb-4 mb-6">
            <h2 className="text-xl font-bold text-white">Deep Dive Report</h2>
            <span className="text-xs text-yellow-500 font-bold bg-yellow-500/10 px-2 py-1 rounded border border-yellow-500/20">
              PRO FEATURE
            </span>
          </div>
          <pre className="text-gray-300 font-mono text-sm whitespace-pre-wrap leading-relaxed">
            {stockData.markdown.trim()}
          </pre>
        </div>

        {/* 右侧：高度结构化的数据列表 (宽 1/3) */}
        <div className="lg:w-1/3 flex flex-col gap-6">
          {/* 列表 1：Key Metrics */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b border-gray-700 pb-2">
              Key Metrics
            </h3>
            <ul className="space-y-4">
              {stockData.metrics.map((metric: any) => (
                <li
                  key={metric.label}
                  className="flex justify-between items-center text-sm"
                >
                  <span className="text-gray-400">{metric.label}</span>
                  <span
                    className={`font-mono font-bold ${metric.highlight || "text-white"}`}
                  >
                    {metric.highlight ? (
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${metric.highlight}`}
                      >
                        {metric.value}
                      </span>
                    ) : (
                      metric.value
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* 列表 2：AI Catalysts */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl flex-1">
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b border-gray-700 pb-2">
              AI Catalysts & News
            </h3>
            <ul className="space-y-4">
              {stockData.catalysts.map((cat: any, index: number) => (
                <li key={index} className="flex flex-col gap-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500">{cat.time}</span>
                    <span
                      className={`font-bold ${cat.sentiment === "Bullish" ? "text-green-400" : cat.sentiment === "Bearish" ? "text-red-400" : "text-yellow-400"}`}
                    >
                      {cat.sentiment}
                    </span>
                  </div>
                  <p className="text-sm text-gray-200">{cat.text}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
