from config import (
    STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    STRONG_BUY_THRESHOLD, BUY_THRESHOLD,
    SELL_THRESHOLD, STRONG_SELL_THRESHOLD,
)


def score_stock(indicators: dict) -> dict:
    """
    Multi-factor score from -5 to +5.
    Returns signal label, numeric score, entry levels, and human-readable reasons.
    """
    score = 0.0
    reasons: list[str] = []

    # --- RSI (weight 2.0) ---
    rsi = indicators["rsi"]
    if rsi < 25:
        score += 2.0
        reasons.append(f"RSI extremely oversold ({rsi})")
    elif rsi < 50:
        score += 1.0
        reasons.append(f"RSI neutral-low ({rsi})")
    elif rsi > 70:
        score -= 2.0
        reasons.append(f"RSI overbought ({rsi})")
    elif rsi > 60:
        score -= 1.0
        reasons.append(f"RSI elevated ({rsi})")

    # --- EMA crossover (weight 1.5) ---
    if indicators["ema_bullish"]:
        score += 1.5
        reasons.append("EMA20 > EMA50 (uptrend)")
    else:
        score -= 1.5
        reasons.append("EMA20 < EMA50 (downtrend)")

    # Bonus for a recent cross
    if indicators.get("ema_cross_up"):
        score += 0.5
        reasons.append("Fresh EMA bullish crossover")
    elif indicators.get("ema_cross_down"):
        score -= 0.5
        reasons.append("Fresh EMA bearish crossover")

    # --- MACD direction (weight 1.0) ---
    if indicators["macd_bullish"]:
        score += 1.0
        reasons.append("MACD above signal line")
    else:
        score -= 1.0
        reasons.append("MACD below signal line")

    # --- MACD crossover event (weight 1.0) ---
    if indicators["bullish_crossover"]:
        score += 1.0
        reasons.append("MACD bullish crossover (last 3 days)")
    elif indicators["bearish_crossover"]:
        score -= 1.0
        reasons.append("MACD bearish crossover (last 3 days)")

    # --- Volume confirmation (weight 0.5) ---
    vr = indicators["volume_ratio"]
    if vr > 1.2:
        score += 0.5
        reasons.append(f"High volume ({vr:.1f}x 20-day avg)")
    elif vr < 0.8:
        score -= 0.5
        reasons.append(f"Low volume ({vr:.1f}x avg — weak conviction)")

    # --- Bollinger Band position (weight 0.5) ---
    bb_pct = indicators["bb_pct"]
    if bb_pct < 0.20:
        score += 0.5
        reasons.append(f"Near Bollinger lower band ({bb_pct:.0%})")
    elif bb_pct > 0.80:
        score -= 0.5
        reasons.append(f"Near Bollinger upper band ({bb_pct:.0%})")

    # --- 1-month momentum (weight 0.5) ---
    mom = indicators["momentum_1m"]
    if mom > 3:
        score += 0.5
        reasons.append(f"Strong 1-month momentum (+{mom}%)")
    elif mom < -3:
        score -= 0.5
        reasons.append(f"Weak 1-month momentum ({mom}%)")

    score = round(max(-5.0, min(5.0, score)), 2)

    if score >= STRONG_BUY_THRESHOLD:
        signal = "STRONG BUY"
    elif score >= BUY_THRESHOLD:
        signal = "BUY"
    elif score <= STRONG_SELL_THRESHOLD:
        signal = "STRONG SELL"
    elif score <= SELL_THRESHOLD:
        signal = "SELL"
    else:
        signal = "HOLD"

    price = indicators["price"]
    stop_loss = round(price * (1 - STOP_LOSS_PCT), 2)
    take_profit = round(price * (1 + TAKE_PROFIT_PCT), 2)

    return {
        "signal": signal,
        "score": score,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "reasons": reasons,
    }
