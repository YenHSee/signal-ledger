import React, { Suspense, type ComponentType } from "react";
import {
  createBrowserRouter,
  Navigate,
  type RouteObject,
} from "react-router-dom";
import AppLayout from "../components/Layout/Layout";
import { macroTerminalRoutes, type RouteItem } from "@signal-ledger/api-types";

// 1. ⭐️ 就像你的 Vue 代码一样，利用 Vite 的 glob 魔法，批量把 views 下的 tsx 扫描进来
const modules = import.meta.glob<{ default: ComponentType }>(
  "../pages/**/*.tsx",
);

/**
 * React 路由工厂函数 (Route Factory)
 * 职责：负责把你从 api-types 拿到的“纯字符串 JSON”，翻译成 React Router 认识的 JSX element 节点数组
 */
function transformRoutesToReact(jsonRoutes: RouteItem[]): RouteObject[] {
  return jsonRoutes.map((item) => {
    const routeObj: RouteObject = {
      path: item.path,
    };

    // 2. ⭐️ 核心关键：处理字符串到组件的转换
    if (item.component && typeof item.component === "string") {
      // 拼接出本地真实的物理路径（假设你的页面全在 src/views 里面）
      const componentPath = `../pages${item.component}.tsx`;

      if (modules[componentPath]) {
        const LazyComponent = React.lazy(modules[componentPath]);

        routeObj.element = (
          <Suspense
            fallback={
              <div className="p-8 text-gray-500">Loading equity research...</div>
            }
          >
            <LazyComponent />
          </Suspense>
        );
      } else {
        routeObj.element = (
          <div>Unable to load page: {componentPath}</div>
        );
      }
    }

    // 3. 递归处理子路由 (Children)
    if (item.children && item.children.length > 0) {
      routeObj.children = transformRoutesToReact(item.children);
    }

    return routeObj;
  });
}

// 4. ⭐️ 终极无缝缝合：生成整个应用的真实路由树
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />, // 你的外壳组件，里面有 SidebarMenu 和 <Outlet />
    children: [
      { index: true, element: <Navigate to="/stock/screener" replace /> },
      // 🚀 注入经过我们工厂函数洗刷干净的、React Router 最爱吃的标准路由数组！
      ...transformRoutesToReact(macroTerminalRoutes),
    ],
  },
]);
