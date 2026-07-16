import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import type {
  InvestmentReportHistoryItem,
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

  async getStockProfile(ticker: string): Promise<StockProfile> {
    const symbol = ticker.toUpperCase();
    const response = await this.reportRepository.findOne({
      where: { ticker: symbol },
      order: { generated_at: 'DESC' },
    });

    if (!response) {
      throw new NotFoundException(`No report found for: ${symbol}`);
    }

    const dayChangePct = await this.getDayChangePct(symbol);
    return {
      ticker: response.ticker,
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
    };
  }

  async findHistoryByTicker(
    ticker: string,
    limit = 10,
  ): Promise<InvestmentReportHistoryItem[]> {
    const reports = await this.reportRepository.find({
      where: { ticker },
      order: { generated_at: 'DESC' },
      take: limit,
    });

    return reports.map((report) => {
      const targetPrice =
        report.target_price !== null && report.target_price !== undefined
          ? Number(report.target_price)
          : null;

      const priceAtGeneration =
        report.raw_financial_data?.smart_money_consensus?.current_price ?? null;

      return {
        id: report.id,
        generatedAt:
          report.generated_at instanceof Date
            ? report.generated_at.toISOString()
            : String(report.generated_at),
        conclusion: report.conclusion ?? null,
        convictionLevel: report.conviction_level ?? null,
        targetPrice,
        upsideDownsidePct: report.upside_downside_pct ?? null,
        riskLevel: report.risk_level ?? null,
        priceAtGeneration,
      };
    });
  }

  private async getDayChangePct(symbol: string): Promise<number | null> {
    const rows = await this.dailyPriceRepository
      .createQueryBuilder('price')
      .select(['price.close_price AS close_price'])
      .where('price.symbol = :symbol', { symbol })
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
}
