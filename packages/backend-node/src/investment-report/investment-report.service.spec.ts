import { InvestmentReportService } from './investment-report.service';
import type { InvestmentReport } from './entities/investment-report.entity';

describe('InvestmentReportService provenance compatibility', () => {
  const queryBuilder = {
    select: jest.fn().mockReturnThis(),
    where: jest.fn().mockReturnThis(),
    andWhere: jest.fn().mockReturnThis(),
    orderBy: jest.fn().mockReturnThis(),
    limit: jest.fn().mockReturnThis(),
    getRawMany: jest.fn().mockResolvedValue([]),
  };
  const dailyPriceRepository = {
    createQueryBuilder: jest.fn(() => queryBuilder),
  };

  it('maps untouched legacy reports to legacy_incomplete', async () => {
    const legacy = {
      id: 1,
      ticker: 'AAPL',
      generated_at: new Date('2026-07-01T00:00:00Z'),
      analysis_as_of: null,
      generation_metadata: null,
      agent_outputs: null,
      raw_financial_data: null,
    } as InvestmentReport;
    const service = new InvestmentReportService(
      { findOne: jest.fn().mockResolvedValue(legacy) } as never,
      dailyPriceRepository as never,
    );

    const result = await service.getStockProfile('aapl');
    expect(result.provenance_status).toBe('legacy_incomplete');
    expect(result.analysis_as_of).toBeNull();
    expect(result.generation_metadata).toBeNull();
  });

  it('loads a historical report by ticker and report id', async () => {
    const historical = {
      id: 7,
      ticker: 'AAPL',
      generated_at: new Date('2026-07-21T12:30:00Z'),
      analysis_as_of: new Date('2026-01-09T21:00:00Z'),
      generation_metadata: null,
      raw_financial_data: {
        company_identity: { symbol: 'AAPL', name: 'Apple Inc.' },
        smart_money_consensus: { current_price: 259.37 },
      },
    } as InvestmentReport;
    const findOne = jest.fn().mockResolvedValue(historical);
    const service = new InvestmentReportService(
      { findOne } as never,
      dailyPriceRepository as never,
    );

    const result = await service.getStockProfile('aapl', 7);

    expect(findOne).toHaveBeenCalledWith({
      where: { ticker: 'AAPL', id: 7 },
      order: {
        analysis_as_of: { direction: 'DESC', nulls: 'LAST' },
        generated_at: 'DESC',
      },
    });
    expect(result.report_id).toBe(7);
    expect(result.current_price).toBe(259.37);
    expect(result.raw_financial_data?.company_identity.name).toBe('Apple Inc.');
    expect(queryBuilder.andWhere).toHaveBeenCalledWith(
      'price.trade_date <= :analysisDate',
      { analysisDate: '2026-01-09' },
    );
  });

  it('rejects an invalid historical report id', async () => {
    const service = new InvestmentReportService(
      { findOne: jest.fn() } as never,
      dailyPriceRepository as never,
    );

    await expect(service.getStockProfile('AAPL', Number.NaN)).rejects.toThrow(
      'reportId must be a positive integer',
    );
  });

  it('returns only final model provenance summary in history', async () => {
    const metadata = {
      schema_version: 2,
      workflow_name: 'equity_research',
      workflow_version: '1.0.0',
      final_run_id: 'run-final',
      provenance_status: 'complete' as const,
      aggregate_usage: {
        calls: 1,
        input_tokens: 100,
        output_tokens: 50,
        total_tokens: 150,
        by_model: [],
      },
      agent_runs: [],
    };
    const report = {
      id: 2,
      ticker: 'AAPL',
      conclusion: 'HOLD',
      generated_at: new Date('2026-07-21T12:30:00Z'),
      analysis_as_of: new Date('2026-01-09T21:00:00Z'),
      model_provider: 'deepseek',
      model_name: 'deepseek-v4-pro',
      prompt_version: 'market-analyst/2.0.1',
      generation_metadata: metadata,
      raw_financial_data: {
        smart_money_consensus: { current_price: 259.37 },
      },
    } as InvestmentReport;
    const find = jest.fn().mockResolvedValue([report]);
    const service = new InvestmentReportService(
      { find } as never,
      dailyPriceRepository as never,
    );

    const [result] = await service.findHistoryByTicker('AAPL');
    expect(find).toHaveBeenCalledWith({
      where: { ticker: 'AAPL' },
      order: {
        analysis_as_of: { direction: 'DESC', nulls: 'LAST' },
        generated_at: 'DESC',
      },
      take: 20,
    });
    expect(result.analysisAsOf).toBe('2026-01-09T21:00:00.000Z');
    expect(result.provenanceStatus).toBe('complete');
    expect(result.modelName).toBe('deepseek-v4-pro');
    expect(result).not.toHaveProperty('generationMetadata');
  });

  it('maps the next report previous-call review onto the reviewed history row', async () => {
    const older = {
      id: 10,
      ticker: 'AAPL',
      conclusion: 'BUY',
      generated_at: new Date('2026-07-21T12:00:00Z'),
      analysis_as_of: new Date('2026-01-09T21:00:00Z'),
      generation_metadata: null,
      raw_financial_data: {
        smart_money_consensus: { current_price: 250 },
      },
    } as InvestmentReport;
    const newer = {
      id: 11,
      ticker: 'AAPL',
      conclusion: 'HOLD',
      generated_at: new Date('2026-07-21T12:01:00Z'),
      analysis_as_of: new Date('2026-01-30T21:00:00Z'),
      generation_metadata: null,
      raw_financial_data: {
        smart_money_consensus: { current_price: 260 },
        previous_report: {
          report_schema_version: 2,
          analysis_as_of: '2026-01-09T21:00:00+00:00',
          conclusion: 'BUY',
          conviction_level: 'Medium',
          target_price: 275,
          price_then: 250,
          evaluation_as_of: '2026-01-30',
          evaluation_price: 260,
          days_elapsed: 21,
          performance_since_pct: 4,
          verdict: 'FAVORABLE',
          verdict_status: 'interim',
          verdict_method: 'interim-price-direction/1.0.0',
        },
      },
    } as InvestmentReport;
    const service = new InvestmentReportService(
      { find: jest.fn().mockResolvedValue([newer, older]) } as never,
      dailyPriceRepository as never,
    );

    const history = await service.findHistoryByTicker('AAPL');
    expect(history[0].verdict).toBeNull();
    expect(history[1].performanceSincePct).toBe(4);
    expect(history[1].verdict).toBe('FAVORABLE');
    expect(history[1].evaluationAsOf).toBe('2026-01-30');
  });
});
