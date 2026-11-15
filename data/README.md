# Data

Prices come from Yahoo Finance and are not stored in this repository. `python code/fetch_data.py`
downloads them to `data/prices_daily.csv` with fixed start and end dates.

| column   | Yahoo ticker | content                                                                    |
|----------|--------------|----------------------------------------------------------------------------|
| `NVDA`   | `NVDA`       | Nvidia, US dollars                                                         |
| `VOO`    | `VOO`        | Vanguard S&P 500 ETF, US dollars                                           |
| `ARU`    | `ARU.AX`     | Arafura Rare Earths, Australian dollars                                    |
| `SGLN`   | `SGLN.L`     | iShares Physical Gold ETC, pence sterling                                  |
| `AUDUSD` | `AUDUSD=X`   | US dollars per Australian dollar                                           |
| `GBPUSD` | `GBPUSD=X`   | US dollars per pound                                                       |
| `IRX`    | `^IRX`       | 13-week US Treasury-bill yield, per cent a year                            |
| `IGLN`   | `IGLN.L`     | US-dollar line of the same gold ETC, used only to check the conversion     |

Prices are adjusted for dividends and splits. The file has one row per calendar day on which any
market traded, from 20 July 2015 to 13 November 2026, with blanks where a market was closed.

Two things to know before reusing the data:

- **Exchange-rate timing.** Yahoo stamps a daily exchange-rate bar with the rate at the start of that
  UTC day. `common.weekly_prices_usd` therefore converts each closing price with the *next* bar.
  With the same-day bar, SGLN in dollars has a weekly correlation of 0.92 with IGLN (the same fund
  traded in dollars); with the next bar it is 0.97.
- **Revisions.** Yahoo recomputes adjusted prices when dividends are paid, so a later download can
  differ from the one behind `results/` (15 November 2026) in the last decimals.
