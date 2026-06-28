import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { StockService } from './stock.service';
import { StockController } from './stock.controller';
import { Stock } from './entities/stock.entity';
import { InvestmentReport } from '../investment-report/entities/investment-report.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Stock, InvestmentReport])],
  controllers: [StockController],
  providers: [StockService],
  exports: [StockService],
})
export class StockModule {}
