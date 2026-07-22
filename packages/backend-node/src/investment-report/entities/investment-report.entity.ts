import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';
import type { RawFinancialSnapshot } from '@signal-ledger/api-types';
import type { AgentOutput, GenerationMetadata } from '@signal-ledger/api-types';

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

  // TypeORM also converts numeric strings received from the Python pipeline.
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

  @Column({ type: 'integer', nullable: true })
  report_schema_version: number | null;

  @Column({ type: 'timestamptz', nullable: true })
  analysis_as_of: Date | null;

  @Column({ type: 'varchar', length: 50, nullable: true })
  generation_mode: string | null;

  @Column({ type: 'varchar', length: 50, nullable: true })
  model_provider: string | null;

  @Column({ type: 'varchar', length: 255, nullable: true })
  model_name: string | null;

  @Column({ type: 'varchar', length: 100, nullable: true })
  prompt_version: string | null;

  @Column({ type: 'jsonb', nullable: true })
  agent_outputs: AgentOutput[] | null;

  @Column({ type: 'jsonb', nullable: true })
  generation_metadata: GenerationMetadata | null;

  @Column({ type: 'timestamptz', default: () => 'CURRENT_TIMESTAMP' })
  generated_at: Date;
}
