"""
SQLite-backed position tracker.
Persists entry trades, logs current prices, and computes running equity curve.
"""
import sqlite3
import math
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "portfolio.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS positions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            entry_date  TEXT NOT NULL,
            entry_price REAL NOT NULL,
            shares      INTEGER NOT NULL,
            position_sek REAL NOT NULL,
            stop_loss   REAL NOT NULL,
            take_profit REAL NOT NULL,
            status      TEXT DEFAULT 'OPEN',   -- OPEN | CLOSED
            exit_date   TEXT,
            exit_price  REAL,
            pnl_sek     REAL,
            pnl_pct     REAL,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS price_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_ts TEXT NOT NULL,
            ticker      TEXT NOT NULL,
            price       REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS equity_curve (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            equity_sek  REAL NOT NULL
        );
    """)
    conn.commit()


def add_position(
    ticker: str,
    entry_price: float,
    shares: int,
    position_sek: float,
    stop_loss: float,
    take_profit: float,
    notes: str = "",
) -> int:
    """Record a new open position. Returns the new row id."""
    with _connect() as conn:
        _init_db(conn)
        cur = conn.execute(
            """INSERT INTO positions
               (ticker, entry_date, entry_price, shares, position_sek, stop_loss, take_profit, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticker, datetime.utcnow().isoformat(), entry_price, shares,
             position_sek, stop_loss, take_profit, notes),
        )
        return cur.lastrowid


def close_position(position_id: int, exit_price: float) -> dict:
    """Mark a position closed and compute realized P&L."""
    with _connect() as conn:
        _init_db(conn)
        row = conn.execute(
            "SELECT * FROM positions WHERE id = ?", (position_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Position {position_id} not found")
        pnl_sek = round((exit_price - row["entry_price"]) * row["shares"], 2)
        pnl_pct = round((exit_price - row["entry_price"]) / row["entry_price"] * 100, 2)
        conn.execute(
            """UPDATE positions
               SET status='CLOSED', exit_date=?, exit_price=?, pnl_sek=?, pnl_pct=?
               WHERE id=?""",
            (datetime.utcnow().isoformat(), exit_price, pnl_sek, pnl_pct, position_id),
        )
        return {"pnl_sek": pnl_sek, "pnl_pct": pnl_pct}


def get_open_positions() -> list[dict]:
    with _connect() as conn:
        _init_db(conn)
        rows = conn.execute(
            "SELECT * FROM positions WHERE status='OPEN' ORDER BY entry_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_positions() -> list[dict]:
    with _connect() as conn:
        _init_db(conn)
        rows = conn.execute(
            "SELECT * FROM positions ORDER BY entry_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def record_snapshot(prices: dict[str, float]) -> None:
    """Save current prices for all open tickers."""
    ts = datetime.utcnow().isoformat()
    with _connect() as conn:
        _init_db(conn)
        conn.executemany(
            "INSERT INTO price_snapshots (snapshot_ts, ticker, price) VALUES (?, ?, ?)",
            [(ts, t, p) for t, p in prices.items()],
        )


def record_equity(equity_sek: float) -> None:
    with _connect() as conn:
        _init_db(conn)
        conn.execute(
            "INSERT INTO equity_curve (recorded_at, equity_sek) VALUES (?, ?)",
            (datetime.utcnow().isoformat(), equity_sek),
        )


def get_equity_curve() -> list[dict]:
    with _connect() as conn:
        _init_db(conn)
        rows = conn.execute(
            "SELECT recorded_at, equity_sek FROM equity_curve ORDER BY recorded_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def performance_summary(starting_capital: float = 10_000.0) -> dict:
    """Compute key metrics from closed positions."""
    with _connect() as conn:
        _init_db(conn)
        closed = conn.execute(
            "SELECT pnl_sek, pnl_pct FROM positions WHERE status='CLOSED'"
        ).fetchall()

    if not closed:
        return {
            "closed_trades": 0,
            "total_pnl_sek": 0.0,
            "win_rate_pct": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "sharpe": 0.0,
            "portfolio_value": starting_capital,
            "total_return_pct": 0.0,
        }

    pnls = [r["pnl_pct"] for r in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total_pnl_sek = sum(r["pnl_sek"] for r in closed)
    portfolio_value = starting_capital + total_pnl_sek
    total_return_pct = round((portfolio_value - starting_capital) / starting_capital * 100, 2)

    mean_ret = sum(pnls) / len(pnls)
    variance = sum((p - mean_ret) ** 2 for p in pnls) / len(pnls)
    std_ret = math.sqrt(variance) if variance > 0 else 1
    sharpe = round((mean_ret / std_ret) * (252 ** 0.5 / 20), 2)  # rough annualised

    return {
        "closed_trades": len(closed),
        "total_pnl_sek": round(total_pnl_sek, 2),
        "win_rate_pct": round(len(wins) / len(pnls) * 100, 1),
        "avg_win_pct": round(sum(wins) / len(wins), 2) if wins else 0.0,
        "avg_loss_pct": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "sharpe": sharpe,
        "portfolio_value": round(portfolio_value, 2),
        "total_return_pct": total_return_pct,
    }
