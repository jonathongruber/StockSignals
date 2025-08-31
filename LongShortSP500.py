import pandas as pd
import yfinance as yf
import numpy as np
import os
from tqdm import tqdm

# PARAMETERS
RSI_PERIOD = 14
SMA_SHORT = 20
SMA_LONG = 50
SMA_LONG2 = 200  # For long-term trend

# Set output folder on your local drive
OUTPUT_DIR = r"C:\Users\grube\OneDrive\Desktop\Python_Projects\SP500"
os.makedirs(OUTPUT_DIR, exist_ok=True)  # create folder if it doesn't exist
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sp500_trade_signals.xlsx")

# FETCH S&P 500 TICKERS
def get_sp500_tickers():
    url = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
    try:
        tickers = pd.read_csv(url)["Symbol"].tolist()
        print(f"Retrieved {len(tickers)} S&P 500 tickers")
        return tickers
    except Exception as e:
        print(f"Error retrieving tickers: {e}")
        return []

# COMPUTE INDICATORS AND SIGNALS
def compute_signals(df):
    signals = []
    try:
        close = df["Close"].squeeze()
        date = df.index[-1].date()

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        roll_up = gain.rolling(RSI_PERIOD).mean()
        roll_down = loss.rolling(RSI_PERIOD).mean()
        rs = np.divide(roll_up, roll_down, out=np.zeros_like(roll_up), where=roll_down != 0)
        rsi = 100 - (100 / (1 + rs))
        last_rsi = rsi.iloc[-1]
        if last_rsi < 30:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "RSI",
                            "Value": round(last_rsi,1), "Signal": "Buy", "Date": date})
        elif last_rsi > 70:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "RSI",
                            "Value": round(last_rsi,1), "Signal": "Sell", "Date": date})

        # SMA Crossovers
        sma_short = close.rolling(SMA_SHORT).mean()
        sma_long = close.rolling(SMA_LONG).mean()
        sma_long2 = close.rolling(SMA_LONG2).mean()
        if sma_short.iloc[-2] < sma_long.iloc[-2] and sma_short.iloc[-1] > sma_long.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "SMA_Cross",
                            "Value": f"{SMA_SHORT}>{SMA_LONG}", "Signal": "Buy", "Date": date})
        elif sma_short.iloc[-2] > sma_long.iloc[-2] and sma_short.iloc[-1] < sma_long.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "SMA_Cross",
                            "Value": f"{SMA_SHORT}<{SMA_LONG}", "Signal": "Sell", "Date": date})

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-2] < signal_line.iloc[-2] and macd.iloc[-1] > signal_line.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "MACD",
                            "Value": round(macd.iloc[-1],2), "Signal": "Buy", "Date": date})
        elif macd.iloc[-2] > signal_line.iloc[-2] and macd.iloc[-1] < signal_line.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "MACD",
                            "Value": round(macd.iloc[-1],2), "Signal": "Sell", "Date": date})

        # Bollinger Bands
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper = sma20 + 2 * std20
        lower = sma20 - 2 * std20
        if close.iloc[-1] < lower.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "Bollinger",
                            "Value": round(lower.iloc[-1],2), "Signal": "Buy", "Date": date})
        elif close.iloc[-1] > upper.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "Bollinger",
                            "Value": round(upper.iloc[-1],2), "Signal": "Sell", "Date": date})

    except Exception as e:
        print(f"Error computing signals for {df.name}: {e}")

    return signals

# MAIN SCANNER
def run_scanner():
    tickers = get_sp500_tickers()
    if not tickers:
        return

    all_signals = []
    print(f"\n--- Scanning {len(tickers)} tickers ---")
    for ticker in tqdm(tickers):
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=False)
            if df.empty:
                continue
            df.name = ticker
            signals = compute_signals(df)
            all_signals.extend(signals)
        except Exception as e:
            print(f"Error downloading {ticker}: {e}")
            continue

    if not all_signals:
        print("No signals detected.")
        return

    # SAVE TO EXCEL
    signals_df = pd.DataFrame(all_signals)
    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        # Save each indicator as its own sheet
        for indicator in signals_df["Indicator"].unique():
            df_ind = signals_df[signals_df["Indicator"] == indicator]
            df_ind.to_excel(writer, sheet_name=indicator, index=False)

        # --- Multi-Signals sheet ---
        multi_df = (signals_df.groupby("Ticker")
                               .filter(lambda x: len(x) > 1)
                               .sort_values(by=["Ticker", "Date"]))
        if not multi_df.empty:
            multi_df.to_excel(writer, sheet_name="Multi_Signals", index=False)

    print(f"\n✅ Signals saved to {OUTPUT_FILE}")

# EXECUTE
if __name__ == "__main__":
    run_scanner()
