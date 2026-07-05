import { Module } from '@nestjs/common';
import { InvestmentReportService } from './investment-report.service';
import { InvestmentReportController } from './investment-report.controller';
import { TypeOrmModule } from '@nestjs/typeorm';
import { InvestmentReport } from './entities/investment-report.entity';
import { Stock } from 'src/stock/entities/stock.entity';
import { DailyPrice } from 'src/stock/entities/daily-price.entity';
import { StockService } from 'src/stock/stock.service';

@Module({
  imports: [TypeOrmModule.forFeature([InvestmentReport, Stock, DailyPrice])],
  controllers: [InvestmentReportController],
  providers: [InvestmentReportService, StockService],
  exports: [TypeOrmModule],
})
export class InvestmentReportModule {}
