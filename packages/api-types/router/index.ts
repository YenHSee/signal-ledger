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
  {
    path: "/stock",
    name: "StockIntel",
    redirect: "/stock/screener",
    meta: {
      title: "Equity Research",
      icon: "TrendingUp",
    },
    children: [
      {
        path: "/stock/screener",
        name: "StockScreener",
        component: "/stock/screener/index",
        meta: {
          title: "Smart Screener",
        },
      },
      {
        path: "/stock/:ticker",
        name: "StockDetail",
        component: "/stock/detail/index",
        meta: {
          title: "Stock Report Details",
          isHide: true,
        },
      },
    ],
  },
];
