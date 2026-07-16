import { Entity, Column, PrimaryColumn, Index } from 'typeorm';

@Entity('stock_news')
@Index(['symbol', 'trade_date'])
export class StockNews {
  @PrimaryColumn({ type: 'bigint' })
  finnhub_id: number;

  @Column({ length: 10 })
  symbol: string;

  @Column({ type: 'date' })
  trade_date: string;

  @Column({ type: 'bigint' })
  datetime: number;

  @Column({ type: 'text' })
  headline: string;

  @Column({ type: 'text', nullable: true })
  summary: string;

  @Column({ length: 255, nullable: true })
  source: string;

  @Column({ type: 'text', nullable: true })
  url: string;

  @Column({ type: 'timestamptz', nullable: true })
  fetched_at: Date;
}
