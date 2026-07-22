# Third-Party Data Notice

SignalLedger's source code is licensed under the repository's MIT License. That
license does not automatically apply to market data, news metadata, company
filings, trademarks, or other third-party material used by the application.

## Local sample fixture

The frozen sample fixture is a small educational and development preview. It is
not offered as a standalone market-data product, a complete historical archive,
or a substitute for obtaining data from the original providers.

The current fixture records the following provenance:

| Material | Source | Included scope |
| --- | --- | --- |
| Daily OHLCV | Yahoo Finance, accessed through `yfinance` | Ten tickers, 2026 YTD |
| News metadata | Finnhub company-news API | Date, source, headline, URL, and ticker; summaries are empty |
| Filing facts | SEC EDGAR/XBRL APIs | Point-in-time filing metadata and selected numeric facts |
| AI research reports | DeepSeek | AI-generated analysis from frozen point-in-time inputs |

The fixture preserves provider attribution and does not claim that SignalLedger
created or owns the underlying market facts, news headlines, company filings,
or provider trademarks. The sample dataset remains marked `draft` with
`redistributionReview: pending`; no separate open-data license is granted for
third-party material by this repository.

Official terms and policies include:

- [Yahoo API Terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apitnc/index.html)
- [yfinance project notice](https://github.com/ranaroussi/yfinance)
- [Finnhub registration and usage notice](https://finnhub.io/register)
- [SEC reuse FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)
- [DeepSeek Terms of Use](https://cdn.deepseek.com/policies/en-US/deepseek-terms-of-use.html)

The DeepSeek-generated reports are labelled as AI research. They may contain
errors and are not financial advice.

## Live and hosted operation

SignalLedger supports different operating contexts:

- **Personal/self-hosted live mode:** the operator supplies their own provider
  accounts and API keys and is responsible for using each service within the
  terms attached to that account.
- **Public hosted mode:** an operator who displays provider data to third parties
  may need commercial, display, or redistribution rights from the relevant
  provider. A personal API plan should not be assumed to cover this use.
- **Raw data export or resale:** SignalLedger does not grant rights to redistribute
  or resell third-party data obtained through the application.

Provider adapters, ETL logic, report provenance, and the database schema are
separate from any particular vendor. A provider can be removed or replaced
without abandoning the SignalLedger application or its historical ledger model.

## Concerns and removal

If you are a rights holder and believe a committed sample record should be
removed or corrected, please open a repository issue identifying the material
and the basis for the request. The maintainer will review the request and can
remove or replace affected fixture records. This process is not a substitute
for obtaining any permission required by applicable terms or law.
