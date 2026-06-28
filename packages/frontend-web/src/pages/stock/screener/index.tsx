import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

// 🌟 1. 严格对应后端 QueryBuilder 吐出的字段
interface ScreenerData {
  symbol: string;
  name: string;
  pe_ratio: number | null;
  ai_signal: string | null; // 可能有的股票还没生成报告，所以是 null
  conviction: string | null;
  upside: string | null;
}

export default function StockScreener() {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState<ScreenerData[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const limit = 5;

  const fetchStocks = async (pageNum: number) => {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:4000/api/stock?page=${pageNum}&limit=${limit}`,
      );
      const result = await response.json();
      setStocks(result.data || []);
      setTotalPages(result.totalPages || 1);
    } catch (error) {
      console.error("Fetch error:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 处理 StrictMode 的经典双重调用 (Cleanup 函数)
    let ignore = false;
    if (!ignore) fetchStocks(page);
    return () => {
      ignore = true;
    };
  }, [page]);

  // 专属颜色逻辑：匹配大模型的输出 (BUY, HOLD, SELL)
  const getSignalColor = (signal: string | null) => {
    if (!signal) return "text-gray-400 bg-gray-800 border-gray-600"; // 无报告状态
    const s = signal.toUpperCase();
    if (s.includes("BUY"))
      return "text-green-400 bg-green-900/30 border-green-800";
    if (s.includes("HOLD"))
      return "text-yellow-400 bg-yellow-900/30 border-yellow-800";
    return "text-red-400 bg-red-900/30 border-red-800";
  };

  return (
    <div className="w-full h-full text-gray-200">
      <h1 className="text-2xl font-extrabold text-white mb-6">
        AI Quantum Screener
      </h1>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-xl">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-700 bg-gray-900/40 text-gray-400 text-xs font-bold uppercase tracking-wider">
              <th className="py-4 px-5 w-1/3">Ticker / Company</th>
              <th className="py-4 px-4 w-1/6 text-right">PE Ratio</th>
              <th className="py-4 px-6 w-1/4">AI Verdict</th>
              <th className="py-4 px-5 text-right w-1/4">Action</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-700/60 text-sm">
            {loading ? (
              <tr>
                <td colSpan={4} className="p-8 text-center text-gray-500">
                  Scanning Markets...
                </td>
              </tr>
            ) : (
              stocks.map((stock) => (
                <tr
                  key={stock.symbol}
                  onClick={() => navigate(`/stock/${stock.symbol}`)}
                  className="hover:bg-gray-700/60 cursor-pointer transition-all group"
                >
                  <td className="py-4 px-5">
                    <div className="font-bold text-blue-400 text-base">
                      {stock.symbol}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5 truncate max-w-[200px]">
                      {stock.name}
                    </div>
                  </td>
                  <td className="py-4 px-4 text-right font-semibold text-white">
                    {stock.pe_ratio ? Number(stock.pe_ratio).toFixed(2) : "N/A"}
                  </td>

                  {/* 🌟 极具吸引力的 AI 数据列 */}
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2.5 py-1 rounded text-xs font-bold border ${getSignalColor(stock.ai_signal)}`}
                      >
                        {stock.ai_signal || "AWAITING"}
                      </span>
                      {stock.upside && (
                        <span
                          className={`text-xs font-bold ${stock.upside.includes("-") ? "text-red-400" : "text-green-400"}`}
                        >
                          {stock.upside}
                        </span>
                      )}
                    </div>
                    {stock.conviction && (
                      <div className="text-[10px] text-gray-500 mt-1 uppercase tracking-wide">
                        Conviction: {stock.conviction}
                      </div>
                    )}
                  </td>

                  <td className="py-4 px-5 text-right">
                    <span className="text-xs font-bold text-blue-500 group-hover:text-white transition-colors flex items-center justify-end gap-1">
                      {stock.ai_signal ? "Read Intel" : "Request Analysis"}{" "}
                      <span className="group-hover:translate-x-1 transition-transform">
                        ➔
                      </span>
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-6 flex justify-between items-center text-sm">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1 || loading}
          className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-50"
        >
          Previous
        </button>
        <span className="font-bold text-gray-400">
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page === totalPages || loading}
          className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
