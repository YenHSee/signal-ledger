import { PartialType } from '@nestjs/mapped-types';
import { CreateInvestmentReportDto } from './create-investment-report.dto';

export class UpdateInvestmentReportDto extends PartialType(CreateInvestmentReportDto) {}
