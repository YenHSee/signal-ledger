import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, SelectQueryBuilder } from 'typeorm';
import type {
  DailyPricePoint,
  FundamentalsProfile,
  ScreenerHasReportFilter,
  ScreenerIndexFilter,
  ScreenerListMeta,
  ScreenerListQuery,
  ScreenerListResponse,
  ScreenerSortField,
  ScreenerStockItem,
  StockNewsItem,
} from '@signal-ledger/api-types';
import { Stock } from './entities/stock.entity';
import { DailyPrice } from './entities/daily-price.entity';
import { StockNews } from './entities/stock-news.entity';

interface RawStockRow {
  symbol: string;
  name: string;
  sector: string | null;
  market_capitalization: string | number | null;
  forward_pe: string | number | null;
  shares_outstanding: string | number | null;
  quarterly_revenue_growth_yoy: string | number | null;
  quarterly_earnings_growth_yoy: string | number | null;
  return_on_equity_ttm: string | number | null;
  profit_margin: string | number | null;
  dividend_yield: string | number | null;
  peg_ratio: string | number | null;
  analyst_target_price: string | number | null;
  week_52_high: string | number | null;
  week_52_low: string | number | null;
  day_50_moving_average: string | number | null;
  day_200_moving_average: string | number | null;
  ai_signal: string | null;
  upside_pct: string | null;
}

type StockQueryBuilder = SelectQueryBuilder<Stock>;

@Injectable()
export class StockService {
  constructor(
    @InjectRepository(Stock)
    private stockRepository: Repository<Stock>,
    @InjectRepository(DailyPrice)
    private dailyPriceRepository: Repository<DailyPrice>,
    @InjectRepository(StockNews)
    private stockNewsRepository: Repository<StockNews>,
  ) {}

  async getCompanyList(
    options: ScreenerListQuery = {},
  ): Promise<ScreenerListResponse> {
    const page = options.page ?? 1;
    const limit = options.limit ?? 100;
    const skip = (page - 1) * limit;
    const sortBy = options.sortBy ?? 'marketCap';
    const sortOrder = (options.sortOrder ?? 'desc').toUpperCase() as
      'ASC' | 'DESC';

    const spxFwdPe = await this.getSpxForwardPe();
    const sectors = await this.getDistinctSectors();

    const query = this.createBaseQuery();
    this.applyAllFilters(query, options, spxFwdPe);

    const sortColumn = this.getSortColumn(sortBy, spxFwdPe);
    query.orderBy(sortColumn, sortOrder).limit(limit).offset(skip);

    const rawRows = await query.getRawMany<RawStockRow>();
    const total = await this.getFilteredCount(options, spxFwdPe);
    const stocksWithReport = await this.getStocksWithReportCount(
      options,
      spxFwdPe,
    );

    const data = rawRows.map((row) => this.mapToScreenerItem(row, spxFwdPe));

    const meta: ScreenerListMeta = {
      totalStocks: total,
      stocksWithReport,
      spxFwdPe,
      sectors,
    };

    return {
      data,
      meta,
      total,
      page,
      totalPages: Math.ceil(total / limit),
    };
  }

  async getStockFundamentals(ticker: string): Promise<FundamentalsProfile> {
    const symbol = ticker.toUpperCase();
    const stock = await this.stockRepository.findOne({ where: { symbol } });

    if (!stock) {
      throw new NotFoundException(`No stock profile found for: ${ticker}`);
    }

    const num = (value: unknown) =>
      this.toNumber(value as string | number | null);

    const marketCap = num(stock.market_capitalization);
    const sharesOutstanding = num(stock.shares_outstanding);
    const price =
      marketCap !== null && sharesOutstanding !== null && sharesOutstanding > 0
        ? Number((marketCap / sharesOutstanding).toFixed(2))
        : null;

    // const dayChangePct = await this.getDayChangePct(symbol);

    return {
      ticker: stock.symbol,
      price,
      // dayChangePct,
      marketCap,
      valuation: {
        trailingPe: num(stock.trailing_pe),
        forwardPe: num(stock.forward_pe),
        pegRatio: num(stock.peg_ratio),
        evToRevenue: num(stock.ev_to_revenue),
        evToEbitda: num(stock.ev_to_ebitda),
        priceToBook: num(stock.price_to_book_ratio),
        priceToSales: num(stock.price_to_sales_ratio_ttm),
      },
      profitability: {
        profitMargin: num(stock.profit_margin),
        returnOnEquity: num(stock.return_on_equity_ttm),
        revenueGrowthYoy: num(stock.quarterly_revenue_growth_yoy),
        earningsGrowthYoy: num(stock.quarterly_earnings_growth_yoy),
      },
      income: {
        dividendYield: num(stock.dividend_yield),
        dividendPerShare: num(stock.dividend_per_share),
        exDividendDate: stock.ex_dividend_date
          ? new Date(stock.ex_dividend_date).toISOString().slice(0, 10)
          : null,
      },
      ownership: {
        percentInsiders: num(stock.percent_insiders),
        percentInstitutions: num(stock.percent_institutions),
      },
      analystRatings: {
        strongBuy: stock.analyst_rating_strong_buy ?? 0,
        buy: stock.analyst_rating_buy ?? 0,
        hold: stock.analyst_rating_hold ?? 0,
        sell: stock.analyst_rating_sell ?? 0,
        strongSell: stock.analyst_rating_strong_sell ?? 0,
      },
      // analystTargetPrice: num(stock.analyst_target_price),
      technical: {
        week52High: num(stock.week_52_high),
        week52Low: num(stock.week_52_low),
        ma50: num(stock.day_50_moving_average),
        ma200: num(stock.day_200_moving_average),
        beta: num(stock.beta),
      },
    };
  }

  async getDailyPrices(ticker: string, days = 30): Promise<DailyPricePoint[]> {
    const symbol = ticker.toUpperCase();
    const rows = await this.dailyPriceRepository
      .createQueryBuilder('price')
      .select([
        'price.trade_date AS trade_date',
        'price.close_price AS close_price',
        'price.volume AS volume',
      ])
      .where('price.symbol = :symbol', { symbol })
      .orderBy('price.trade_date', 'DESC')
      .limit(days)
      .getRawMany<{
        trade_date: string;
        close_price: string | number | null;
        volume: string | number | null;
      }>();

    return rows
      .map((row) => ({
        date: row.trade_date,
        close: this.toNumber(row.close_price) ?? 0,
        volume: this.toNumber(row.volume) ?? undefined,
      }))
      .reverse();
  }

  async getCompanyNews(ticker: string, days = 30): Promise<StockNewsItem[]> {
    const symbol = ticker.toUpperCase();
    const rows = await this.stockNewsRepository
      .createQueryBuilder('news')
      .select([
        'news.finnhub_id AS finnhub_id',
        'news.trade_date AS trade_date',
        'news.datetime AS datetime',
        'news.headline AS headline',
        'news.summary AS summary',
        'news.source AS source',
        'news.url AS url',
      ])
      .where('news.symbol = :symbol', { symbol })
      .andWhere(`news.trade_date >= CURRENT_DATE - INTERVAL '${days} days'`)
      .orderBy('news.datetime', 'DESC')
      .getRawMany<{
        finnhub_id: string | number;
        trade_date: string;
        datetime: string | number;
        headline: string;
        summary: string | null;
        source: string | null;
        url: string | null;
      }>();

    return rows.map((row) => ({
      id: Number(row.finnhub_id),
      date: row.trade_date,
      datetime: Number(row.datetime),
      headline: row.headline,
      summary: row.summary ?? '',
      source: row.source ?? '',
      url: row.url ?? '',
    }));
  }

  private createBaseQuery(): StockQueryBuilder {
    return this.stockRepository
      .createQueryBuilder('stock')
      .leftJoin(
        'investment_reports',
        'report',
        `report.ticker = stock.symbol AND report.generated_at = (
          SELECT MAX(ir.generated_at)
          FROM investment_reports ir
          WHERE ir.ticker = stock.symbol
        )`,
      )
      .select([
        'stock.symbol AS symbol',
        'stock.name AS name',
        'stock.sector AS sector',
        'stock.market_capitalization AS market_capitalization',
        'stock.forward_pe AS forward_pe',
        'stock.shares_outstanding AS shares_outstanding',
        'stock.quarterly_revenue_growth_yoy AS quarterly_revenue_growth_yoy',
        'stock.quarterly_earnings_growth_yoy AS quarterly_earnings_growth_yoy',
        'stock.return_on_equity_ttm AS return_on_equity_ttm',
        'stock.profit_margin AS profit_margin',
        'stock.dividend_yield AS dividend_yield',
        'stock.peg_ratio AS peg_ratio',
        'stock.analyst_target_price AS analyst_target_price',
        'stock.week_52_high AS week_52_high',
        'stock.week_52_low AS week_52_low',
        'stock.day_50_moving_average AS day_50_moving_average',
        'stock.day_200_moving_average AS day_200_moving_average',
        'report.conclusion AS ai_signal',
        'report.upside_downside_pct AS upside_pct',
      ]);
  }

  private priceExpression(): string {
    return 'stock.market_capitalization / NULLIF(stock.shares_outstanding, 0)';
  }

  private applyAllFilters(
    query: StockQueryBuilder,
    options: ScreenerListQuery,
    spxFwdPe: number | null,
  ) {
    this.applyIndexFilter(query, options.index);
    this.applySectorFilter(query, options.sector);
    this.applySearchFilter(query, options.search);
    this.applyValuationFilters(query, options, spxFwdPe);
    this.applyGrowthFilters(query, options);
    this.applyQualityFilters(query, options);
    this.applyIncomeFilters(query, options);
    this.applyTechnicalFilters(query, options);
    this.applyReportFilters(query, options);
  }

  private applyIndexFilter(
    query: StockQueryBuilder,
    index?: ScreenerIndexFilter,
  ) {
    if (index === 'spx') {
      query.andWhere('stock.is_sp500 = :isSp500', { isSp500: true });
    } else if (index === 'ndx') {
      query.andWhere('stock.exchange IN (:...ndxExchanges)', {
        ndxExchanges: ['NASDAQ', 'NMS'],
      });
    }
  }

  private applySectorFilter(query: StockQueryBuilder, sector?: string) {
    if (sector && sector !== 'all') {
      query.andWhere('stock.sector = :sector', { sector });
    }
  }

  private applySearchFilter(query: StockQueryBuilder, search?: string) {
    const term = search?.trim();
    if (!term) return;

    query.andWhere('(stock.symbol ILIKE :search OR stock.name ILIKE :search)', {
      search: `%${term}%`,
    });
  }

  private applyValuationFilters(
    query: StockQueryBuilder,
    options: ScreenerListQuery,
    spxFwdPe: number | null,
  ) {
    if (options.marketCapMin !== undefined) {
      query.andWhere('stock.market_capitalization >= :marketCapMin', {
        marketCapMin: options.marketCapMin,
      });
    }
    if (options.marketCapMax !== undefined) {
      query.andWhere('stock.market_capitalization <= :marketCapMax', {
        marketCapMax: options.marketCapMax,
      });
    }
    if (options.forwardPeMin !== undefined) {
      query.andWhere('stock.forward_pe >= :forwardPeMin', {
        forwardPeMin: options.forwardPeMin,
      });
    }
    if (options.forwardPeMax !== undefined) {
      query.andWhere('stock.forward_pe <= :forwardPeMax', {
        forwardPeMax: options.forwardPeMax,
      });
    }
    if (options.vsSpxMin !== undefined && spxFwdPe !== null && spxFwdPe > 0) {
      query.andWhere('stock.forward_pe / :spxFwdPeVsMin >= :vsSpxMin', {
        spxFwdPeVsMin: spxFwdPe,
        vsSpxMin: options.vsSpxMin,
      });
    }
    if (options.vsSpxMax !== undefined && spxFwdPe !== null && spxFwdPe > 0) {
      query.andWhere('stock.forward_pe / :spxFwdPeVsMax <= :vsSpxMax', {
        spxFwdPeVsMax: spxFwdPe,
        vsSpxMax: options.vsSpxMax,
      });
    }
    if (options.pegMax !== undefined) {
      query.andWhere('stock.peg_ratio <= :pegMax', {
        pegMax: options.pegMax,
      });
    }
  }

  private applyGrowthFilters(
    query: StockQueryBuilder,
    options: ScreenerListQuery,
  ) {
    if (options.revenueGrowthMin !== undefined) {
      query.andWhere(
        'stock.quarterly_revenue_growth_yoy >= :revenueGrowthMin',
        { revenueGrowthMin: options.revenueGrowthMin },
      );
    }
    if (options.earningsGrowthMin !== undefined) {
      query.andWhere(
        'stock.quarterly_earnings_growth_yoy >= :earningsGrowthMin',
        { earningsGrowthMin: options.earningsGrowthMin },
      );
    }
  }

  private applyQualityFilters(
    query: StockQueryBuilder,
    options: ScreenerListQuery,
  ) {
    if (options.roeMin !== undefined) {
      query.andWhere('stock.return_on_equity_ttm >= :roeMin', {
        roeMin: options.roeMin,
      });
    }
    if (options.profitMarginMin !== undefined) {
      query.andWhere('stock.profit_margin >= :profitMarginMin', {
        profitMarginMin: options.profitMarginMin,
      });
    }
  }

  private applyIncomeFilters(
    query: StockQueryBuilder,
    options: ScreenerListQuery,
  ) {
    if (options.dividendYieldMin !== undefined) {
      query.andWhere('stock.dividend_yield >= :dividendYieldMin', {
        dividendYieldMin: options.dividendYieldMin,
      });
    }
  }

  private applyTechnicalFilters(
    query: StockQueryBuilder,
    options: ScreenerListQuery,
  ) {
    const priceExpr = this.priceExpression();

    if (options.ma50 === 'above') {
      query.andWhere(`${priceExpr} > stock.day_50_moving_average`);
    } else if (options.ma50 === 'below') {
      query.andWhere(`${priceExpr} < stock.day_50_moving_average`);
    }

    if (options.ma200 === 'above') {
      query.andWhere(`${priceExpr} > stock.day_200_moving_average`);
    } else if (options.ma200 === 'below') {
      query.andWhere(`${priceExpr} < stock.day_200_moving_average`);
    }

    if (options.nearExtreme === 'high') {
      query.andWhere(`${priceExpr} >= stock.week_52_high * 0.9`);
    } else if (options.nearExtreme === 'low') {
      query.andWhere(`${priceExpr} <= stock.week_52_low * 1.1`);
    }
  }

  private applyReportFilters(
    query: StockQueryBuilder,
    options: ScreenerListQuery,
  ) {
    const hasReport = options.hasReport ?? 'all';
    if (hasReport === 'yes') {
      query.andWhere('report.conclusion IS NOT NULL');
    } else if (hasReport === 'no') {
      query.andWhere('report.conclusion IS NULL');
    }

    if (options.conclusions && options.conclusions.length > 0) {
      const conditions = options.conclusions.map((conclusion, index) => {
        const param = `conclusion${index}`;
        query.setParameter(param, `%${conclusion}%`);
        return `report.conclusion ILIKE :${param}`;
      });
      query.andWhere(`(${conditions.join(' OR ')})`);
    }
  }

  private getSortColumn(
    sortBy: ScreenerSortField,
    spxFwdPe: number | null,
  ): string {
    const priceExpr = this.priceExpression();

    switch (sortBy) {
      case 'forwardPe':
        return 'stock.forward_pe';
      case 'price':
        return priceExpr;
      case 'vsSpx':
        return spxFwdPe ? 'stock.forward_pe' : 'stock.forward_pe';
      case 'ticker':
        return 'stock.symbol';
      case 'revenueGrowthYoy':
        return 'stock.quarterly_revenue_growth_yoy';
      case 'analystUpside':
        return `(CASE WHEN ${priceExpr} > 0 AND stock.analyst_target_price IS NOT NULL
          THEN (stock.analyst_target_price - (${priceExpr})) / (${priceExpr})
          ELSE NULL END)`;
      case 'roe':
        return 'stock.return_on_equity_ttm';
      case 'marketCap':
      default:
        return 'stock.market_capitalization';
    }
  }

  private async getFilteredCount(
    options: ScreenerListQuery,
    spxFwdPe: number | null,
  ): Promise<number> {
    const query = this.stockRepository.createQueryBuilder('stock').leftJoin(
      'investment_reports',
      'report',
      `report.ticker = stock.symbol AND report.generated_at = (
          SELECT MAX(ir.generated_at)
          FROM investment_reports ir
          WHERE ir.ticker = stock.symbol
        )`,
    );
    this.applyAllFilters(query, options, spxFwdPe);
    return query.getCount();
  }

  private async getStocksWithReportCount(
    options: ScreenerListQuery,
    spxFwdPe: number | null,
  ): Promise<number> {
    const query = this.stockRepository
      .createQueryBuilder('stock')
      .leftJoin(
        'investment_reports',
        'report',
        `report.ticker = stock.symbol AND report.generated_at = (
          SELECT MAX(ir.generated_at)
          FROM investment_reports ir
          WHERE ir.ticker = stock.symbol
        )`,
      )
      .andWhere('report.conclusion IS NOT NULL');

    const countOptions = {
      ...options,
      hasReport: 'all' as ScreenerHasReportFilter,
    };
    this.applyAllFilters(query, countOptions, spxFwdPe);
    return query.getCount();
  }

  private async getSpxForwardPe(): Promise<number | null> {
    const result = await this.stockRepository
      .createQueryBuilder('stock')
      .select('AVG(stock.forward_pe)', 'avg_forward_pe')
      .where('stock.is_sp500 = :isSp500', { isSp500: true })
      .andWhere('stock.forward_pe IS NOT NULL')
      .andWhere('stock.forward_pe > 0')
      .getRawOne<{ avg_forward_pe: string | null }>();

    if (!result?.avg_forward_pe) return null;
    return Number(Number(result.avg_forward_pe).toFixed(1));
  }

  private async getDistinctSectors(): Promise<string[]> {
    const rows = await this.stockRepository
      .createQueryBuilder('stock')
      .select('DISTINCT stock.sector', 'sector')
      .where('stock.sector IS NOT NULL')
      .andWhere("stock.sector <> ''")
      .orderBy('stock.sector', 'ASC')
      .getRawMany<{ sector: string }>();

    return rows.map((row) => row.sector);
  }

  private mapToScreenerItem(
    row: RawStockRow,
    spxFwdPe: number | null,
  ): ScreenerStockItem {
    const marketCap = this.toNumber(row.market_capitalization);
    const sharesOutstanding = this.toNumber(row.shares_outstanding);
    const forwardPe = this.toNumber(row.forward_pe);
    const week52High = this.toNumber(row.week_52_high);
    const analystTargetPrice = this.toNumber(row.analyst_target_price);

    const price =
      marketCap !== null && sharesOutstanding !== null && sharesOutstanding > 0
        ? Number((marketCap / sharesOutstanding).toFixed(2))
        : null;

    const forwardEps =
      price !== null && forwardPe !== null && forwardPe > 0
        ? Number((price / forwardPe).toFixed(2))
        : null;

    const vsSpx =
      forwardPe !== null && spxFwdPe !== null && spxFwdPe > 0
        ? Number((forwardPe / spxFwdPe).toFixed(2))
        : null;

    const analystUpside =
      price !== null && analystTargetPrice !== null && price > 0
        ? Number((((analystTargetPrice - price) / price) * 100).toFixed(1))
        : null;

    const pctFrom52wHigh =
      price !== null && week52High !== null && week52High > 0
        ? Number((((price - week52High) / week52High) * 100).toFixed(1))
        : null;

    const aiSignal = row.ai_signal ?? null;

    return {
      ticker: row.symbol,
      name: row.name,
      sector: row.sector,
      price,
      marketCap,
      forwardEps,
      forwardPe,
      vsSpx,
      hasReport: aiSignal !== null,
      aiSignal,
      upsidePct: row.upside_pct ?? null,
      revenueGrowthYoy: this.toNumber(row.quarterly_revenue_growth_yoy),
      roe: this.toNumber(row.return_on_equity_ttm),
      analystUpside,
      pctFrom52wHigh,
    };
  }

  private toNumber(value: string | number | null): number | null {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
}
