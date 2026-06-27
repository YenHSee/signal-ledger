import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('company_overview')
export class Stock {
  @PrimaryColumn({ name: 'symbol' })
  symbol: string;

  @Column({ name: 'asset_type', nullable: true })
  assetType: string;

  @Column({ nullable: true })
  name: string;

  @Column({ type: 'text', nullable: true })
  description: string;

  @Column({ nullable: true })
  exchange: string;

  @Column({ nullable: true })
  sector: string;

  @Column({ nullable: true })
  industry: string;

  @Column({ name: 'market_capitalization', type: 'bigint', nullable: true })
  marketCap: string; // BigInt 在 JS 中用 string 接收以防精度丢失

  @Column({
    name: 'pe_ratio',
    type: 'decimal',
    precision: 10,
    scale: 4,
    nullable: true,
  })
  peRatio: number;

  @Column({
    name: 'peg_ratio',
    type: 'decimal',
    precision: 10,
    scale: 4,
    nullable: true,
  })
  pegRatio: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  eps: number;

  @Column({
    name: 'last_updated',
    type: 'timestamp with time zone',
    nullable: true,
  })
  lastUpdated: Date;
}
