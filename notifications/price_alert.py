"""
Checks all open positions against current prices.
Sends an email alert if stop-loss or take-profit is hit.
Only runs during Nasdaq Stockholm market hours: Mon–Fri 09:00–17:30 CET.
"""
import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yfinance as yf

from portfolio.tracker import get_open_positions
from config import CLAUDE_MODEL

CET = timezone(timedelta(hours=1))   # UTC+1 (winter); close enough year-round for hour checks
MARKET_OPEN = 9
MARKET_CLOSE = 17


def _is_market_hours() -> bool:
    now = datetime.now(CET)
    if now.weekday() >= 5:      # Saturday / Sunday
        return False
    return MARKET_OPEN <= now.hour < MARKET_CLOSE


def _fetch_price(ticker: str) -> float | None:
    try:
        df = yf.download(ticker, period="1d", interval="5m", auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        if hasattr(df.columns, "get_level_values"):
            df.columns = df.columns.get_level_values(0)
        return float(df["Close"].iloc[-1])
    except Exception:
        return None


def _send_alert_email(alerts: list[dict]) -> str:
    sender    = os.environ.get("EMAIL_SENDER", "")
    password  = os.environ.get("EMAIL_PASSWORD", "")
    recipient = os.environ.get("EMAIL_RECIPIENT", "")
    if not sender or not password or not recipient:
        return "Email credentials not set."

    rows = "".join(
        f"""<tr>
            <td><b>{a['ticker'].replace('.ST','')}</b></td>
            <td style="color:{'#ef4444' if a['type']=='STOP-LOSS' else '#22c55e'}">{a['type']}</td>
            <td>{a['entry']:.2f}</td>
            <td>{a['current']:.2f}</td>
            <td>{a['level']:.2f}</td>
            <td style="color:{'#ef4444' if a['pnl_pct']<0 else '#22c55e'}">{a['pnl_pct']:+.1f}%</td>
        </tr>"""
        for a in alerts
    )

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size:14px; color:#222; max-width:680px; margin:0 auto; padding:20px; }}
  h2 {{ color:#1d4ed8; border-bottom:2px solid #1d4ed8; padding-bottom:8px; }}
  table {{ border-collapse:collapse; width:100%; margin:16px 0; }}
  th {{ background:#1d4ed8; color:white; padding:8px; text-align:left; font-size:12px; }}
  td {{ padding:8px; border-bottom:1px solid #eee; font-size:13px; }}
  .footer {{ margin-top:24px; font-size:11px; color:#999; border-top:1px solid #eee; padding-top:12px; }}
</style></head><body>
<h2>⚠️ Price Alert — Action Required</h2>
<p>The following positions have hit a trigger level. Please log in to <b>Nordnet</b> and take action immediately.</p>
<table>
  <tr><th>Stock</th><th>Alert</th><th>Entry (SEK)</th><th>Current (SEK)</th><th>Trigger (SEK)</th><th>P&L</th></tr>
  {rows}
</table>
<h3>Recommended actions</h3>
<ul>
{''.join(f"<li><b>{a['ticker'].replace('.ST','')}</b> — {a['action']}</li>" for a in alerts)}
</ul>
<div class="footer">OMXSPI Trading Model · {datetime.now().strftime('%Y-%m-%d %H:%M CET')} · Not financial advice</div>
</body></html>"""

    subject = f"⚠️ Price Alert — {', '.join(a['ticker'].replace('.ST','') for a in alerts)}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(sender, password)
            srv.sendmail(sender, recipient, msg.as_string())
        return "OK"
    except Exception as e:
        return str(e)


# Track which positions have already triggered an alert this session
# so we don't spam the same alert every 15 minutes
_alerted: set[str] = set()


def check_and_alert() -> list[dict]:
    """
    Fetch current prices for all open positions.
    Send an email if stop-loss or take-profit is hit (once per position per session).
    Returns list of triggered alerts.
    """
    if not _is_market_hours():
        return []

    positions = get_open_positions()
    if not positions:
        return []

    triggered = []
    for pos in positions:
        alert_key = f"{pos['id']}"
        if alert_key in _alerted:
            continue

        current = _fetch_price(pos["ticker"])
        if current is None:
            continue

        pnl_pct = (current - pos["entry_price"]) / pos["entry_price"] * 100
        alert = None

        if current <= pos["stop_loss"]:
            alert = {
                "ticker":  pos["ticker"],
                "type":    "STOP-LOSS",
                "entry":   pos["entry_price"],
                "current": current,
                "level":   pos["stop_loss"],
                "pnl_pct": pnl_pct,
                "action":  f"Sell all {pos['shares']} shares immediately. "
                           f"Loss: {pnl_pct:.1f}%",
            }
        elif current >= pos["take_profit"]:
            alert = {
                "ticker":  pos["ticker"],
                "type":    "TAKE-PROFIT",
                "entry":   pos["entry_price"],
                "current": current,
                "level":   pos["take_profit"],
                "pnl_pct": pnl_pct,
                "action":  f"Consider selling {pos['shares']} shares. "
                           f"Gain: +{pnl_pct:.1f}%. "
                           f"If momentum is strong, trail stop to +10%.",
            }

        if alert:
            triggered.append(alert)
            _alerted.add(alert_key)

    if triggered:
        _send_alert_email(triggered)

    return triggered
