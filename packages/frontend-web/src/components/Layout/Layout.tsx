import { useEffect, useMemo, useState } from "react";
import { Outlet, useLocation, matchPath } from "react-router-dom";
import SidebarMenu from "../Menu/Sidebar";
import {
  macroTerminalRoutes,
  type RouteItem,
  type RuntimeMeta,
} from "@signal-ledger/api-types";
import { getRuntimeMeta } from "../../api/runtime";

const getRouteTitle = (routes: RouteItem[], pathname: string): string => {
  for (const route of routes) {
    if (matchPath({ path: route.path, end: true }, pathname)) {
      return route.meta.title;
    }
    if (route.children) {
      const childTitle = getRouteTitle(route.children, pathname);
      if (childTitle) return childTitle;
    }
  }
  return "Overview";
};

export default function AppLayout() {
  const location = useLocation();
  const [runtimeMeta, setRuntimeMeta] = useState<RuntimeMeta | null>(null);

  useEffect(() => {
    let ignore = false;
    getRuntimeMeta()
      .then((meta) => {
        if (!ignore) setRuntimeMeta(meta);
      })
      .catch(() => {
        if (!ignore) setRuntimeMeta(null);
      });
    return () => {
      ignore = true;
    };
  }, []);

  const pageTitle = useMemo(() => {
    return getRouteTitle(macroTerminalRoutes, location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex h-screen w-screen bg-gray-900 text-white overflow-hidden">
      <aside className="w-64 flex-shrink-0 bg-gray-950 border-r border-gray-800 flex flex-col h-full">
        <div className="min-h-16 flex items-center px-6 py-3 border-b border-gray-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">📊</span>
              <h1 className="text-lg font-extrabold text-blue-400 tracking-tight">
                SignalLedger
              </h1>
            </div>
            {runtimeMeta?.mode === "sample" && (
              <div className="mt-1.5 ml-8 inline-flex items-center rounded border border-amber-500/60 bg-amber-500/10 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-widest text-amber-300">
                Demo / Sample Version
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-4">
          <SidebarMenu routes={macroTerminalRoutes} />
        </div>

        <div className="p-4 border-t border-gray-800 bg-gray-900/30 text-center">
          <div className="text-xs text-gray-500">
            {/* Senior Fullstack Trader Edition */}
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col h-full min-w-0 bg-gray-900">
        <header className="h-16 border-b border-gray-800/60 flex items-center px-8 justify-between bg-gray-900/50 backdrop-blur-sm z-10">
          <div className="text-sm font-medium text-gray-400">
            Workspace / <span className="text-white">{pageTitle}</span>
          </div>
          {runtimeMeta?.mode === "sample" && (
            <div className="flex items-center gap-3 text-xs">
              <span className="rounded-full border border-amber-500/60 bg-amber-500/10 px-3 py-1 font-bold uppercase tracking-wider text-amber-300">
                Sample Mode
              </span>
              <span className="text-gray-500">
                {runtimeMeta.datasetVersion}
                {runtimeMeta.dataAsOf
                  ? ` · Data as of ${runtimeMeta.dataAsOf}`
                  : ""}
              </span>
            </div>
          )}
        </header>

        <main className="flex-1 overflow-y-auto p-8 bg-gradient-to-b from-gray-900 to-gray-950">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
