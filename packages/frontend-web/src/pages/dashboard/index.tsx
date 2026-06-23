import React, { useState } from "react";

// ----------------------------------------------------------------------
// ⚠️ 架构师注：在真实项目中，下面这几个小组件应该被抽离到 src/components/ 里
// 这里为了让你直接能跑起来，我把它们写在同一个文件里作为内部组件
// ----------------------------------------------------------------------

// 积木 1：大盘指标卡片组件
const MetricCard = ({ title, price, change, isUp }: any) => (
  <div className="bg-gray-800 p-5 rounded-xl border border-gray-700 shadow-lg hover:border-gray-600 transition-colors">
    <h3 className="text-gray-400 text-sm font-medium">{title}</h3>
    <div className="mt-2 flex items-baseline gap-2">
      <span className="text-2xl font-bold text-white">${price}</span>
      <span
        className={`text-sm font-bold ${isUp ? "text-green-400" : "text-red-400"}`}
      >
        {isUp ? "▲" : "▼"} {change}
      </span>
    </div>
  </div>
);

// 积木 2：AI 情绪播报流组件
const SentimentFeed = () => (
  <div className="bg-gray-800 rounded-xl border border-gray-700 p-5 h-full">
    <h3 className="text-white font-bold mb-4 flex items-center gap-2">
      <span>⚡️</span> AI 市场情绪异动监控
    </h3>
    <div className="space-y-4">
      {/* 模拟一条偏空的新闻数据 (结合咱们之前 Alpha Vantage 的 JSON) */}
      <div className="border-l-2 border-red-500 pl-3">
        <p className="text-xs text-gray-400">10 分钟前 • AAPL (苹果)</p>
        <p className="text-sm text-gray-200 mt-1">
          Xiao-I 公司在上海发起专利诉讼，市场情绪转为 Somewhate-Bearish (偏空)。
        </p>
      </div>
      {/* 模拟一条偏多的新闻数据 */}
      <div className="border-l-2 border-green-500 pl-3">
        <p className="text-xs text-gray-400">45 分钟前 • NVDA (英伟达)</p>
        <p className="text-sm text-gray-200 mt-1">
          分析师上调目标价至 $298.93，PEG 估值处于极度合理区间，建议强力买入。
        </p>
      </div>
    </div>
  </div>
);

// ----------------------------------------------------------------------
// 🚀 核心视图页面 (这才是被路由引擎加载的那个大容器)
// ----------------------------------------------------------------------

export default function Dashboard() {
  // 在真实项目中，这里会写 useEffect 去 call 你的 Node.js API 获取大盘数据
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div className="w-full h-full flex flex-col gap-6 animate-fade-in">
      {/* 顶部 Header 区 */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            全球大盘概览
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Macro Matrix Overview • 美东时间 09:30 AM (开盘)
          </p>
        </div>
        <button className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-md shadow-blue-900/20 transition-all">
          生成今日 AI 研报
        </button>
      </div>

      {/* 第一层：核心数据指标区 (Grid 网格布局) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="标普 500 (S&P 500)"
          price="5,240.12"
          change="+1.2%"
          isUp={true}
        />
        <MetricCard
          title="纳斯达克 (NASDAQ)"
          price="16,399.52"
          change="+1.8%"
          isUp={true}
        />
        <MetricCard
          title="恐慌指数 (VIX)"
          price="14.25"
          change="-5.4%"
          isUp={false}
        />
        <MetricCard
          title="美国 10 年期国债收益率"
          price="4.21%"
          change="+0.02%"
          isUp={true}
        />
      </div>

      {/* 第二层：图表与资讯区 (左右分栏，左侧占 2/3，右侧占 1/3) */}
      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        {/* 左侧主图表区 */}
        <div className="lg:w-2/3 bg-gray-800 rounded-xl border border-gray-700 p-5 flex flex-col shadow-lg">
          <h3 className="text-white font-bold mb-4">标普 500 资金流向热力图</h3>
          <div className="flex-1 border-2 border-dashed border-gray-700 rounded-lg flex items-center justify-center bg-gray-900/50">
            <p className="text-gray-500 text-sm">
              [这里未来会接入 ECharts 或 TradingView Lightweight Charts 的
              K线组件]
            </p>
          </div>
        </div>

        {/* 右侧动态流 */}
        <div className="lg:w-1/3">
          <SentimentFeed />
        </div>
      </div>
    </div>
  );
}
