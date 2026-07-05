# Stock Detail:30 天价格 Chart + AI 信号 + News

> 目标:把 detail 页面变成一个有故事性的页面 —— 30 天价格 chart 上叠加 AI 报告信号和异动日新闻 marker,下方配完整 news list。
>
> 架构原则:**Python 拿数据写 Postgres → NestJS 只读 DB → 前端只调 NestJS**(与现有 daily_prices 流程一致)。

## 最终效果

```
┌─ Headline(现有)──────────────────────────────┐
├─ PriceChart(新,全宽)─────────────────────────┤
│   · 30 天 close 价格线 + 渐变面积(SVG 自绘)      │
│   · target price 水平虚线                        │
│   · AI 报告 marker:BUY 绿 / SELL 红 / HOLD 黄    │
│   · 异动日圆点 marker,hover 显示当天新闻标题       │
├─ AI Report(现有)── │ ─ Fundamentals(现有)────┤
├─ NewsSection(新):按日期分组的 30 天新闻列表 ────┤
├─ TrackRecord(现有)───────────────────────────┤
```

### 哪些新闻会被 show?

- **NewsSection(下方 list):全部显示。** 30 天内所有新闻按日期分组(新到旧),每天默认显示前几条,可展开。
- **Chart 上的 marker:只标"异动日"。** 判断标准(纯前端从 `daily_prices` 数据计算):
  - 当天 close 相对前一天涨跌 `>= ±2%`,或
  - 当天 volume `>= 30 天平均量 × 2`
- 异动日 marker hover 显示当天新闻标题(最多 3 条),点击滚动到 NewsSection 对应日期组。
- 设计理由:30 天可能有上百条新闻,全标就是噪音;marker 只回答 "这天为什么大涨/大跌"。

### 技术选型

- **Chart:自绘 SVG**(复用 `PriceSparkline.tsx` 的 line/area/hover 模式放大),不用 TradingView lightweight-charts。原因:只有 30 个日线点,不需要 zoom/pan/蜡烛图;核心是自定义 marker 交互,SVG 更直接、零依赖、样式与现有 Tailwind 深色风格一致。以后要做蜡烛图/1 年数据/zoom 再换库。
- **News 源:Finnhub company-news**(免费,60 calls/min,支持按日期范围查询)。
  - `GET https://finnhub.io/api/v1/company-news?symbol=AAPL&from=YYYY-MM-DD&to=YYYY-MM-DD&token=KEY`
  - 返回:`id / datetime(unix 秒) / headline / summary / source / url / image`

## 前置准备(手动,一次性)

1. 到 finnhub.io 免费注册,拿 API key。
2. `packages/data-python/.env` 加 `FINNHUB_API_KEY=xxx`。
3. GitHub Actions 跑 ETL 的话,`.github/workflows/etl.yml` 对应 repo secrets 也加 `FINNHUB_API_KEY`。

---

## Phase 1:Python — 建表 + 拉取 news 入库

### 1.1 建表(`packages/data-python/utils/storage.py` → `init_tables()`)

```sql
CREATE TABLE IF NOT EXISTS stock_news (
    id BIGSERIAL PRIMARY KEY,
    finnhub_id BIGINT UNIQUE NOT NULL,      -- Finnhub 新闻 id,去重用
    symbol VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,               -- 从 datetime 转出,用于按日对齐 chart
    datetime BIGINT NOT NULL,               -- unix 秒,精确时间
    headline TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(100),
    url TEXT,
    fetched_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stock_news_symbol_date
    ON stock_news (symbol, trade_date);
```

注意:这张表是 **append/upsert 的永久档案**,不像 `daily_prices` 那样每次 truncate 重灌。旧新闻在 Finnhub 上游会过期消失,存下来 chart 才能长期按 date 查到;以后 AI 报告接 news(Recent Catalysts)也直接读这张表。

### 1.2 新建 `packages/data-python/tools/finnhub_news.py`

- `get_company_news(symbol, from_date, to_date) -> list[dict]`
- 读 `config.FINNHUB_API_KEY`;带 pacing(约 1 call/秒,守住 60/min 限制);单支失败 log + 跳过,不中断整个 pipeline。

### 1.3 Transform(`packages/data-python/utils/data_transformer.py`)

- `transform_finnhub_news_to_db(symbol, news_items) -> list[dict]`:datetime 转 `trade_date`(YYYY-MM-DD),过滤缺 headline/url 的脏数据。

### 1.4 入库(`packages/data-python/utils/storage.py`)

- `insert_stock_news(rows)`:批量 `INSERT ... ON CONFLICT (finnhub_id) DO NOTHING`。

### 1.5 ETL 接入(`packages/data-python/scripts/daily_etl_pipeline.py`)

- 新增 STEP 5(news):遍历 S&P 500 tickers:
  - 常规:每支拉最近 **3 天**(增量,容忍周末/失败的 run)。
  - 首次(表里该 symbol 无数据):backfill **30 天**。
- ~503 支 × 1 call/秒 ≈ 9 分钟,在现有 pipeline 可接受范围。
- `config.py` 加 `FINNHUB_API_KEY` 读取。

### Phase 1 验收

- 手动跑一次 pipeline(或单跑 news step),`SELECT count(*) FROM stock_news WHERE symbol='AAPL'` 有数据,`trade_date` 分布在最近 30 天。
- 重复跑不产生重复行(`finnhub_id` unique 生效)。

---

## Phase 2:API 类型 + NestJS 只读接口

### 2.1 `packages/api-types/stock/index.ts` 新增类型

```ts
export interface StockNewsItem {
  id: number;          // finnhub_id
  date: string;        // YYYY-MM-DD(= trade_date),按日对齐 chart 用
  datetime: number;    // unix 秒
  headline: string;
  summary: string;
  source: string;
  url: string;
}
```

### 2.2 NestJS(`packages/backend-node/src/stock/`)

- 新建 `entities/stock-news.entity.ts`:`StockNews` entity 映射 `stock_news` 表;注册进 `stock.module.ts` 的 `TypeOrmModule.forFeature`。
- `stock.controller.ts`:新增 `GET /api/stock/:ticker/news`。
- `stock.service.ts`:`getCompanyNews(ticker)`,纯 DB 查询:
  - `WHERE symbol = :symbol AND trade_date >= (今天 - 30 天) ORDER BY datetime DESC`
  - 映射成 `StockNewsItem[]`;无数据返回 `[]`(前端优雅降级,不报错)。

### Phase 2 验收

- `curl http://localhost:4000/api/stock/AAPL/news` 返回 30 天内的新闻 JSON;不存在的 ticker 返回 `[]`。

---

## Phase 3:前端 — PriceChart + NewsSection

### 3.1 新建 `packages/frontend-web/src/pages/stock/detail/PriceChart.tsx`

Props:`prices: DailyPricePoint[]`、`history: InvestmentReportHistoryItem[]`、`targetPrice: number | null`、`news: StockNewsItem[]`、`onNewsDayClick?: (date: string) => void`。`PriceSparkline.tsx` 保持不动。

组件内部分四层:

#### A. 数据准备层(`useMemo` 纯计算)

1. **坐标系**:x 按交易日 index 均分(不按日历天,周末无数据不留空隙);y 取 30 天 close 的 min/max 加 padding。**target price 在价格区间 ±30% 内时纳入 y 域**(保证虚线画得进来),超出太远则不画线、只在角落文字提示。
2. **每日涨跌** `dailyChanges: Map<date, pct>`:close 相对前一日的百分比。
3. **异动日集合** `Set<date>`:`|涨跌| >= 2%` 或 `volume >= 2 × 30 日均量`。
4. **新闻按日索引** `newsByDate: Map<date, StockNewsItem[]>`:每天的数组先过 `rankDayNews`(见 3.2)。
5. **AI 信号定位**:`history` 中落在窗口内的报告,`generatedAt` 映射到**最近的交易日 index**(报告可能周末生成);y 用 `priceAtGeneration`,缺失则用该日 close。

#### B. SVG 渲染层(自底向顶)

1. 渐变 area + 价格 line(复用 sparkline 画法,全宽响应式,高约 220px)
2. y 轴 3~4 个价格刻度 + 横向淡格线;x 轴每 5~7 天一个日期标签
3. target price 水平虚线 + 右端 `Target $XXX` 标签
4. 异动日 marker:该日 close 处圆点(有新闻:实心 + 外圈;无新闻:空心弱化)
5. AI 信号 marker:BUY 绿▲ / SELL 红▼ / HOLD 黄◆ 徽标,画在价格线上方偏移处,避免与异动日圆点重叠
6. hover 捕捉层:每个交易日一个透明竖条 rect(sparkline 同款)→ crosshair 虚线 + 当前点圆点

#### C. Tooltip / 交互层(HTML absolute overlay,不在 SVG 内)

1. **普通 hover**:日期 + close + 当日涨跌
2. **异动日 hover**:涨跌幅高亮 + top 3 新闻标题 + `"+ N more…"`;**点击**触发 `onNewsDayClick(date)` 滚动到 NewsSection 对应组
3. **AI marker hover**:conclusion + 当时价格 + 生成日期
4. 边界处理:tooltip 靠容器左/右边缘时翻转方向
5. 三种 tooltip 互斥,优先级:AI marker > 异动日 > 普通 hover

#### D. 头部与空态

1. 卡片头:标题 "30-Day Price" + 区间累计涨跌幅 + 图例(target 线 / AI 信号 / 异动日说明)
2. `prices.length < 2` → "No chart data" 空态;`news` 为空时 chart 照常渲染,仅无新闻 tooltip

### 3.2 同一天 N 条新闻的处理(dedup + ranking)

热门股一天 20~100 条新闻是常态,且有大量重复转发和 "3 Stocks to Buy" 类 listicle 垃圾。策略:**DB 全存不筛,display 前排序去重,UI 固定只露 top 3**。

在 `detail/utils.ts`(或新建 `newsUtils.ts`)加一个 `rankDayNews(items): StockNewsItem[]`:

1. **去重**:headline 归一化(小写、去标点)后相同的只留一条,保留 source tier 最高的 —— 干掉同一篇稿被多个网站转发的情况。
2. **Source tier 排序**:
   - Tier 1:reuters、bloomberg、cnbc、wsj、barrons、ft、marketwatch、yahoo 等一手媒体
   - Tier 2:benzinga、investing.com 等
   - Tier 3(listicle 大户,垫底):zacks、seekingalpha、fool、investorplace
   - 未知 source 归 Tier 2.5;同 tier 内按 datetime 新到旧。
3. 排序结果决定"哪 3 条露出来"。

### 3.3 新建 `packages/frontend-web/src/pages/stock/detail/NewsSection.tsx`

Props:`news: StockNewsItem[]`、`dailyChanges: Map<string, number>`(由 prices 算出)。

- 按 `date` 分组,新到旧;组头显示 `日期 + 当日涨跌幅 + 新闻总数`(如 `Jul 3 · -4.2% · 27 条`),异动日加高亮 badge。
- 每组经 `rankDayNews` 排序后默认只显示 **top 3**,底部 "Show all N" 展开全部(展开后组内 max-height + 滚动,防止一天 100 条撑爆页面)。
- 每条:headline(`<a target="_blank" rel="noopener noreferrer">` 外链)、source、时间。
- 每组容器 `id={"news-" + date}`,供 chart 点击滚动(`scrollIntoView`)。

### 3.4 接线 `packages/frontend-web/src/pages/stock/detail/index.tsx`

- `Promise.allSettled` 加第 5 个请求:`${API_BASE}/stock/${ticker}/news`,失败置 `[]`。
- `<Headline />` 下方插入全宽卡片放 `<PriceChart />`。
- `<TrackRecord />` 上方插入 `<NewsSection />`。

### Phase 3 验收

- 打开一个有报告 + 有新闻的 ticker:chart 显示价格线、target 线、AI 标记、异动日圆点;hover 各类 marker tooltip 正确;点异动日圆点滚动到对应新闻组;新闻外链可打开。
- 无新闻/无报告的 ticker:chart 正常显示纯价格线,NewsSection 显示空态,不报错。

---

## Phase 4(以后,不在本次范围)

- **News 反哺 AI 报告**:报告生成时从 `stock_news` 读最近 30 天新闻作为 LLM context,报告加 "Recent Catalysts" 章节(接上 `tools/web_research.py` 当年没接的意图)。
- **异动日 LLM 一句话摘要**:用现有 LLM pipeline 把异动日的新闻压缩成一句 "这天发生了什么"(如 "Q2 财报超预期,上调指引"),chart tooltip 和 NewsSection 组头直接显示这句,替代 top 3 标题 —— 一天 N 条新闻的终极解法。
- Sentiment 分析 / chart 下方情绪色带。
- 换 TradingView lightweight-charts(若要蜡烛图、更长时间范围、zoom/pan)。

---

## 决策记录

| 决策点 | 选择 | 理由 |
| --- | --- | --- |
| News 源 | Finnhub company-news | 免费、支持按日期范围查、60 calls/min 够用;Alpha Vantage 免费版 25 req/天太少;yfinance 只有最近 ~10 条无法按日期查 |
| 谁去拿 news | Python ETL(非 NestJS 代理) | 与现有 "Python 拿数据入库,Node 只读" 架构一致;NestJS 不用配 key;代价是新闻最多滞后 24h,对日线 chart 可接受 |
| 存不存 DB | 存,`stock_news` 永久 upsert | 上游旧新闻会过期;为 Phase 4 AI 报告铺路;按 finnhub_id 去重 |
| 全量 or 按需拉 | ETL 全量(S&P 500) | 用户要求统一 Python 入库;~9 分钟/天在限额内 |
| Chart 实现 | 自绘 SVG | 仅 30 个点,核心是自定义 marker 交互;lightweight-charts 的能力(zoom/蜡烛)用不上,自定义 tooltip 反而更麻烦 |
| Marker 筛选 | 异动日(±2% 或 2× volume) | 避免每天都标造成噪音;完整新闻在下方 list 不丢失 |
| 一天 N 条新闻 | DB 全存;display 前 dedup + source tier 排序;UI 固定露 top 3 + 展开 | 热门股一天几十条且多为转发/listicle;tier 排序保证露出的是一手媒体;结构上不管 2 条还是 100 条页面都稳定 |
