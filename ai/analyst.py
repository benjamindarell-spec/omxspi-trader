import json
import anthropic
from config import CLAUDE_MODEL

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def get_ai_analysis(
    ticker: str,
    indicators: dict,
    score_result: dict,
    portfolio_context: dict,
) -> str:
    """
    Ask Claude to synthesize technical signals into a plain-language trade rationale.
    Returns a markdown-formatted analysis string.
    """
    prompt = f"""You are a Swedish stock market analyst specializing in OMXSPI swing trading.

PORTFOLIO CONTEXT:
- Total capital: {portfolio_context['capital']:,.0f} SEK
- Current open positions: {portfolio_context.get('positions', [])}
- Target: Double to {portfolio_context['capital'] * 2:,.0f} SEK within 6 months
- Trading horizon: 1–4 weeks per position

STOCK BEING ANALYZED: {ticker}

TECHNICAL INDICATORS:
{json.dumps(indicators, indent=2)}

SIGNAL SCORE: {score_result['score']} / 5.0
RECOMMENDATION: {score_result['signal']}
KEY REASONS: {', '.join(score_result.get('reasons', []))}

ENTRY LEVELS:
- Entry: {indicators['price']:.2f} SEK
- Stop-loss: {score_result['stop_loss']:.2f} SEK (-7%)
- Take-profit: {score_result['take_profit']:.2f} SEK (+15%)

Provide a concise trade analysis in exactly this format:

**VERDICT:** [1-sentence buy/sell/avoid recommendation]

**WHY:** [2–3 sentences explaining the technical case in plain language]

**RISK:** [1–2 sentences on the main risk to this trade]

**NORDNET ACTION:** [Exact steps — e.g. "Place a buy order at market open for 2,000 SEK worth of {ticker.replace('.ST','')}. Set stop-loss at {score_result['stop_loss']:.2f} SEK and take-profit at {score_result['take_profit']:.2f} SEK."]

Keep it practical and actionable. No fluff."""

    response = _get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=450,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def get_portfolio_summary(portfolio: list[dict], capital: float) -> str:
    """Ask Claude for a morning briefing on the suggested portfolio."""
    holdings = "\n".join(
        f"- {p['ticker']}: {p['signal']} (score {p['score']}/5) — "
        f"{p['shares']} shares @ {p['price']:.2f} SEK — "
        f"SL {p['stop_loss']} / TP {p['take_profit']}"
        for p in portfolio
    )
    prompt = f"""You are a Swedish stock trading coach.

A swing trader with {capital:,.0f} SEK has just run their weekly OMXSPI signal scan.
Today is their rebalancing day. Here is the suggested portfolio:

{holdings}

Write a brief (4–6 sentence) Monday morning briefing:
1. Quick market context for the Swedish market this week
2. What the portfolio looks like collectively (sectors, risk profile)
3. The single highest-conviction trade and why
4. One thing to watch out for

Be direct, specific, and practical. No disclaimers needed — the user knows this is technical analysis only."""

    response = _get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
