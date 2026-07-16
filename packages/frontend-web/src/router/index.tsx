import React, { Suspense, type ComponentType } from "react";
import {
  createBrowserRouter,
  Navigate,
  type RouteObject,
} from "react-router-dom";
import AppLayout from "../components/Layout/Layout";
import { macroTerminalRoutes, type RouteItem } from "@signal-ledger/api-types";

// Eagerly import route views with Vite's glob loader.
const modules = import.meta.glob<{ default: ComponentType }>(
  "../pages/**/*.tsx",
);

/**
 * Convert the shared route configuration into React Router route objects.
 */
function transformRoutesToReact(jsonRoutes: RouteItem[]): RouteObject[] {
  return jsonRoutes.map((item) => {
    const routeObj: RouteObject = {
      path: item.path,
    };

    // Resolve the configured component name to an imported React component.
    if (item.component && typeof item.component === "string") {
      // Route views live under src/pages.
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

    // Recursively build nested routes.
    if (item.children && item.children.length > 0) {
      routeObj.children = transformRoutesToReact(item.children);
    }

    return routeObj;
  });
}

// Build the complete application route tree.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/stock/screener" replace /> },
      ...transformRoutesToReact(macroTerminalRoutes),
    ],
  },
]);
