import {
  Controller,
  Get,
  Post,
  Patch,
  Param,
  Query,
  Delete,
} from '@nestjs/common';
import type {
  DailyPricePoint,
  FundamentalsProfile,
  InvestmentReportHistoryItem,
} from '@stock-analyst/api-types';
import { InvestmentReportService } from './investment-report.service';
import { CreateInvestmentReportDto } from './dto/create-investment-report.dto';
import { UpdateInvestmentReportDto } from './dto/update-investment-report.dto';
import { StockService } from 'src/stock/stock.service';

@Controller('investment-report')
export class InvestmentReportController {
  constructor(
    private readonly investmentReportService: InvestmentReportService,
    private readonly stockService: StockService,
  ) {}

  @Get(':ticker/history')
  findHistory(
    @Param('ticker') ticker: string,
    @Query('limit') limit?: string,
  ): Promise<InvestmentReportHistoryItem[]> {
    return this.investmentReportService.findHistoryByTicker(
      ticker,
      limit ? Number(limit) : 10,
    );
  }

  @Get(':ticker')
  async getStockProfile(@Param('ticker') ticker: string) {
    return this.investmentReportService.getStockProfile(ticker);
  }

  @Get(':ticker/fundamentals')
  async getStockFundamentals(
    @Param('ticker') ticker: string,
  ): Promise<FundamentalsProfile> {
    return this.stockService.getStockFundamentals(ticker);
  }
}
