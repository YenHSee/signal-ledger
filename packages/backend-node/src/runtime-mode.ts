import type { AppMode, RuntimeMeta } from '@signal-ledger/api-types';

const VALID_APP_MODES: readonly AppMode[] = ['live', 'sample'];

export function getAppMode(env: NodeJS.ProcessEnv = process.env): AppMode {
  const value = (env.APP_MODE || 'live').trim().toLowerCase();
  if (!VALID_APP_MODES.includes(value as AppMode)) {
    throw new Error(
      `Invalid APP_MODE "${value}". Expected one of: ${VALID_APP_MODES.join(', ')}.`,
    );
  }
  return value as AppMode;
}

export function assertDatabaseModeBoundary(
  env: NodeJS.ProcessEnv = process.env,
): void {
  const mode = getAppMode(env);
  const database = (env.DB_NAME || 'signal_ledger').trim().toLowerCase();
  if (mode === 'sample' && database !== 'signal_ledger_sample') {
    throw new Error(
      `Sample API must use DB_NAME=signal_ledger_sample, got "${database}".`,
    );
  }
  if (mode === 'live' && database.endsWith('_sample')) {
    throw new Error(`Live API cannot use sample database "${database}".`);
  }
}

function optionalString(value: string | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function optionalCount(value: string | undefined): number | null {
  if (!value?.trim()) return null;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error('SAMPLE_TICKER_COUNT must be a non-negative integer.');
  }
  return parsed;
}

export function getRuntimeMeta(
  env: NodeJS.ProcessEnv = process.env,
): RuntimeMeta {
  const mode = getAppMode(env);
  return {
    mode,
    isLive: mode === 'live',
    datasetVersion:
      mode === 'sample' ? optionalString(env.SAMPLE_DATASET_VERSION) : null,
    dataAsOf: mode === 'sample' ? optionalString(env.SAMPLE_DATA_AS_OF) : null,
    tickerCount:
      mode === 'sample' ? optionalCount(env.SAMPLE_TICKER_COUNT) : null,
  };
}
