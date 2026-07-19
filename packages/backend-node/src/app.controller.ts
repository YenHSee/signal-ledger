import { Controller, Get } from '@nestjs/common';
import type { HealthStatus, RuntimeMeta } from '@signal-ledger/api-types';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  getHello(): string {
    return this.appService.getHello();
  }

  @Get('meta')
  getMeta(): RuntimeMeta {
    return this.appService.getMeta();
  }

  @Get('health')
  getHealth(): Promise<HealthStatus> {
    return this.appService.getHealth();
  }
}
