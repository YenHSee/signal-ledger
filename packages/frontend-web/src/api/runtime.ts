import type { RuntimeMeta } from "@signal-ledger/api-types";
import { apiGet } from "./client";

export function getRuntimeMeta(): Promise<RuntimeMeta> {
  return apiGet<RuntimeMeta>("/meta");
}
