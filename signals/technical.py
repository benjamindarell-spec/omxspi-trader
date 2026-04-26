import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands


def _squeeze(series: pd.Series) -> pd.Series:
    """Flatten a Series that may have a MultiIndex or extra levels."""
    if isinstance(series.index, pd.MultiIndex):
        series = series.droplevel(list(range(1, series.index.nlevels)))
    return series


def compute_indicators(df: pd.DataFrame) -> dict:
    """
    Compute all technical indicators from OHLCV data.
    Returns a flat dict of scalar values ready for scoring.
    """
    close = _squeeze(df["Close"].dropna())
    volume = _squeeze(df["Volume"].dropna())

    # --- RSI ---
    rsi = float(RSIIndicator(close, window=14).rsi().iloc[-1])

    # --- EMA crossover ---
    ema20_series = EMAIndicator(close, window=20).ema_indicator()
    ema50_series = EMAIndicator(close, window=50).ema_indicator()
    ema20 = float(ema20_series.iloc[-1])
    ema50 = float(ema50_series.iloc[-1])
    # Look back 4 bars to detect recent cross
    ema20_prev = float(ema20_series.iloc[-4])
    ema50_prev = float(ema50_series.iloc[-4])
    ema_cross_up = (ema20_prev < ema50_prev) and (ema20 > ema50)
    ema_cross_down = (ema20_prev > ema50_prev) and (ema20 < ema50)

    # --- MACD ---
    macd_obj = MACD(close)
    macd_line = float(macd_obj.macd().iloc[-1])
    signal_line = float(macd_obj.macd_signal().iloc[-1])
    prev_macd = float(macd_obj.macd().iloc[-4])
    prev_signal = float(macd_obj.macd_signal().iloc[-4])
    bullish_crossover = (prev_macd < prev_signal) and (macd_line > signal_line)
    bearish_crossover = (prev_macd > prev_signal) and (macd_line < signal_line)

    # --- Bollinger Bands ---
    bb = BollingerBands(close, window=20, window_dev=2)
    bb_upper = float(bb.bollinger_hband().iloc[-1])
    bb_lower = float(bb.bollinger_lband().iloc[-1])
    bb_range = bb_upper - bb_lower
    bb_pct = (float(close.iloc[-1]) - bb_lower) / bb_range if bb_range > 0 else 0.5

    # --- Volume ratio ---
    vol_series = volume.reindex(close.index).fillna(0)
    avg_volume = float(vol_series.tail(20).mean())
    cur_volume = float(vol_series.iloc[-1])
    volume_ratio = (cur_volume / avg_volume) if avg_volume > 0 else 1.0

    # --- 1-month momentum ---
    momentum_1m = 0.0
    if len(close) >= 22:
        momentum_1m = (float(close.iloc[-1]) - float(close.iloc[-22])) / float(close.iloc[-22])

    price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2])

    return {
        "rsi": round(rsi, 1),
        "ema20": round(ema20, 4),
        "ema50": round(ema50, 4),
        "ema_bullish": ema20 > ema50,
        "ema_cross_up": ema_cross_up,
        "ema_cross_down": ema_cross_down,
        "macd_line": round(macd_line, 4),
        "signal_line": round(signal_line, 4),
        "macd_bullish": macd_line > signal_line,
        "bullish_crossover": bool(bullish_crossover),
        "bearish_crossover": bool(bearish_crossover),
        "bb_pct": round(bb_pct, 3),
        "bb_upper": round(bb_upper, 2),
        "bb_lower": round(bb_lower, 2),
        "volume_ratio": round(volume_ratio, 2),
        "momentum_1m": round(momentum_1m * 100, 1),
        "price": round(price, 2),
        "prev_close": round(prev_close, 2),
        "change_pct": round((price - prev_close) / prev_close * 100, 2),
    }
