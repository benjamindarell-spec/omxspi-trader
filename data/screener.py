"""Pre-scan filtering before full technical analysis."""
import pandas as pd
from config import MIN_DAILY_VOLUME_SEK


def passes_liquidity_filter(df: pd.DataFrame) -> bool:
    """True if average 20-day volume * price exceeds minimum threshold."""
    if df is None or len(df) < 20:
        return False
    avg_vol = df["Volume"].tail(20).mean()
    last_price = float(df["Close"].iloc[-1])
    return (avg_vol * last_price) >= MIN_DAILY_VOLUME_SEK


def passes_data_quality(df: pd.DataFrame) -> bool:
    """True if DataFrame has enough rows and no excessive NaN gaps."""
    if df is None or len(df) < 55:
        return False
    close = df["Close"].dropna()
    return len(close) >= 50


def screen_universe(stock_data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Apply all pre-filters to the fetched universe.
    Returns only the tickers that pass.
    """
    passed: dict[str, pd.DataFrame] = {}
    for ticker, df in stock_data.items():
        if passes_data_quality(df) and passes_liquidity_filter(df):
            passed[ticker] = df
    return passed
