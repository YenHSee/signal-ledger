import { Controller, Get, Post, Patch, Param, Delete } from '@nestjs/common';
import { InvestmentReportService } from './investment-report.service';
import { CreateInvestmentReportDto } from './dto/create-investment-report.dto';
import { UpdateInvestmentReportDto } from './dto/update-investment-report.dto';

@Controller('investment-report')
export class InvestmentReportController {
  constructor(
    private readonly investmentReportService: InvestmentReportService,
  ) {}

  @Get(':ticker')
  findOne(@Param('ticker') ticker: string) {
    return this.investmentReportService.findLatestByTicker(ticker);
  }
}
