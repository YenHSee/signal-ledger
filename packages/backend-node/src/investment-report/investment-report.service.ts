import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { InvestmentReport } from './entities/investment-report.entity';

@Injectable()
export class InvestmentReportService {
  constructor(
    @InjectRepository(InvestmentReport)
    private reportRepository: Repository<InvestmentReport>,
  ) {}

  async findLatestByTicker(ticker: string) {
    const report = await this.reportRepository.findOne({
      where: { ticker },
      order: { generated_at: 'DESC' },
    });

    if (!report) {
      throw new NotFoundException(`No report found for: ${ticker}`);
    }
    return report;
  }
}
