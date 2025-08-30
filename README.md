# StockSignals

# Trade Signal Scanners

This repository contains two Python scripts that scan major U.S. stock indices and generate trade signals using popular technical indicators.

Included Scanners:

1. S&P 500 Scanner
- Downloads daily price data for all S&P 500 tickers from Yahoo Finance.
- Computes indicators:
  - RSI (Relative Strength Index)
  - SMA Crossovers
  - MACD
  - Bollinger Bands
- Generates buy/sell signals and saves them to a local Excel file, with separate sheets per indicator.

2. Russell 1000 Scanner
- Loads Russell 1000 tickers from a local CSV file.
- Downloads daily price data and computes the same indicators as the S&P 500 scanner.
- Saves results to Excel with separate sheets per indicator and an optional `Multi_Signals` sheet for tickers triggering multiple signals.

*Requirements*
- Python 3.8+
- Packages: `pandas`, `numpy`, `yfinance`, `tqdm`, `xlsxwriter`

pip install pandas numpy yfinance tqdm xlsxwriter
