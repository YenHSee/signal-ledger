import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Stock } from './stock/entities/stock.entity';
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
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5433', 10),
      username: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'password123',
      database: process.env.DB_NAME || 'signal_ledger',
      entities: [Stock, InvestmentReport, DailyPrice, StockNews],
      synchronize: false,
    }),
    TypeOrmModule.forFeature([Stock, DailyPrice, StockNews]),
    StockModule,
    InvestmentReportModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
