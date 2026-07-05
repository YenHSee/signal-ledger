import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';
import type { RawFinancialSnapshot } from '@stock-analyst/api-types';

@Entity('investment_reports')
export class InvestmentReport {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ length: 10 })
  ticker: string;

  @Column({ length: 10, nullable: true })
  model_tier: string;

  @Column({ length: 50, nullable: true })
  conclusion: string;

  @Column({ length: 50, nullable: true })
  conviction_level: string;

  // 如果 Python 传过来的是字符串形式的数字，TypeORM 也会帮你转
  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  target_price: number;

  @Column({ length: 20, nullable: true })
  upside_downside_pct: string;

  @Column({ length: 20, nullable: true })
  risk_level: string;

  @Column({ type: 'text', nullable: true })
  reasoning: string;

  @Column({ type: 'text', nullable: true })
  full_report: string;

  @Column({ type: 'jsonb', nullable: true })
  raw_financial_data: RawFinancialSnapshot | null;

  @Column({ type: 'timestamptz', default: () => 'CURRENT_TIMESTAMP' })
  generated_at: Date;
}
