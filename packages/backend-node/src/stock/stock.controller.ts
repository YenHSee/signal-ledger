import {
  Controller,
  Get,
  Post,
  Body,
  Patch,
  Param,
  Delete,
  Query,
} from '@nestjs/common';
import { StockService } from './stock.service';

@Controller('stock')
export class StockController {
  constructor(private readonly stockService: StockService) {}

  @Get()
  async getCompanies(
    @Query('page') page: number = 1,
    @Query('limit') limit: number = 100,
  ) {
    return await this.stockService.getCompanyList(Number(page), Number(limit));
  }
}
