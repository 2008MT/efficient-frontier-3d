"""Download the price data from Yahoo Finance (via yfinance) and save it to data/prices_daily.csv.

Dates are pinned so that the study can be rerun on the same sample. Yahoo occasionally revises
dividend-adjusted prices, so numbers may differ in the last decimals from those in results/.
"""
import os
import pandas as pd
import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

START = "2015-07-20"      # one week before the first weekly return
END = "2026-11-14"        # exclusive: last price is Friday 13 November 2026
FX_END = "2026-11-17"     # exchange rates need one more bar (see common.weekly_prices_usd)

# column name -> Yahoo ticker
SERIES = {
    "NVDA": "NVDA",         # Nvidia, Nasdaq, USD
    "VOO": "VOO",           # Vanguard S&P 500 ETF, NYSE Arca, USD
    "ARU": "ARU.AX",        # Arafura Rare Earths, ASX, AUD
    "SGLN": "SGLN.L",       # iShares Physical Gold ETC, LSE, quoted in pence sterling
    "AUDUSD": "AUDUSD=X",   # US dollars per Australian dollar
    "GBPUSD": "GBPUSD=X",   # US dollars per pound sterling
    "IRX": "^IRX",          # 13-week US Treasury bill yield, per cent per year
    "IGLN": "IGLN.L",       # US-dollar line of the same gold ETC (used only to check the conversion)
}


def main():
    cols = {}
    for name, ticker in SERIES.items():
        end = FX_END if ticker.endswith("=X") else END
        d = yf.download(ticker, start=START, end=end, progress=False, auto_adjust=True)
        if d.empty:
            raise RuntimeError(f"no data returned for {ticker}")
        close = d["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        cols[name] = close
        print(f"{name:>7} {ticker:<9} {len(close):5d} rows  {close.index.min().date()} to {close.index.max().date()}")
    out = pd.DataFrame(cols).sort_index()
    out.index.name = "date"
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    path = os.path.join(ROOT, "data", "prices_daily.csv")
    out.to_csv(path, float_format="%.6f")
    print(f"saved data/prices_daily.csv: {out.shape[0]} calendar days")


if __name__ == "__main__":
    main()
