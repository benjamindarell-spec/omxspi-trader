"""
Monday morning portfolio email via Gmail SMTP.
Uses an App Password — see setup instructions in the Strategy Guide.
"""
import smtplib
import os
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import CLAUDE_MODEL
from data.fetcher import fetch_all_stocks
from data.screener import screen_universe
from signals.technical import compute_indicators
from signals.scorer import score_stock
from portfolio.manager import suggest_portfolio, build_scan_result
from portfolio.tracker import performance_summary
import anthropic


def _claude_email_briefing(portfolio: list[dict], capital: float, perf: dict) -> str:
    """Ask Claude to write the full email body as HTML."""
    holdings_text = "\n".join(
        f"- {p['ticker']} ({p['sector']}): {p['signal']} score {p['score']}/5 — "
        f"buy {p['shares']} shares @ {p['price']:.2f} SEK — "
        f"SL {p['stop_loss']} / TP {p['take_profit']} — "
        f"reasons: {'; '.join(p.get('reasons', []))}"
        for p in portfolio
    )

    prompt = f"""You are a Swedish stock trading assistant writing a Monday morning email briefing.

PORTFOLIO PERFORMANCE SO FAR:
- Starting capital: {capital:,.0f} SEK
- Current value: {perf['portfolio_value']:,.0f} SEK
- Total return: {perf['total_return_pct']:+.1f}%
- Win rate: {perf['win_rate_pct']:.0f}%
- Closed trades: {perf['closed_trades']}

THIS WEEK'S SUGGESTED PORTFOLIO (5 stocks):
{holdings_text}

Write a concise Monday morning email briefing. Structure it exactly like this:

<h2>Good morning — here is your OMXSPI weekly briefing for {datetime.now().strftime('%d %B %Y')}</h2>

<h3>Portfolio performance</h3>
[2 sentences on how the portfolio is tracking toward the 20,000 SEK target]

<h3>This week's 5 stock picks</h3>
[For EACH stock, one short paragraph: what to buy, why, the exact entry, stop-loss, and take-profit]

<h3>Key risk this week</h3>
[1–2 sentences on the biggest macro or sector risk to watch]

<h3>Action checklist for Nordnet</h3>
<ul>
[Bullet list of exact actions: buy X shares of Y at market open, set SL at Z, set TP at W]
</ul>

Use plain HTML only. No markdown. Keep it tight and actionable."""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _build_html_email(body: str, portfolio: list[dict], capital: float) -> str:
    table_rows = "".join(
        f"""<tr>
            <td><b>{p['ticker'].replace('.ST','')}</b></td>
            <td>{p['sector']}</td>
            <td>{p['signal']}</td>
            <td>{p['score']}/5</td>
            <td>{p['price']:.2f}</td>
            <td>{p['stop_loss']:.2f}</td>
            <td>{p['take_profit']:.2f}</td>
            <td>{p['shares']} shares ≈ {p['actual_investment']:,.0f} SEK</td>
        </tr>"""
        for p in portfolio
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 14px; color: #222; max-width: 700px; margin: 0 auto; padding: 20px; }}
  h2 {{ color: #1a7a4a; border-bottom: 2px solid #1a7a4a; padding-bottom: 8px; }}
  h3 {{ color: #333; margin-top: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th {{ background: #1a7a4a; color: white; padding: 8px; text-align: left; font-size: 12px; }}
  td {{ padding: 7px 8px; border-bottom: 1px solid #eee; font-size: 13px; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .footer {{ margin-top: 32px; font-size: 11px; color: #999; border-top: 1px solid #eee; padding-top: 12px; }}
  .disclaimer {{ background: #fff8e1; border-left: 4px solid #f0ad00; padding: 10px 14px; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>

{body}

<h3>Quick reference table</h3>
<table>
  <tr>
    <th>Ticker</th><th>Sector</th><th>Signal</th><th>Score</th>
    <th>Price (SEK)</th><th>Stop-loss</th><th>Take-profit</th><th>Position size</th>
  </tr>
  {table_rows}
</table>

<div class="disclaimer">
  <b>Disclaimer:</b> Technical analysis signals only. Not financial advice.
  Always set stop-losses in Nordnet before stepping away from a position.
  Never invest money you cannot afford to lose.
</div>

<div class="footer">
  OMXSPI Swing Trading Model · Generated {datetime.now().strftime('%Y-%m-%d %H:%M CET')} ·
  Target: {capital:,.0f} SEK → {capital*2:,.0f} SEK in 6 months
</div>

</body>
</html>"""


def send_weekly_email(capital: float = 10_000, n_positions: int = 5) -> str:
    """
    Run a full scan, build portfolio, generate Claude briefing, send email.
    Returns a status string ('OK' or error message).
    """
    try:
        raw = fetch_all_stocks()
        stock_data = screen_universe(raw)
        results = []
        for ticker, df in stock_data.items():
            try:
                ind = compute_indicators(df)
                scored = score_stock(ind)
                results.append(build_scan_result(ticker, ind, scored))
            except Exception:
                pass

        portfolio = suggest_portfolio(results, capital, n_positions)
        if not portfolio:
            return "No BUY signals found — email not sent."

        perf = performance_summary(capital)
        body = _claude_email_briefing(portfolio, capital, perf)
        html = _build_html_email(body, portfolio, capital)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"OMXSPI Weekly Picks — {datetime.now().strftime('%d %b %Y')}"
        msg.attach(MIMEText(html, "html"))

        sender = os.environ.get("EMAIL_SENDER", "")
        password = os.environ.get("EMAIL_PASSWORD", "")
        recipient = os.environ.get("EMAIL_RECIPIENT", "benjamin.darell@gmail.com")

        if not sender or not password:
            return "EMAIL_SENDER or EMAIL_PASSWORD not set."

        msg["From"] = sender
        msg["To"] = recipient

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())

        return "OK"

    except Exception as e:
        return str(e)
