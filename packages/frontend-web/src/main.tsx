import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import AppLayout from "./components/Layout/Layout";
import { RouterProvider } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { router } from "./router/index";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
    {/* <BrowserRouter>
      <AppLayout />
    </BrowserRouter> */}
    {/* <App /> */}
  </StrictMode>,
);
