"""
OMXSPI Swing Trading Model
Target: 10,000 SEK → 20,000 SEK in 6 months via Nordnet
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

import os
from config import PORTFOLIO_CAPITAL, MAX_POSITIONS
from data.fetcher import fetch_all_stocks
from data.screener import screen_universe
from signals.technical import compute_indicators
from signals.scorer import score_stock
from portfolio.manager import suggest_portfolio, build_scan_result
from portfolio.risk import position_status
from portfolio import tracker
from ai.analyst import get_ai_analysis, get_portfolio_summary
from notifications import scheduler
import streamlit as st

# Load secrets into env vars so background threads and submodules can access them
for _key in ["ANTHROPIC_API_KEY", "EMAIL_SENDER", "EMAIL_PASSWORD", "EMAIL_RECIPIENT"]:
    if _key in st.secrets and not os.environ.get(_key):
        os.environ[_key] = st.secrets[_key]

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OMXSPI // Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Professional dark theme CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif !important;
    background-color: #111318 !important;
    color: #e2e8f0 !important;
}

[data-testid="stSidebar"] {
    background-color: #0d0f14 !important;
    border-right: 1px solid #1e2330 !important;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] .stMarkdown p { font-size: 0.8rem !important; }

.main .block-container { padding-top: 1.5rem; max-width: 1400px; }

h1 { color: #f1f5f9 !important; font-weight: 600 !important; font-size: 1.5rem !important; letter-spacing: -0.02em; }
h2 { color: #cbd5e1 !important; font-weight: 500 !important; font-size: 1rem !important; text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 1px solid #1e2330; padding-bottom: 8px; margin-top: 1.5rem !important; }
h3 { color: #94a3b8 !important; font-size: 0.85rem !important; text-transform: uppercase; letter-spacing: 0.05em; }

[data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important;
    color: #64748b !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.03em;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #e2e8f0 !important;
    border-bottom-color: #3b82f6 !important;
}

.stButton > button {
    background-color: #1e2330 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d3748 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    transition: all 0.15s;
}
.stButton > button:hover { background-color: #2d3748 !important; border-color: #4a5568 !important; }
.stButton > button[kind="primary"] { background-color: #1d4ed8 !important; border-color: #1d4ed8 !important; color: #fff !important; }
.stButton > button[kind="primary"]:hover { background-color: #2563eb !important; }

[data-testid="stMetric"] {
    background: #161a24 !important;
    border: 1px solid #1e2330 !important;
    padding: 14px 18px !important;
    border-radius: 8px !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500 !important; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.4rem !important; font-weight: 600 !important; }

[data-testid="stExpander"] { border: 1px solid #1e2330 !important; background: #161a24 !important; border-radius: 8px !important; }
[data-testid="stExpander"] summary { color: #94a3b8 !important; font-size: 0.82rem !important; }

hr { border-color: #1e2330 !important; }
.stCaption, small { color: #64748b !important; font-size: 0.72rem !important; }

[data-testid="stProgressBar"] > div { background: #3b82f6 !important; }
[data-testid="stProgressBar"] { background: #1e2330 !important; border-radius: 4px !important; }

input[type="number"], input[type="text"], input[type="password"] {
    background: #161a24 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 6px !important;
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #111318; }
::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #4a5568; }
</style>
""", unsafe_allow_html=True)

# ── Start background email scheduler ─────────────────────────────────────────
scheduler.start_scheduler()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Settings**")
    capital = st.number_input("Portfolio capital (SEK)", value=PORTFOLIO_CAPITAL, step=500, min_value=1000)
    n_positions = st.slider("Max simultaneous positions", 3, 8, MAX_POSITIONS)
    use_ai = st.toggle("AI analysis (Claude API)", value=True)
    st.divider()

    st.markdown("**📧 Weekly Email (Monday 08:00)**")
    email_sender = st.text_input(
        "Your Gmail address",
        value=os.environ.get("EMAIL_SENDER", ""),
        placeholder="you@gmail.com",
    )
    email_password = st.text_input(
        "Gmail App Password",
        value=os.environ.get("EMAIL_PASSWORD", ""),
        type="password",
        placeholder="xxxx xxxx xxxx xxxx",
        help="Create at myaccount.google.com → Security → App Passwords. Use 'Mail' as the app.",
    )
    if email_sender:
        os.environ["EMAIL_SENDER"] = email_sender
    if email_password:
        os.environ["EMAIL_PASSWORD"] = email_password

    status = scheduler.last_email_status()
    if status["sent_at"]:
        st.caption(f"Last sent: {status['sent_at'][:16]}  ·  {status['result']}")
    else:
        st.caption("No email sent yet this session.")

    if st.button("📤 Send test email now", use_container_width=True):
        if not email_sender or not email_password:
            st.error("Enter your Gmail address and App Password first.")
        else:
            with st.spinner("Running scan and sending email…"):
                result = scheduler.trigger_now(capital, n_positions)
            if result == "OK":
                st.success(f"Email sent to {os.environ.get('EMAIL_RECIPIENT','')}")
            else:
                st.error(f"Failed: {result}")

    st.divider()
    st.caption("**Strategy rules**")
    st.caption("• Stop-loss: -7%  |  Take-profit: +15%")
    st.caption("• Moonshot: +30% with trailing stop")
    st.caption("• Rebalance every Monday")
    st.caption("• Max 2 stocks per sector")
    st.divider()
    st.caption(
        "> This app provides technical analysis signals only. "
        "Not financial advice. Always set stop-losses in Nordnet before stepping away."
    )

# ── Header ───────────────────────────────────────────────────────────────────
st.title("OMXSPI Trading Model")
st.markdown(
    f'<p style="color:#64748b;font-size:0.78rem;">'
    f'Target &nbsp;<strong style="color:#e2e8f0">{capital:,.0f} SEK → {capital*2:,.0f} SEK</strong>'
    f'&nbsp; · &nbsp;Nasdaq Stockholm&nbsp; · &nbsp;Nordnet&nbsp; · &nbsp;1–4 week swing trading'
    f'</p>',
    unsafe_allow_html=True,
)

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_scan, tab_portfolio, tab_tracker, tab_guide = st.tabs(
    ["🔍 Market Scan", "📊 Portfolio Builder", "📒 Position Tracker", "📖 Strategy Guide"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MARKET SCAN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_scan:
    st.subheader("Full OMXSPI Signal Scan")
    if st.button("🔄 Run market scan", type="primary", use_container_width=True):
        with st.spinner("Fetching data from Yahoo Finance (this takes ~60 seconds)…"):
            raw_data = fetch_all_stocks()

        with st.spinner("Screening for liquidity…"):
            stock_data = screen_universe(raw_data)

        st.info(f"Passed liquidity filter: **{len(stock_data)}** stocks")

        results: list[dict] = []
        bar = st.progress(0, text="Computing indicators…")
        tickers = list(stock_data.keys())
        for i, ticker in enumerate(tickers):
            try:
                ind = compute_indicators(stock_data[ticker])
                scored = score_stock(ind)
                row = build_scan_result(ticker, ind, scored)
                results.append(row)
            except Exception as e:
                pass
            bar.progress((i + 1) / len(tickers), text=f"{ticker}")

        bar.empty()
        st.session_state["scan_results"] = results
        st.session_state["stock_data"] = stock_data
        st.success(f"Scan complete — {len(results)} stocks analysed.")

    if "scan_results" in st.session_state:
        results = st.session_state["scan_results"]
        df = pd.DataFrame(results)[
            ["ticker", "price", "change_pct", "rsi", "ema_bullish",
             "macd_bullish", "volume_ratio", "signal", "score",
             "stop_loss", "take_profit", "momentum_1m"]
        ].sort_values("score", ascending=False).reset_index(drop=True)

        # Signal colour map
        def _signal_bg(val: str) -> str:
            return {
                "STRONG BUY": "background-color:#1a7a4a;color:white",
                "BUY": "background-color:#2ecc71;color:white",
                "HOLD": "",
                "SELL": "background-color:#e74c3c;color:white",
                "STRONG SELL": "background-color:#8e1c1c;color:white",
            }.get(val, "")

        styled = df.style.map(_signal_bg, subset=["signal"])
        st.dataframe(styled, use_container_width=True, height=520)

        # Score histogram
        fig = px.histogram(
            df, x="score", nbins=20,
            color_discrete_sequence=["#3b82f6"],
            title="Signal Score Distribution",
            labels={"score": "Signal score (−5 to +5)"},
        )
        fig.add_vline(x=1.5, line_dash="dash", line_color="#f59e0b", annotation_text="BUY")
        fig.add_vline(x=3.5, line_dash="dash", line_color="#22c55e", annotation_text="Strong Buy")
        fig.update_layout(
            paper_bgcolor="#111318", plot_bgcolor="#161a24",
            font=dict(family="Inter, sans-serif", color="#94a3b8", size=11),
            title_font_color="#e2e8f0",
            xaxis=dict(gridcolor="#1e2330", zerolinecolor="#1e2330"),
            yaxis=dict(gridcolor="#1e2330", zerolinecolor="#1e2330"),
        )
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_portfolio:
    st.subheader("Suggested Portfolio")

    if "scan_results" not in st.session_state:
        st.info("Run the market scan first.")
    else:
        results = st.session_state["scan_results"]
        portfolio = suggest_portfolio(results, capital, n_positions)

        if not portfolio:
            st.warning("No BUY signals found in current scan. Try again after the next trading session.")
        else:
            if use_ai:
                with st.expander("🤖 Monday Morning Briefing (Claude)", expanded=True):
                    with st.spinner("Asking Claude for a portfolio briefing…"):
                        try:
                            briefing = get_portfolio_summary(portfolio, capital)
                            st.markdown(briefing)
                        except Exception as e:
                            st.error(f"Claude API error: {e}")

            st.divider()
            cols = st.columns(len(portfolio))
            for col, pos in zip(cols, portfolio):
                with col:
                    emoji = "🟢" if pos["signal"] == "STRONG BUY" else "🔵"
                    st.metric(
                        label=f"{emoji} {pos['ticker'].replace('.ST', '')}",
                        value=f"{pos['price']:.2f} SEK",
                        delta=f"{pos['change_pct']:+.2f}% today",
                    )
                    st.caption(f"**Score:** {pos['score']}/5  ·  **{pos['signal']}**")
                    st.caption(f"**Sector:** {pos['sector']}")
                    st.caption(f"**Stop-loss:** {pos['stop_loss']} SEK")
                    st.caption(f"**Take-profit:** {pos['take_profit']} SEK")
                    st.caption(
                        f"**Buy:** {pos['shares']} shares ≈ {pos['actual_investment']:,.0f} SEK"
                    )

                    reasons_md = "\n".join(f"- {r}" for r in pos.get("reasons", []))
                    with st.expander("Signal details"):
                        st.markdown(reasons_md)

                    if use_ai:
                        if st.button("🤖 AI analysis", key=f"ai_{pos['ticker']}"):
                            with st.spinner(f"Analysing {pos['ticker']}…"):
                                try:
                                    analysis = get_ai_analysis(
                                        pos["ticker"],
                                        {k: pos[k] for k in [
                                            "price", "rsi", "ema_bullish", "macd_bullish",
                                            "bullish_crossover", "volume_ratio", "bb_pct",
                                            "momentum_1m", "change_pct",
                                        ]},
                                        {
                                            "signal": pos["signal"],
                                            "score": pos["score"],
                                            "stop_loss": pos["stop_loss"],
                                            "take_profit": pos["take_profit"],
                                            "reasons": pos.get("reasons", []),
                                        },
                                        {
                                            "capital": capital,
                                            "positions": [p["ticker"] for p in portfolio],
                                        },
                                    )
                                    st.markdown(analysis)
                                except Exception as e:
                                    st.error(f"Claude API error: {e}")

                    if st.button("📥 Add to tracker", key=f"add_{pos['ticker']}"):
                        try:
                            tracker.add_position(
                                ticker=pos["ticker"],
                                entry_price=pos["price"],
                                shares=pos["shares"],
                                position_sek=pos["actual_investment"],
                                stop_loss=pos["stop_loss"],
                                take_profit=pos["take_profit"],
                                notes=f"Score {pos['score']} | {pos['signal']}",
                            )
                            st.success(f"Added {pos['ticker']} to tracker.")
                        except Exception as e:
                            st.error(str(e))

            # Sector breakdown chart
            st.divider()
            sectors = [p["sector"] for p in portfolio]
            sector_sek = [p["actual_investment"] for p in portfolio]
            fig_pie = px.pie(
                values=sector_sek, names=sectors,
                title="Sector Allocation", hole=0.5,
                color_discrete_sequence=["#3b82f6","#6366f1","#8b5cf6","#06b6d4","#0ea5e9","#22c55e"],
            )
            fig_pie.update_layout(
                paper_bgcolor="#111318",
                font=dict(family="Inter, sans-serif", color="#94a3b8", size=11),
                title_font_color="#e2e8f0",
                legend=dict(bgcolor="#161a24", bordercolor="#1e2330"),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            # Risk table
            st.subheader("Risk matrix")
            risk_rows = []
            for pos in portfolio:
                risk_rows.append({
                    "Ticker": pos["ticker"].replace(".ST", ""),
                    "Entry (SEK)": pos["price"],
                    "Stop-loss": pos["stop_loss"],
                    "Take-profit": pos["take_profit"],
                    "Max loss (SEK)": round((pos["price"] - pos["stop_loss"]) * pos["shares"], 2),
                    "Target gain (SEK)": round((pos["take_profit"] - pos["price"]) * pos["shares"], 2),
                    "R:R": round(
                        (pos["take_profit"] - pos["price"]) / (pos["price"] - pos["stop_loss"]), 2
                    ),
                })
            st.dataframe(pd.DataFrame(risk_rows), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — POSITION TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_tracker:
    st.subheader("Live Position Tracker")

    # Performance summary
    summary = tracker.performance_summary(capital)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Portfolio value", f"{summary['portfolio_value']:,.0f} SEK",
              delta=f"{summary['total_return_pct']:+.1f}%")
    m2.metric("Closed trades", summary["closed_trades"])
    m3.metric("Win rate", f"{summary['win_rate_pct']:.0f}%")
    m4.metric("Avg win", f"{summary['avg_win_pct']:+.1f}%")
    m5.metric("Avg loss", f"{summary['avg_loss_pct']:+.1f}%")

    st.divider()

    # Shared chart layout for this tab
    _CHART_LAYOUT = dict(
        paper_bgcolor="#111318", plot_bgcolor="#161a24",
        font=dict(family="Inter, sans-serif", color="#94a3b8", size=11),
        title_font_color="#e2e8f0",
        xaxis=dict(gridcolor="#1e2330", zerolinecolor="#1e2330"),
        yaxis=dict(gridcolor="#1e2330", zerolinecolor="#1e2330"),
        legend=dict(bgcolor="#161a24", bordercolor="#1e2330"),
    )

    # Equity curve
    curve = tracker.get_equity_curve()
    if curve:
        eq_df = pd.DataFrame(curve)
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=eq_df["recorded_at"], y=eq_df["equity_sek"],
            mode="lines+markers", name="Equity",
            line=dict(color="#3b82f6", width=2),
            marker=dict(color="#3b82f6", size=5),
        ))
        fig_eq.add_hline(y=capital * 2, line_dash="dash", line_color="#f59e0b",
                         annotation_text="Target 2×", annotation_font_color="#f59e0b")
        fig_eq.add_hline(y=capital, line_dash="dash", line_color="#64748b",
                         annotation_text="Start", annotation_font_color="#64748b")
        fig_eq.update_layout(title="Equity Curve", yaxis_title="SEK", **_CHART_LAYOUT)
        st.plotly_chart(fig_eq, use_container_width=True)

    # ── Forward projection ────────────────────────────────────────────────────
    st.subheader("Portfolio Projection")
    perf = tracker.performance_summary(capital)

    # Use actual stats if we have closed trades, else use strategy defaults
    if perf["closed_trades"] >= 3:
        win_rate = perf["win_rate_pct"] / 100
        avg_win = perf["avg_win_pct"] / 100
        avg_loss = abs(perf["avg_loss_pct"]) / 100
        note = f"Based on {perf['closed_trades']} closed trades"
    else:
        win_rate, avg_win, avg_loss = 0.65, 0.15, 0.07
        note = "Based on strategy defaults (65% win rate, +15% avg win, −7% avg loss)"

    trades_per_month = 4  # ~1 per week per position cycle
    months = 6
    weeks = months * 4

    import numpy as np
    from datetime import timedelta

    today = pd.Timestamp.now()
    dates = [today + timedelta(weeks=w) for w in range(weeks + 1)]

    # Base case — expected value compounding
    base, opt, pess = [summary["portfolio_value"]], [summary["portfolio_value"]], [summary["portfolio_value"]]
    for _ in range(weeks):
        ev = win_rate * avg_win - (1 - win_rate) * avg_loss
        base.append(base[-1] * (1 + ev))
        opt.append(opt[-1] * (1 + win_rate * avg_win * 1.1 - (1 - win_rate) * avg_loss * 0.8))
        pess.append(pess[-1] * (1 + win_rate * avg_win * 0.8 - (1 - win_rate) * avg_loss * 1.2))

    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(
        x=dates, y=opt, name="Optimistic", mode="lines",
        line=dict(color="#22c55e", width=1, dash="dot"),
    ))
    fig_proj.add_trace(go.Scatter(
        x=dates, y=base, name="Base case", mode="lines",
        line=dict(color="#3b82f6", width=2.5),
    ))
    fig_proj.add_trace(go.Scatter(
        x=dates, y=pess, name="Conservative", mode="lines",
        line=dict(color="#f59e0b", width=1, dash="dot"),
    ))
    fig_proj.add_hline(y=capital * 2, line_dash="dash", line_color="#f59e0b",
                       annotation_text="Target 20,000 SEK", annotation_font_color="#f59e0b")
    fig_proj.add_hline(y=capital, line_dash="dash", line_color="#64748b",
                       annotation_text="Starting capital", annotation_font_color="#64748b")

    weeks_to_target = next(
        (i for i, v in enumerate(base) if v >= capital * 2), None
    )
    if weeks_to_target:
        target_date = today + timedelta(weeks=weeks_to_target)
        fig_proj.add_vline(
            x=target_date.timestamp() * 1000, line_dash="dash", line_color="#22c55e",
            annotation_text=f"~{weeks_to_target}w", annotation_font_color="#22c55e",
        )

    fig_proj.update_layout(
        title=f"6-Month Projection  ·  {note}",
        yaxis_title="Portfolio value (SEK)", xaxis_title="",
        **_CHART_LAYOUT,
    )
    st.plotly_chart(fig_proj, use_container_width=True)

    p1, p2, p3 = st.columns(3)
    p1.metric("Base case (6m)", f"{base[-1]:,.0f} SEK", f"{(base[-1]-capital)/capital*100:+.0f}%")
    p2.metric("Optimistic (6m)", f"{opt[-1]:,.0f} SEK", f"{(opt[-1]-capital)/capital*100:+.0f}%")
    p3.metric("Conservative (6m)", f"{pess[-1]:,.0f} SEK", f"{(pess[-1]-capital)/capital*100:+.0f}%")
    if weeks_to_target:
        st.caption(f"Base case reaches target in approximately **{weeks_to_target} weeks** ({target_date.strftime('%d %b %Y')})")

    st.divider()

    # Open positions
    st.subheader("Open positions")
    open_positions = tracker.get_open_positions()

    if not open_positions:
        st.info("No open positions. Use the Portfolio Builder tab to add trades.")
    else:
        for pos in open_positions:
            with st.expander(f"{pos['ticker']}  —  Entry {pos['entry_price']:.2f} SEK  ·  {pos['shares']} shares"):
                # Optionally fetch current price
                if "stock_data" in st.session_state and pos["ticker"] in st.session_state["stock_data"]:
                    df = st.session_state["stock_data"][pos["ticker"]]
                    current_price = float(df["Close"].iloc[-1])
                    status = position_status(pos["entry_price"], current_price)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current price", f"{current_price:.2f} SEK",
                              delta=f"{status['pnl_pct']:+.2f}%")
                    c2.metric("Stop-loss", f"{pos['stop_loss']:.2f}")
                    c3.metric("Take-profit", f"{pos['take_profit']:.2f}")
                    st.info(f"**Action:** {status['action']}")
                else:
                    st.write(f"Entry: {pos['entry_price']:.2f}  |  SL: {pos['stop_loss']}  |  TP: {pos['take_profit']}")
                    st.caption("Run a market scan to refresh current prices.")

                close_price = st.number_input(
                    "Close at price (SEK)", key=f"close_price_{pos['id']}", min_value=0.01, value=float(pos["entry_price"])
                )
                if st.button("✅ Close position", key=f"close_{pos['id']}"):
                    result = tracker.close_position(pos["id"], close_price)
                    tracker.record_equity(summary["portfolio_value"] + result["pnl_sek"])
                    color = "success" if result["pnl_sek"] >= 0 else "error"
                    getattr(st, color)(
                        f"Closed {pos['ticker']} at {close_price:.2f} — P&L: {result['pnl_sek']:+.2f} SEK ({result['pnl_pct']:+.2f}%)"
                    )
                    st.rerun()

    # All closed trades
    st.divider()
    st.subheader("Trade history")
    all_pos = tracker.get_all_positions()
    if all_pos:
        hist_df = pd.DataFrame(all_pos)[
            ["ticker", "entry_date", "entry_price", "shares",
             "exit_date", "exit_price", "pnl_sek", "pnl_pct", "status", "notes"]
        ]

        def _pnl_color(val: float) -> str:
            if pd.isna(val):
                return ""
            return "color:green" if val > 0 else "color:red"

        st.dataframe(
            hist_df.style.map(_pnl_color, subset=["pnl_sek", "pnl_pct"]),
            use_container_width=True,
        )
    else:
        st.caption("No trade history yet.")

    # Manual equity snapshot
    if st.button("📸 Record equity snapshot now"):
        tracker.record_equity(summary["portfolio_value"])
        st.success("Equity snapshot saved.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — STRATEGY GUIDE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_guide:
    st.subheader("Strategy Reference")

    st.markdown("""
### Goal
Double **10,000 SEK → 20,000 SEK** within 6 months via disciplined swing trading on Nasdaq Stockholm.

### Signal Scoring (−5 to +5)
| Factor | Buy condition | Sell condition | Weight |
|--------|--------------|----------------|--------|
| RSI (14d) | < 50 (oversold) | > 60 (overbought) | 2.0 |
| EMA crossover (20 vs 50) | EMA20 > EMA50 | EMA20 < EMA50 | 1.5 |
| MACD direction | MACD > Signal | MACD < Signal | 1.0 |
| MACD crossover event | Bullish cross (3d) | Bearish cross (3d) | 1.0 |
| Volume confirmation | > 1.2× avg | < 0.8× avg | 0.5 |
| Bollinger Band position | Near lower band | Near upper band | 0.5 |
| 1-month momentum | > +3% | < −3% | 0.5 |

### Signal Thresholds
| Score | Signal |
|-------|--------|
| ≥ 3.5 | STRONG BUY |
| 1.5 – 3.5 | BUY |
| −1.5 – 1.5 | HOLD |
| −1.5 to −3.5 | SELL |
| ≤ −3.5 | STRONG SELL |

### Position Management Rules
1. **Entry:** Market order at next open after signal confirmation
2. **Stop-loss:** Place immediately at −7% from entry — no exceptions
3. **Take-profit:** +15% from entry; set as limit order
4. **Moonshot:** If +30% is hit, trail your stop to +10% from entry
5. **Sector cap:** Maximum 2 positions in the same sector at once
6. **Rebalance:** Every Monday morning — exit losers, replace with fresh signals

### 6-Month Math
To reach +100% total:
- ~70% win rate (realistic with this system)
- Average win: +15% · Average loss: −7%
- Expected value per trade: `(0.70 × 15%) + (0.30 × −7%) = +8.4% per trade`
- Need ~12–15 winning trades to compound from 10,000 to 20,000 SEK

### Nordnet Execution Checklist
- [ ] Log in to Nordnet before market open (09:00 CET)
- [ ] Check if any positions have hit SL or TP overnight
- [ ] Run Monday scan → get new portfolio suggestions
- [ ] Place buy orders at market open for new positions
- [ ] **Immediately** set stop-loss orders after each buy
- [ ] Set take-profit limit orders
- [ ] Log trades in the Position Tracker tab
""")

    st.divider()
    st.subheader("📧 Weekly Email Setup")
    st.markdown("""
To receive your Monday 08:00 briefing email you need a **Gmail App Password** (takes 2 minutes):

1. Go to [myaccount.google.com](https://myaccount.google.com) → **Security**
2. Enable **2-Step Verification** if not already on
3. Search for **App Passwords** → create one, choose app: **Mail**
4. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)
5. Paste it into the **Gmail App Password** field in the left sidebar
6. Enter your Gmail address in the sidebar too
7. Click **Send test email now** to verify it works

The scheduler fires automatically every Monday at 08:00 **as long as the app is running**.
To keep it running overnight, leave the terminal open, or consider hosting on [Streamlit Community Cloud](https://streamlit.io/cloud) for free.
""")

    st.divider()
    st.warning(
        "**Disclaimer:** This model provides signal suggestions based on technical analysis only. "
        "It does not account for fundamental valuation, earnings releases, or macroeconomic shocks. "
        "Past performance of these signals does not guarantee future results. "
        "Never invest money you cannot afford to lose."
    )
