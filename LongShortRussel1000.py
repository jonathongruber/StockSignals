import pandas as pd
import yfinance as yf
import numpy as np
import os
from tqdm import tqdm
import warnings

# --- Suppress all warnings to clean up output ---
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# ------------------------
# PARAMETERS
# ------------------------
RSI_PERIOD = 14
SMA_SHORT = 20
SMA_LONG = 50
SMA_LONG2 = 200  # For long-term trend
HOLDINGS_FILE_PATH = r"C:\Users\grube\OneDrive\Desktop\Python_Projects\Divergence\IWB_holdings.csv"

# Construct the output file path based on the holdings file's directory
output_directory = os.path.dirname(HOLDINGS_FILE_PATH)
OUTPUT_FILE = os.path.join(output_directory, "russel1000_trade_signals.xlsx")

# ------------------------
# FETCH RUSSELL 1000 TICKERS
# ------------------------
def get_russell1000_tickers():
    """
    Loads Russell 1000 tickers from a local CSV file.
    """
    if not os.path.exists(HOLDINGS_FILE_PATH):
        print(f"Error: The file '{HOLDINGS_FILE_PATH}' was not found.")
        return []
    try:
        # Skip the first 9 rows of metadata, row 10 is header
        df = pd.read_csv(HOLDINGS_FILE_PATH, skiprows=9)

        if 'Ticker' not in df.columns:
            print("Error: 'Ticker' column not found. Please check your CSV file.")
            return []
        
        tickers = df["Ticker"].dropna().tolist()
        print(f"Retrieved {len(tickers)} Russell 1000 tickers from local file.")
        return tickers
    except Exception as e:
        print(f"Error processing the CSV file: {e}")
        return []

# ------------------------
# COMPUTE INDICATORS AND SIGNALS
# ------------------------
def compute_signals(df):
    signals = []

    try:
        close = df["Close"].squeeze()  # ensure 1D
        date = df.index[-1].date()
        
        # --- RSI ---
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        roll_up = gain.rolling(RSI_PERIOD).mean()
        roll_down = loss.rolling(RSI_PERIOD).mean()
        # Handle division by zero for RSI calculation
        rs = np.divide(roll_up, roll_down, out=np.zeros_like(roll_up), where=roll_down != 0)
        rsi = 100 - (100 / (1 + rs))
        last_rsi = rsi.iloc[-1]
        if last_rsi < 30:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "RSI", "Value": round(last_rsi,1), "Signal": "Buy", "Date": date})
        elif last_rsi > 70:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "RSI", "Value": round(last_rsi,1), "Signal": "Sell", "Date": date})
        
        # --- SMA Crossovers ---
        sma_short = close.rolling(SMA_SHORT).mean()
        sma_long = close.rolling(SMA_LONG).mean()
        sma_long2 = close.rolling(SMA_LONG2).mean()
        # Golden Cross
        if sma_short.iloc[-2] < sma_long.iloc[-2] and sma_short.iloc[-1] > sma_long.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "SMA_Cross", "Value": f"{SMA_SHORT}>{SMA_LONG}", "Signal": "Buy", "Date": date})
        # Death Cross
        elif sma_short.iloc[-2] > sma_long.iloc[-2] and sma_short.iloc[-1] < sma_long.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "SMA_Cross", "Value": f"{SMA_SHORT}<{SMA_LONG}", "Signal": "Sell", "Date": date})
        
        # --- MACD ---
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-2] < signal_line.iloc[-2] and macd.iloc[-1] > signal_line.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "MACD", "Value": round(macd.iloc[-1],2), "Signal": "Buy", "Date": date})
        elif macd.iloc[-2] > signal_line.iloc[-2] and macd.iloc[-1] < signal_line.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "MACD", "Value": round(macd.iloc[-1],2), "Signal": "Sell", "Date": date})

        # --- Bollinger Bands ---
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper = sma20 + 2 * std20
        lower = sma20 - 2 * std20
        if close.iloc[-1] < lower.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "Bollinger", "Value": round(lower.iloc[-1],2), "Signal": "Buy", "Date": date})
        elif close.iloc[-1] > upper.iloc[-1]:
            signals.append({"Ticker": df.name, "Close": close.iloc[-1], "Indicator": "Bollinger", "Value": round(upper.iloc[-1],2), "Signal": "Sell", "Date": date})
        
    except Exception as e:
        print(f"Error computing signals for {df.name}: {e}")

    return signals

# ------------------------
# MAIN SCANNER
# ------------------------
def run_scanner():
    tickers = get_russell1000_tickers()
    if not tickers:
        return
    
    all_signals = []

    print(f"\n--- Scanning {len(tickers)} tickers ---")
    for ticker in tqdm(tickers):
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=False)
            if df.empty:
                continue
            df.name = ticker  # pass ticker into signals
            signals = compute_signals(df)
            all_signals.extend(signals)
        except Exception as e:
            print(f"Error downloading {ticker}: {e}")
            continue

    if not all_signals:
        print("No signals detected.")
        return

    # ------------------------
    # SAVE TO EXCEL
    # ------------------------
    signals_df = pd.DataFrame(all_signals)
    writer = pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter")
    
    # Save one sheet per indicator
    for indicator in signals_df["Indicator"].unique():
        df_ind = signals_df[signals_df["Indicator"] == indicator]
        df_ind.to_excel(writer, sheet_name=indicator, index=False)
    
    # --- NEW: Multi-Signals page ---
    multi_df = (signals_df.groupby("Ticker")
                           .filter(lambda x: len(x) > 1)   # keep tickers with >1 signal
                           .sort_values(by=["Ticker", "Date"]))
    
    if not multi_df.empty:
        multi_df.to_excel(writer, sheet_name="Multi_Signals", index=False)

    writer.close()
    print(f"\n✅ Signals saved to {OUTPUT_FILE}")

# ------------------------
# EXECUTE
# ------------------------
if __name__ == "__main__":
    run_scanner()