import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';

@Entity('investment_reports')
export class InvestmentReport {
  // 🌟 强烈建议加一个自增的主键 ID，方便以后查询单篇报告
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

  // 🌟 PostgreSQL 最牛逼的特性 jsonb，直接无缝存储前端传来的巨型 JSON
  @Column({ type: 'jsonb', nullable: true })
  raw_financial_data: any;

  @Column({ type: 'timestamptz', default: () => 'CURRENT_TIMESTAMP' })
  generated_at: Date;
}
