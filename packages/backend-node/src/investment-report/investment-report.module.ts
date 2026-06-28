import { Module } from '@nestjs/common';
import { InvestmentReportService } from './investment-report.service';
import { InvestmentReportController } from './investment-report.controller';
import { TypeOrmModule } from '@nestjs/typeorm';
import { InvestmentReport } from './entities/investment-report.entity';

@Module({
  imports: [TypeOrmModule.forFeature([InvestmentReport])],
  controllers: [InvestmentReportController],
  providers: [InvestmentReportService],
  exports: [TypeOrmModule],
})
export class InvestmentReportModule {}
