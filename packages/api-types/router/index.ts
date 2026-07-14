export interface RouteMeta {
  title: string;
  icon?: string;
  isHide?: boolean;
}

export interface RouteItem {
  path: string;
  name: string;
  component?: string;
  redirect?: string;
  meta: RouteMeta;
  children?: RouteItem[];
}

export const macroTerminalRoutes: RouteItem[] = [
  // {
  //   path: "/dashboard",
  //   name: "Dashboard",
  //   component: "/dashboard/index",
  //   meta: {
  //     title: "Market Overview", // 大盘概览
  //     icon: "Activity",
  //   },
  // },
  {
    path: "/stock",
    name: "StockIntel",
    redirect: "/stock/screener",
    meta: {
      title: "Equity Research", // 个股 AI 分析
      icon: "TrendingUp",
    },
    children: [
      {
        path: "/stock/screener",
        name: "StockScreener",
        component: "/stock/screener/index",
        meta: {
          title: "Smart Screener", // AI 智能扫盘
        },
      },
      {
        path: "/stock/:ticker",
        name: "StockDetail",
        component: "/stock/detail/index",
        meta: {
          title: "Stock Report Details", // 个股研报详情
          isHide: true,
        },
      },
    ],
  },
];
