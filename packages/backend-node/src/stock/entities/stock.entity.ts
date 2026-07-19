import { Entity, Column, PrimaryColumn, UpdateDateColumn } from 'typeorm';

@Entity('company_overview')
export class Stock {
  @PrimaryColumn({ length: 10 })
  symbol: string;

  @Column({ nullable: true, length: 50 })
  asset_type: string;

  @Column({ nullable: true, length: 255 })
  name: string;

  @Column({ type: 'text', nullable: true })
  description: string;

  @Column({ nullable: true, length: 20 })
  cik: string;

  @Column({ nullable: true, length: 50 })
  exchange: string;

  @Column({ nullable: true, length: 10 })
  currency: string;

  @Column({ nullable: true, length: 50 })
  country: string;

  @Column({ nullable: true, length: 100 })
  sector: string;

  @Column({ nullable: true, length: 100 })
  industry: string;

  @Column({ type: 'text', nullable: true })
  address: string;

  @Column({ type: 'text', nullable: true })
  official_site: string;

  @Column({ nullable: true, length: 20 })
  fiscal_year_end: string;

  @Column({ type: 'date', nullable: true })
  latest_quarter: Date;

  @Column({ type: 'bigint', nullable: true })
  market_capitalization: number;

  @Column({ type: 'bigint', nullable: true })
  ebitda: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  pe_ratio: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  peg_ratio: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  book_value: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  dividend_per_share: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  dividend_yield: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  eps: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  revenue_per_share_ttm: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  profit_margin: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  operating_margin_ttm: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  return_on_assets_ttm: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  return_on_equity_ttm: number;

  @Column({ type: 'bigint', nullable: true })
  revenue_ttm: number;

  @Column({ type: 'bigint', nullable: true })
  gross_profit_ttm: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  diluted_eps_ttm: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  quarterly_earnings_growth_yoy: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  quarterly_revenue_growth_yoy: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  analyst_target_price: number;

  @Column({ nullable: true })
  analyst_rating_strong_buy: number;

  @Column({ nullable: true })
  analyst_rating_buy: number;

  @Column({ nullable: true })
  analyst_rating_hold: number;

  @Column({ nullable: true })
  analyst_rating_sell: number;

  @Column({ nullable: true })
  analyst_rating_strong_sell: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  trailing_pe: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  forward_pe: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  price_to_sales_ratio_ttm: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  price_to_book_ratio: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  ev_to_revenue: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  ev_to_ebitda: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  beta: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  week_52_high: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  week_52_low: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  day_50_moving_average: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  day_200_moving_average: number;

  @Column({ type: 'bigint', nullable: true })
  shares_outstanding: number;

  @Column({ type: 'bigint', nullable: true })
  shares_float: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  percent_insiders: number;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  percent_institutions: number;

  @Column({ type: 'date', nullable: true })
  dividend_date: Date;

  @Column({ type: 'date', nullable: true })
  ex_dividend_date: Date;

  @Column({ default: false })
  is_sp500: boolean;

  @Column({ type: 'decimal', precision: 10, scale: 4, nullable: true })
  current_price: number;

  @Column({ type: 'timestamptz', nullable: true })
  price_as_of: Date;

  @UpdateDateColumn({ type: 'timestamptz', default: () => 'CURRENT_TIMESTAMP' })
  last_updated: Date;
}
