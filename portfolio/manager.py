from config import SECTORS, MAX_SECTOR_POSITIONS, PORTFOLIO_CAPITAL, MAX_POSITIONS


def suggest_portfolio(
    all_scores: list[dict],
    capital: float = PORTFOLIO_CAPITAL,
    n_positions: int = MAX_POSITIONS,
) -> list[dict]:
    """
    Select up to n_positions stocks with sector diversification.
    Ranks BUY/STRONG BUY candidates by score, caps each sector at MAX_SECTOR_POSITIONS.
    Returns enriched position dicts including sizing in SEK and shares.
    """
    buy_candidates = [
        s for s in all_scores if s.get("signal") in ("STRONG BUY", "BUY")
    ]
    buy_candidates.sort(key=lambda x: x["score"], reverse=True)

    selected: list[dict] = []
    sector_counts: dict[str, int] = {}

    for candidate in buy_candidates:
        if len(selected) >= n_positions:
            break
        ticker = candidate["ticker"]
        sector = SECTORS.get(ticker, "Other")
        if sector_counts.get(sector, 0) >= MAX_SECTOR_POSITIONS:
            continue
        position_sek = round(capital / n_positions, 0)
        shares = max(1, int(position_sek / candidate["price"]))
        candidate = {
            **candidate,
            "sector": sector,
            "position_size_sek": position_sek,
            "shares": shares,
            "actual_investment": round(shares * candidate["price"], 2),
        }
        selected.append(candidate)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    return selected


def build_scan_result(
    ticker: str,
    indicators: dict,
    scored: dict,
) -> dict:
    """Flatten indicators + scored into one dict for the results table."""
    return {
        "ticker": ticker,
        **indicators,
        **scored,
    }
