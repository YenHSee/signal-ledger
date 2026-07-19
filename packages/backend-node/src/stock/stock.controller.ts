import { Controller, Get, Param, Query } from '@nestjs/common';
import type {
  DailyPricePoint,
  ScreenerConclusionFilter,
  ScreenerHasReportFilter,
  ScreenerIndexFilter,
  ScreenerListQuery,
  ScreenerListResponse,
  ScreenerMaFilter,
  ScreenerNearExtremeFilter,
  ScreenerSortField,
  ScreenerSortOrder,
  StockNewsItem,
} from '@signal-ledger/api-types';
import { StockService } from './stock.service';

function parseNumber(value?: string): number | undefined {
  if (value === undefined || value === '') return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function parseConclusions(
  value?: string,
): ScreenerConclusionFilter[] | undefined {
  if (!value) return undefined;
  const items = value
    .split(',')
    .map((item) => item.trim().toUpperCase())
    .filter((item): item is ScreenerConclusionFilter =>
      ['BUY', 'HOLD', 'SELL'].includes(item),
    );
  return items.length > 0 ? items : undefined;
}

@Controller('stock')
export class StockController {
  constructor(private readonly stockService: StockService) {}

  @Get()
  async getCompanies(
    @Query('page') page?: string,
    @Query('limit') limit?: string,
    @Query('index') index?: string,
    @Query('sector') sector?: string,
    @Query('search') search?: string,
    @Query('sortBy') sortBy?: string,
    @Query('sortOrder') sortOrder?: string,
    @Query('marketCapMin') marketCapMin?: string,
    @Query('marketCapMax') marketCapMax?: string,
    @Query('forwardPeMin') forwardPeMin?: string,
    @Query('forwardPeMax') forwardPeMax?: string,
    @Query('vsSpxMin') vsSpxMin?: string,
    @Query('vsSpxMax') vsSpxMax?: string,
    @Query('pegMax') pegMax?: string,
    @Query('revenueGrowthMin') revenueGrowthMin?: string,
    @Query('earningsGrowthMin') earningsGrowthMin?: string,
    @Query('roeMin') roeMin?: string,
    @Query('profitMarginMin') profitMarginMin?: string,
    @Query('dividendYieldMin') dividendYieldMin?: string,
    @Query('ma50') ma50?: string,
    @Query('ma200') ma200?: string,
    @Query('nearExtreme') nearExtreme?: string,
    @Query('hasReport') hasReport?: string,
    @Query('conclusions') conclusions?: string,
  ): Promise<ScreenerListResponse> {
    const query: ScreenerListQuery = {
      page: page ? Number(page) : 1,
      limit: limit ? Number(limit) : 100,
      index: index as ScreenerIndexFilter | undefined,
      sector,
      search,
      sortBy: sortBy as ScreenerSortField | undefined,
      sortOrder: sortOrder as ScreenerSortOrder | undefined,
      marketCapMin: parseNumber(marketCapMin),
      marketCapMax: parseNumber(marketCapMax),
      forwardPeMin: parseNumber(forwardPeMin),
      forwardPeMax: parseNumber(forwardPeMax),
      vsSpxMin: parseNumber(vsSpxMin),
      vsSpxMax: parseNumber(vsSpxMax),
      pegMax: parseNumber(pegMax),
      revenueGrowthMin: parseNumber(revenueGrowthMin),
      earningsGrowthMin: parseNumber(earningsGrowthMin),
      roeMin: parseNumber(roeMin),
      profitMarginMin: parseNumber(profitMarginMin),
      dividendYieldMin: parseNumber(dividendYieldMin),
      ma50: ma50 as ScreenerMaFilter | undefined,
      ma200: ma200 as ScreenerMaFilter | undefined,
      nearExtreme: nearExtreme as ScreenerNearExtremeFilter | undefined,
      hasReport: hasReport as ScreenerHasReportFilter | undefined,
      conclusions: parseConclusions(conclusions),
    };

    return this.stockService.getCompanyList(query);
  }

  // @Get(':ticker')
  // async getStockProfile(@Param('ticker') ticker: string): Promise<StockProfile> {
  //   return this.stockService.getStockProfile(ticker);
  // }

  @Get(':ticker/prices')
  async getDailyPrices(
    @Param('ticker') ticker: string,
    @Query('days') days?: string,
  ): Promise<DailyPricePoint[]> {
    return this.stockService.getDailyPrices(ticker, days ? Number(days) : 365);
  }

  @Get(':ticker/news')
  async getCompanyNews(
    @Param('ticker') ticker: string,
    @Query('days') days?: string,
  ): Promise<StockNewsItem[]> {
    return this.stockService.getCompanyNews(ticker, days ? Number(days) : 30);
  }
}
