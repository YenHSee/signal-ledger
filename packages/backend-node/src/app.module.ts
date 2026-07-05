import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Stock } from './stock/entities/stock.entity';
import { StockController } from './stock/stock.controller';
import { StockService } from './stock/stock.service';
import { StockModule } from './stock/stock.module';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { InvestmentReportModule } from './investment-report/investment-report.module';
import { InvestmentReport } from './investment-report/entities/investment-report.entity';
import { DailyPrice } from './stock/entities/daily-price.entity';
import { StockNews } from './stock/entities/stock-news.entity';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: 'localhost',
      port: 5433,
      username: 'postgres',
      password: 'password123',
      database: 'stock_analyst',
      entities: [Stock, InvestmentReport, DailyPrice, StockNews],
      synchronize: false,
    }),
    TypeOrmModule.forFeature([Stock, DailyPrice, StockNews]),
    StockModule,
    InvestmentReportModule,
  ],
  // controllers: [StockController],
  // providers: [StockService],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
