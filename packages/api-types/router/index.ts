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
  {
    path: "/dashboard",
    name: "Dashboard",
    component: "/dashboard/index",
    meta: {
      title: "大盘概览",
      icon: "Activity",
    },
  },
  {
    path: "/stock",
    name: "StockIntel",
    redirect: "/stock/screener",
    meta: {
      title: "个股 AI 分析",
      icon: "TrendingUp",
    },
    children: [
      {
        path: "/stock/screener",
        name: "StockScreener",
        component: "/stock/screener/index",
        meta: {
          title: "AI 智能扫盘",
        },
      },
      {
        path: "/stock/:ticker",
        name: "StockDetail",
        component: "/stock/detail/index",
        meta: {
          title: "个股研报详情",
          isHide: true,
        },
      },
    ],
  },
  {
    path: "/macro",
    name: "MacroMatrix",
    redirect: "/macro/nfp",
    meta: {
      title: "宏观决战矩阵",
      icon: "Globe",
    },
    children: [
      {
        path: "/macro/nfp",
        name: "MacroNFP",
        component: "/macro/nfp/index",
        meta: {
          title: "NFP 非农剧本",
        },
      },
      {
        path: "/macro/cpi",
        name: "MacroCPI",
        component: "/macro/cpi/index",
        meta: {
          title: "CPI 通胀预演",
          requiresPro: true,
        },
      },
    ],
  },
  {
    path: "/settings",
    name: "Settings",
    redirect: "/settings/subscription",
    meta: {
      title: "账户与资产",
      icon: "Shield",
    },
    children: [
      {
        path: "/settings/subscription",
        name: "Subscription",
        component: "/settings/subscription/index",
        meta: {
          title: "会员订阅 ($9.99)",
        },
      },
      {
        path: "/settings/broker",
        name: "BrokerLink",
        component: "/settings/broker/index",
        meta: {
          title: "券商 API 绑定",
        },
      },
    ],
  },
];
