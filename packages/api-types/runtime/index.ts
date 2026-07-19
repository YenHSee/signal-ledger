export type AppMode = "live" | "sample";

export interface RuntimeMeta {
  mode: AppMode;
  isLive: boolean;
  datasetVersion: string | null;
  dataAsOf: string | null;
  tickerCount: number | null;
}

export interface HealthStatus {
  status: "ok";
  database: "connected";
  mode: AppMode;
}

