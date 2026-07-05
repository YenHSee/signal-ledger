import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('daily_prices')
export class DailyPrice {
  @PrimaryColumn({ length: 10 })
  symbol: string;

  @PrimaryColumn({ type: 'date' })
  trade_date: string;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  open_price: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  high_price: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  low_price: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  close_price: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  adjusted_close: number;

  @Column({ type: 'bigint', nullable: true })
  volume: number;
}
