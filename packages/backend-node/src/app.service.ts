import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import { DataSource } from 'typeorm';
import type { HealthStatus, RuntimeMeta } from '@signal-ledger/api-types';
import { getAppMode, getRuntimeMeta } from './runtime-mode';

@Injectable()
export class AppService {
  constructor(private readonly dataSource: DataSource) {}

  getHello(): string {
    return 'Hello World!';
  }

  getMeta(): RuntimeMeta {
    return getRuntimeMeta();
  }

  async getHealth(): Promise<HealthStatus> {
    try {
      await this.dataSource.query('SELECT 1');
      return {
        status: 'ok',
        database: 'connected',
        mode: getAppMode(),
      };
    } catch {
      throw new ServiceUnavailableException('Database is unavailable');
    }
  }
}
