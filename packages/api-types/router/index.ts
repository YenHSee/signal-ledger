export interface RouteMeta {
  title: string;
  icon?: string;
  isHide?: boolean;
  requiresPro?: boolean;
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
      title: "AI Stock Intel", // 个股 AI 分析
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
          isHide: false,
        },
      },
    ],
  },
  {
    path: "/macro",
    name: "MacroMatrix",
    redirect: "/macro/nfp",
    meta: {
      title: "Macro Matrix", // 宏观决战矩阵
      icon: "Globe",
    },
    children: [
      {
        path: "/macro/nfp",
        name: "MacroNFP",
        component: "/macro/nfp/index",
        meta: {
          title: "NFP Playbook", // NFP 非农剧本
        },
      },
      {
        path: "/macro/cpi",
        name: "MacroCPI",
        component: "/macro/cpi/index",
        meta: {
          title: "CPI Projections", // CPI 通胀预演
          requiresPro: true,
        },
      },
    ],
  },
];
