import React from "react";
import { useNavigate } from "react-router-dom";

// 1. 升级版 Sample Data：加入了极具吸引力的“交易信号”和“关键字”
const SAMPLE_STOCKS = [
  {
    ticker: "NVDA",
    name: "NVIDIA Corp",
    price: 127.4,
    change: "+3.4%",
    isUp: true,
    aiSignal: "Strong Buy",
    // ⭐️ 吸引用户点击的核心关键词
    keywords: ["PEG < 1.0", "产能突破", "财报预期看涨"],
  },
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    price: 214.32,
    change: "-0.8%",
    isUp: false,
    aiSignal: "Hold",
    keywords: ["估值过高", "iPhone 需求疲软"],
  },
  {
    ticker: "PLTR",
    name: "Palantir Tech",
    price: 24.5,
    change: "+5.2%",
    isUp: true,
    aiSignal: "Buy",
    keywords: ["政府大单落地", "技术突破"],
  },
];

export default function StockScreener() {
  const navigate = useNavigate();

  // 辅助函数：根据 AI 信号返回不同的专属颜色
  const getSignalColor = (signal: string) => {
    switch (signal) {
      case "Strong Buy":
        return "text-green-400 bg-green-900/30 border-green-800";
      case "Buy":
        return "text-emerald-400 bg-emerald-900/30 border-emerald-800";
      case "Hold":
        return "text-yellow-400 bg-yellow-900/30 border-yellow-800";
      default:
        return "text-red-400 bg-red-900/30 border-red-800";
    }
  };

  return (
    <div className="w-full h-full text-gray-200">
      <h1 className="text-2xl font-extrabold text-white mb-6">
        AI Smart Screener (高转化率版)
      </h1>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-xl">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-700 bg-gray-900/40 text-gray-400 text-xs font-bold uppercase tracking-wider">
              <th className="py-4 px-5 w-1/4">Ticker / Company</th>
              <th className="py-4 px-4 w-1/6 text-right">Price</th>
              <th className="py-4 px-6 w-1/6">AI Signal</th>
              {/* ⭐️ 新增：关键驱动因素列，占据最大宽度吸引眼球 */}
              <th className="py-4 px-5 text-right">Action</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-700/60 text-sm">
            {SAMPLE_STOCKS.map((stock) => (
              <tr
                key={stock.ticker}
                onClick={() => navigate(`/stock/${stock.ticker}`)}
                className="hover:bg-gray-700/60 cursor-pointer transition-all group"
              >
                {/* 1. Ticker & Name */}
                <td className="py-4 px-5">
                  <div className="font-bold text-blue-400 group-hover:text-blue-300 text-base">
                    {stock.ticker}
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {stock.name}
                  </div>
                </td>

                {/* 2. Price & Change */}
                <td className="py-4 px-4 text-right">
                  <div className="font-semibold text-white">
                    ${stock.price.toFixed(2)}
                  </div>
                  <div
                    className={`text-xs font-bold mt-0.5 ${stock.isUp ? "text-green-400" : "text-red-400"}`}
                  >
                    {stock.change}
                  </div>
                </td>

                {/* 3. AI Signal (带颜色的药丸徽章) */}
                <td className="py-4 px-6">
                  <span
                    className={`px-2.5 py-1 rounded text-xs font-bold border ${getSignalColor(stock.aiSignal)}`}
                  >
                    {stock.aiSignal}
                  </span>
                </td>

                {/* 4. ⭐️ 核心魔法：Keywords 标签组 */}

                {/* 5. 诱导点击的 Action */}
                <td className="py-4 px-5 text-right">
                  <span className="text-xs font-bold text-blue-500 group-hover:text-white transition-colors flex items-center justify-end gap-1">
                    Read Intel{" "}
                    <span className="group-hover:translate-x-1 transition-transform">
                      ➔
                    </span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
