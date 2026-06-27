import os
import logging
from datetime import datetime
from bot.alpaca_client import (
    get_account, get_positions, get_bars,
    place_market_order, close_position, get_tradable_us_stocks
)
from bot.indicators import combined_score
from bot.notifier import send_trade_email
import bot.trade_log as tlog

logger = logging.getLogger(__name__)

BUY_THRESHOLD = 2
SELL_THRESHOLD = -1


def _risk_per_trade() -> float:
    return float(os.getenv("RISK_PER_TRADE", "0.02"))


def _max_positions() -> int:
    return int(os.getenv("MAX_POSITIONS", "10"))


def _stop_loss_pct() -> float:
    return float(os.getenv("STOP_LOSS_PCT", "0.05"))


def _allowed_sectors() -> set[str]:
    raw = os.getenv("ALLOWED_SECTORS", "")
    if not raw.strip():
        return set()
    return {s.strip().lower() for s in raw.split(",")}


def _get_sector(symbol: str) -> str:
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info
        return (info.get("sector") or "").lower()
    except Exception:
        return ""


def run_scan(live: bool = False) -> dict:
    logger.info("Starting scan (live=%s)", live)
    try:
        account = get_account(live)
        portfolio_value = account["portfolio_value"]
    except Exception as e:
        logger.error("Failed to fetch account: %s", e)
        return {"error": str(e)}

    allowed_sectors = _allowed_sectors()
    stop_loss = _stop_loss_pct()

    # --- Sell pass ---
    try:
        positions = get_positions(live)
    except Exception as e:
        logger.error("Failed to fetch positions: %s", e)
        positions = []

    held_symbols = {p["symbol"] for p in positions}
    sold = []

    for pos in positions:
        sym = pos["symbol"]
        plpc = pos.get("unrealized_plpc", 0.0)
        reason = None

        # Stop-loss check
        if plpc <= -stop_loss:
            reason = f"stop-loss ({plpc*100:.1f}%)"
        else:
            try:
                df = get_bars(sym, days=90, live=live)
                if df is not None and len(df) >= 50:
                    score = combined_score(df)
                    if score <= SELL_THRESHOLD:
                        reason = f"score={score}"
            except Exception as e:
                logger.warning("Error evaluating %s for sell: %s", sym, e)

        if reason:
            try:
                result = close_position(sym, live=live)
                entry = {
                    "time": datetime.utcnow().isoformat(),
                    "symbol": sym,
                    "action": "SELL",
                    "score": combined_score(get_bars(sym, days=90, live=live)) if "score" in reason else None,
                    "reason": reason,
                    "order_id": result.get("order_id"),
                }
                tlog.append(entry)
                send_trade_email(entry)
                sold.append(sym)
                logger.info("Sold %s (%s)", sym, reason)
            except Exception as e:
                logger.warning("Failed to close %s: %s", sym, e)

    held_symbols -= set(sold)
    open_slots = _max_positions() - len(held_symbols)

    # --- Buy pass ---
    bought = []
    if open_slots <= 0:
        logger.info("No open slots for new positions")
        return {"sold": sold, "bought": bought}

    try:
        universe = get_tradable_us_stocks(live)
    except Exception as e:
        logger.error("Failed to fetch tradable stocks: %s", e)
        universe = []

    candidates = []
    for sym in universe:
        if sym in held_symbols:
            continue
        try:
            df = get_bars(sym, days=90, live=live)
            if df is None or len(df) < 50:
                continue
            score = combined_score(df)
            if score >= BUY_THRESHOLD:
                candidates.append((sym, score))
        except Exception as e:
            logger.debug("Skipping %s: %s", sym, e)

    candidates.sort(key=lambda x: x[1], reverse=True)

    trade_amount = portfolio_value * _risk_per_trade()

    for sym, score in candidates:
        if len(bought) >= open_slots:
            break

        # Sector filter
        if allowed_sectors:
            sector = _get_sector(sym)
            if sector not in allowed_sectors:
                logger.debug("Skipping %s — sector '%s' not in allowed list", sym, sector)
                continue
        else:
            sector = ""

        try:
            df = get_bars(sym, days=5, live=live)
            if df is None or df.empty:
                continue
            price = float(df["close"].iloc[-1])
            qty = round(trade_amount / price, 6)
            if qty < 0.001:
                continue
            result = place_market_order(sym, qty, "buy", live=live)
            entry = {
                "time": datetime.utcnow().isoformat(),
                "symbol": sym,
                "action": "BUY",
                "score": score,
                "qty": qty,
                "price": price,
                "sector": sector,
                "order_id": result.get("id"),
            }
            tlog.append(entry)
            send_trade_email(entry)
            bought.append(sym)
            logger.info("Bought %s qty=%.4f score=%d sector=%s", sym, qty, score, sector)
        except Exception as e:
            logger.warning("Failed to buy %s: %s", sym, e)

    return {"sold": sold, "bought": bought}
