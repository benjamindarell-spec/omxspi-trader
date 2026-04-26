import yfinance as yf
import pandas as pd
from config import OMXSPI_UNIVERSE, MIN_DAILY_VOLUME_SEK


def fetch_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame | None:
    """Fetch OHLCV data for a single .ST ticker. Returns None if insufficient data or volume."""
    try:
        df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False)
        if df is None or len(df) < 55:
            return None
        # Flatten MultiIndex columns that yfinance sometimes returns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        avg_vol = df["Volume"].tail(20).mean()
        last_price = float(df["Close"].iloc[-1])
        avg_vol_sek = avg_vol * last_price
        if avg_vol_sek < MIN_DAILY_VOLUME_SEK:
            return None
        return df
    except Exception:
        return None


def fetch_all_stocks(universe: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for every ticker in the universe. Returns {ticker: DataFrame}."""
    tickers = universe or OMXSPI_UNIVERSE
    results: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        df = fetch_stock_data(ticker)
        if df is not None:
            results[ticker] = df
    return results


def fetch_single(ticker: str) -> pd.DataFrame | None:
    """Convenience wrapper for a single ticker refresh."""
    return fetch_stock_data(ticker)
