import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Stock } from './entities/stock.entity';

@Injectable()
export class StockService {
  constructor(
    @InjectRepository(Stock)
    private stockRepository: Repository<Stock>,
  ) {}

  async getScreenerStocks() {
    // 1. 去数据库把所有公司捞出来
    const rawStocks = await this.stockRepository.find();

    // 2. 将生硬的数据库字段，洗成前端 UI 直接能用的 JSON 格式
    return rawStocks.map(stock => {
      let aiSignal = 'HOLD';
      if (Number(stock.pegRatio) > 0 && Number(stock.pegRatio) < 1.2) {
        aiSignal = 'STRONG BUY';
      } else if (Number(stock.peRatio) > 35) {
        aiSignal = 'SELL';
      }

      return {
        ticker: stock.symbol,
        name: stock.name,
        price: 150.00, // 暂时写死，后续可以关联价格表
        change: "+1.2%",
        isUp: true,
        aiSignal: aiSignal,
        keywords: [`PE: ${Number(stock.peRatio).toFixed(1)}`, stock.sector?.toUpperCase()].filter(Boolean),
      };
    });
  }
}
