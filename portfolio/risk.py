from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT, MOONSHOT_PCT, TRAIL_STOP_PCT


def position_status(entry_price: float, current_price: float) -> dict:
    """
    Evaluate a live position against stop-loss, take-profit, and moonshot targets.
    Returns a dict with current P&L and an ACTION recommendation.
    """
    pnl_pct = (current_price - entry_price) / entry_price

    stop_loss = round(entry_price * (1 - STOP_LOSS_PCT), 2)
    take_profit = round(entry_price * (1 + TAKE_PROFIT_PCT), 2)
    moonshot = round(entry_price * (1 + MOONSHOT_PCT), 2)
    trail_stop = round(entry_price * (1 + TRAIL_STOP_PCT), 2)

    if current_price <= stop_loss:
        action = "STOP LOSS — EXIT NOW"
    elif current_price >= moonshot:
        action = f"MOONSHOT HIT (+{MOONSHOT_PCT*100:.0f}%) — trail stop to {trail_stop:.2f}"
    elif current_price >= take_profit:
        action = f"TAKE PROFIT HIT (+{TAKE_PROFIT_PCT*100:.0f}%) — consider partial exit"
    elif pnl_pct > 0:
        action = "HOLD — in profit"
    else:
        action = "HOLD — below entry, monitor"

    return {
        "entry": entry_price,
        "current": current_price,
        "pnl_pct": round(pnl_pct * 100, 2),
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "moonshot": moonshot,
        "trail_stop": trail_stop,
        "action": action,
    }


def max_position_size(capital: float, n_positions: int) -> float:
    """Equal-weight position size in SEK."""
    return round(capital / n_positions, 2)


def shares_to_buy(position_sek: float, price: float) -> int:
    """Integer shares that fit within position size."""
    return max(1, int(position_sek / price))
