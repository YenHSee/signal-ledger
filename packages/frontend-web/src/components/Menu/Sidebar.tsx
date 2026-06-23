import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import type { RouteItem } from "@stock-analyst/api-types";

// 定义组件
const SidebarMenu = ({ routes }: { routes: RouteItem[] }) => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <ul className="space-y-2">
      {routes.map((route) => {
        if (route.meta.isHide) return null;

        if (route.children && route.children.length > 0) {
          return (
            <li key={route.name} className="px-4 py-2">
              <div className="font-bold text-gray-400 uppercase text-xs mb-2">
                {route.meta.title}
              </div>
              <SidebarMenu routes={route.children} />
            </li>
          );
        }

        const isActive = location.pathname.startsWith(route.path);

        return (
          <li key={route.name}>
            <button
              onClick={() => navigate(route.path)}
              className={`w-full text-left px-4 py-2 rounded-lg flex items-center justify-between ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-800"
              }`}
            >
              <span>{route.meta.title}</span>

              {route.meta.requiresPro && (
                <span className="text-[10px] bg-yellow-500 text-black px-1.5 py-0.5 rounded font-bold">
                  PRO
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
};

export default SidebarMenu;
