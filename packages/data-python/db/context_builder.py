import psycopg2.extras

from db.connection import get_connection, release_connection


def build_ai_context(ticker: str):
    """读时计算：把公司基本面、日线动量和近 7 天新闻组装成喂给 LLM 的 context dict"""
    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM company_overview WHERE symbol = %s", (ticker.upper(),))
        overview = cursor.fetchone()
        if not overview: return None

        cursor.execute("""
            SELECT trade_date, close_price FROM daily_prices 
            WHERE symbol = %s ORDER BY trade_date DESC LIMIT 15
        """, (ticker.upper(),))
        prices = cursor.fetchall()

        # 现价优先级：实时报价(overview.current_price) 优先，daily_prices 最新收盘价兜底
        if overview['current_price']:
            current_price = float(overview['current_price'])
        elif prices:
            current_price = float(prices[0]['close_price'])
        else:
            current_price = 0
            print(f"⚠️ {ticker.upper()} 无可用现价数据 (overview.current_price 和 daily_prices 均为空)")

        price_3_weeks_ago = float(prices[-1]['close_price']) if len(prices) == 15 else current_price

        recent_price_change_pct = 0
        if price_3_weeks_ago > 0:
            recent_price_change_pct = round((current_price - price_3_weeks_ago) / price_3_weeks_ago, 4)

        high_52 = float(overview['week_52_high']) if overview['week_52_high'] else 0
        low_52 = float(overview['week_52_low']) if overview['week_52_low'] else 0
        current_position_pct = 0
        if high_52 > low_52 and current_price > 0:
            current_position_pct = round((current_price - low_52) / (high_52 - low_52), 4)

        # 近 7 天新闻作为催化剂线索，随 context 一起归档进报告快照
        cursor.execute("""
            SELECT headline, source, trade_date FROM stock_news
            WHERE symbol = %s AND trade_date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY trade_date DESC LIMIT 8
        """, (ticker.upper(),))
        news_rows = cursor.fetchall()
        recent_catalysts = [
            {
                "date": row['trade_date'].isoformat(),
                "source": row['source'],
                "headline": row['headline']
            } for row in news_rows
        ]

        return {
            "company_identity": {
                "symbol": overview['symbol'], "name": overview['name'], "sector": overview['sector'],
                "business_summary": overview['description'][:300] if overview['description'] else "N/A"
            },
            "profitability_and_scale": {
                "market_cap": float(overview['market_capitalization'] or 0),
                "profit_margin": float(overview['profit_margin'] or 0),
                "return_on_equity_ttm": float(overview['return_on_equity_ttm'] or 0)
            },
            "valuation_and_growth": {
                "trailing_pe": float(overview['trailing_pe'] or 0), "forward_pe": float(overview['forward_pe'] or 0),
                "peg_ratio": float(overview['peg_ratio'] or 0),
                "earnings_growth_yoy": float(overview['quarterly_earnings_growth_yoy'] or 0),
                "revenue_growth_yoy": float(overview['quarterly_revenue_growth_yoy'] or 0) 
            },
            "smart_money_consensus": {
                "percent_institutions": float(overview['percent_institutions'] or 0),
                "analyst_target_price": float(overview['analyst_target_price'] or 0), "current_price": current_price
            },
            "technical_and_momentum": {
                "moving_averages": {
                    "day_50_ma": float(overview['day_50_moving_average'] or 0),
                    "day_200_ma": float(overview['day_200_moving_average'] or 0)
                },
                "week_52_range": {"high": high_52, "low": low_52, "current_position_pct": current_position_pct},
                "recent_3_weeks_action": {"price_change_pct": recent_price_change_pct}
            },
            "recent_catalysts": recent_catalysts
        }
    except Exception as e:
        print(f"❌ 组装 AI Context 失败: {e}")
        return None
    finally:
        if cursor: cursor.close()
        release_connection(connection, is_from_pool)
