// src/app.module.ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Stock } from './stock.entity';
import { StockController } from './stock.controller';
import { StockService } from './stock.service';
import { StockModule } from './stock/stock.module';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: 'localhost',
      port: 5433, // ⭐️ 之前改过的 Mac 门牌号
      username: 'postgres',
      password: 'password123',
      database: 'stock_analyst', // 数据库名
      entities: [Stock], // 告诉 NestJS 我们的股票地图
      synchronize: false, // 🚨 铁律：必须是 false，由 Python 维护表结构
    }),
    TypeOrmModule.forFeature([Stock]),
    StockModule, // 注入 Stock 仓库
  ],
  controllers: [StockController],
  providers: [StockService],
})
export class AppModule {}
