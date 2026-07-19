import {
  assertDatabaseModeBoundary,
  getAppMode,
  getRuntimeMeta,
} from './runtime-mode';

describe('runtime mode', () => {
  it('defaults to live mode', () => {
    expect(getAppMode({})).toBe('live');
  });

  it('rejects unsupported modes', () => {
    expect(() => getAppMode({ APP_MODE: 'preview' })).toThrow(
      'Invalid APP_MODE',
    );
  });

  it('returns sample metadata from the environment', () => {
    expect(
      getRuntimeMeta({
        APP_MODE: 'sample',
        SAMPLE_DATASET_VERSION: '2026-07-17.1',
        SAMPLE_DATA_AS_OF: '2026-07-17',
        SAMPLE_TICKER_COUNT: '10',
      }),
    ).toEqual({
      mode: 'sample',
      isLive: false,
      datasetVersion: '2026-07-17.1',
      dataAsOf: '2026-07-17',
      tickerCount: 10,
    });
  });

  it('rejects an invalid sample ticker count', () => {
    expect(() =>
      getRuntimeMeta({ APP_MODE: 'sample', SAMPLE_TICKER_COUNT: '-1' }),
    ).toThrow('SAMPLE_TICKER_COUNT');
  });
  it('keeps sample and live databases isolated', () => {
    expect(() =>
      assertDatabaseModeBoundary({
        APP_MODE: 'sample',
        DB_NAME: 'signal_ledger',
      }),
    ).toThrow('Sample API must use');
    expect(() =>
      assertDatabaseModeBoundary({
        APP_MODE: 'live',
        DB_NAME: 'signal_ledger_sample',
      }),
    ).toThrow('Live API cannot use');
    expect(() =>
      assertDatabaseModeBoundary({
        APP_MODE: 'sample',
        DB_NAME: 'signal_ledger_sample',
      }),
    ).not.toThrow();
  });
});
