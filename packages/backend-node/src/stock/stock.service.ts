import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Stock } from './entities/stock.entity';
import { InvestmentReport } from '../investment-report/entities/investment-report.entity';

@Injectable()
export class StockService {
  constructor(
    @InjectRepository(Stock)
    private stockRepository: Repository<Stock>,

    @InjectRepository(InvestmentReport)
    private reportRepository: Repository<InvestmentReport>,
  ) {}

  async getCompanyList(page: number = 1, limit: number = 100) {
    const skip = (page - 1) * limit;

    // 🌟 架构师级写法：使用 QueryBuilder 进行跨表 JOIN，只拿需要的字段！
    const query = this.stockRepository
      .createQueryBuilder('stock')
      // 左连接 investment_reports 表，条件是 stock.symbol == report.ticker
      .leftJoin(
        this.reportRepository.metadata.target,
        'report',
        'stock.symbol = report.ticker',
      )
      .select([
        'stock.symbol AS symbol',
        'stock.name AS name',
        'stock.pe_ratio AS pe_ratio',
        // 👇 从 Report 表里抓取极具吸引力的 AI 数据
        'report.conclusion AS ai_signal',
        'report.conviction_level AS conviction',
        'report.upside_downside_pct AS upside',
      ])
      .orderBy('stock.market_capitalization', 'DESC') // 比如按市值从大到小排
      .limit(limit)
      .offset(skip);

    // 获取原始联表数据
    const data = await query.getRawMany();

    // 获取总数（用于前端算总页数）
    const total = await this.stockRepository.count();

    return {
      data,
      total,
      page,
      totalPages: Math.ceil(total / limit),
    };
  }
}
