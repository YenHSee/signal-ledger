import {
  BadRequestException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import type {
  InvestmentReportHistoryItem,
  ProvenanceStatus,
  StockProfile,
} from '@signal-ledger/api-types';
import { InvestmentReport } from './entities/investment-report.entity';
import { DailyPrice } from '../stock/entities/daily-price.entity';

@Injectable()
export class InvestmentReportService {
  constructor(
    @InjectRepository(InvestmentReport)
    private reportRepository: Repository<InvestmentReport>,
    @InjectRepository(DailyPrice)
    private dailyPriceRepository: Repository<DailyPrice>,
  ) {}

  async getStockProfile(
    ticker: string,
    reportId?: number,
  ): Promise<StockProfile> {
    const symbol = ticker.toUpperCase();
    if (
      reportId !== undefined &&
      (!Number.isInteger(reportId) || reportId <= 0)
    ) {
      throw new BadRequestException('reportId must be a positive integer.');
    }

    const response = await this.reportRepository.findOne({
      where:
        reportId === undefined
          ? { ticker: symbol }
          : { ticker: symbol, id: reportId },
      order: {
        analysis_as_of: { direction: 'DESC', nulls: 'LAST' },
        generated_at: 'DESC',
      },
    });

    if (!response) {
      throw new NotFoundException(`No report found for: ${symbol}`);
    }

    const dayChangePct = await this.getDayChangePct(
      symbol,
      response.analysis_as_of,
    );
    return {
      report_id: response.id,
      report_schema_version: response.report_schema_version ?? null,
      ticker: response.ticker,
      analysis_as_of: this.toIso(response.analysis_as_of),
      generation_mode: response.generation_mode ?? null,
      model_tier: response.model_tier ?? null,
      model_provider: response.model_provider ?? null,
      model_name: response.model_name ?? null,
      prompt_version: response.prompt_version ?? null,
      current_price:
        response.raw_financial_data?.smart_money_consensus?.current_price ??
        null,
      target_price: response.target_price ?? null,
      conclusion: response.conclusion ?? null,
      conviction_level: response.conviction_level ?? null,
      upside_downside_pct: response.upside_downside_pct ?? null,
      risk_level: response.risk_level ?? null,
      full_report: response.full_report ?? null,
      reasoning: response.reasoning ?? null,
      dayChangePct: dayChangePct ?? null,
      generated_at: response.generated_at ?? null,
      company_identity: response.raw_financial_data?.company_identity ?? null,
      raw_financial_data: response.raw_financial_data ?? null,
      agent_outputs: response.agent_outputs ?? null,
      generation_metadata: response.generation_metadata ?? null,
      provenance_status: this.getProvenanceStatus(response),
    };
  }

  async findHistoryByTicker(
    ticker: string,
    limit = 20,
  ): Promise<InvestmentReportHistoryItem[]> {
    const reports = await this.reportRepository.find({
      where: { ticker },
      order: {
        analysis_as_of: { direction: 'DESC', nulls: 'LAST' },
        generated_at: 'DESC',
      },
      take: limit,
    });

    const reviewsByAnalysisDate = new Map<
      string,
      NonNullable<InvestmentReport['raw_financial_data']>['previous_report']
    >();
    for (const report of reports) {
      const review = report.raw_financial_data?.previous_report;
      if (review?.analysis_as_of) {
        reviewsByAnalysisDate.set(this.dateKey(review.analysis_as_of), review);
      }
    }

    return reports.map((report) => {
      const targetPrice =
        report.target_price !== null && report.target_price !== undefined
          ? Number(report.target_price)
          : null;

      const priceAtGeneration =
        report.raw_financial_data?.smart_money_consensus?.current_price ?? null;
      const reportDate = report.analysis_as_of ?? report.generated_at;
      const review = reviewsByAnalysisDate.get(this.dateKey(reportDate));

      return {
        id: report.id,
        generatedAt:
          report.generated_at instanceof Date
            ? report.generated_at.toISOString()
            : String(report.generated_at),
        analysisAsOf: this.toIso(report.analysis_as_of),
        conclusion: report.conclusion ?? null,
        convictionLevel: report.conviction_level ?? null,
        targetPrice,
        upsideDownsidePct: report.upside_downside_pct ?? null,
        riskLevel: report.risk_level ?? null,
        priceAtGeneration,
        modelProvider: report.model_provider ?? null,
        modelName: report.model_name ?? null,
        promptVersion: report.prompt_version ?? null,
        provenanceStatus: this.getProvenanceStatus(report),
        evaluationAsOf: review?.evaluation_as_of ?? null,
        evaluationPrice: review?.evaluation_price ?? null,
        performanceSincePct: review?.performance_since_pct ?? null,
        verdict: review?.verdict ?? null,
        verdictStatus: review?.verdict_status ?? null,
        verdictMethod: review?.verdict_method ?? null,
      };
    });
  }

  private async getDayChangePct(
    symbol: string,
    analysisAsOf: Date | null,
  ): Promise<number | null> {
    const query = this.dailyPriceRepository
      .createQueryBuilder('price')
      .select(['price.close_price AS close_price'])
      .where('price.symbol = :symbol', { symbol });
    if (analysisAsOf) {
      query.andWhere('price.trade_date <= :analysisDate', {
        analysisDate: analysisAsOf.toISOString().slice(0, 10),
      });
    }
    const rows = await query
      .orderBy('price.trade_date', 'DESC')
      .limit(2)
      .getRawMany<{ close_price: string | number | null }>();

    if (rows.length < 2) return null;

    const latest = this.toNumber(rows[0].close_price);
    const previous = this.toNumber(rows[1].close_price);
    if (latest === null || previous === null || previous === 0) return null;

    return Number((((latest - previous) / previous) * 100).toFixed(2));
  }

  private toNumber(value: string | number | null): number | null {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  private toIso(value: Date | string | null): string | null {
    if (!value) return null;
    return value instanceof Date ? value.toISOString() : String(value);
  }

  private getProvenanceStatus(report: InvestmentReport): ProvenanceStatus {
    if (!report.generation_metadata) return 'legacy_incomplete';
    return report.generation_metadata.provenance_status;
  }

  private dateKey(value: Date | string): string {
    return new Date(value).toISOString();
  }
}
