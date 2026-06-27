import os
import logging
from datetime import datetime
from bot.alpaca_client import (
    get_account, get_positions, get_bars,
    place_market_order, close_position, get_tradable_us_stocks
)
from bot.indicators import combined_score

logger = logging.getLogger(__name__)

# In-memory trade log shared with Flask app
trade_log: list[dict] = []

BUY_THRESHOLD = 2
SELL_THRESHOLD = -1


def _risk_per_trade() -> float:
    return float(os.getenv("RISK_PER_TRADE", "0.02"))


def _max_positions() -> int:
    return int(os.getenv("MAX_POSITIONS", "10"))


def run_scan(live: bool = False) -> dict:
    logger.info("Starting scan (live=%s)", live)
    try:
        account = get_account(live)
        portfolio_value = account["portfolio_value"]
    except Exception as e:
        logger.error("Failed to fetch account: %s", e)
        return {"error": str(e)}

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
        try:
            df = get_bars(sym, days=90, live=live)
            if df is None or len(df) < 50:
                continue
            score = combined_score(df)
            if score <= SELL_THRESHOLD:
                result = close_position(sym, live=live)
                entry = {
                    "time": datetime.utcnow().isoformat(),
                    "symbol": sym,
                    "action": "SELL",
                    "score": score,
                    "order_id": result.get("order_id"),
                }
                trade_log.append(entry)
                sold.append(sym)
                logger.info("Sold %s (score=%d)", sym, score)
        except Exception as e:
            logger.warning("Error evaluating %s for sell: %s", sym, e)

    # Update held symbols after sells
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

    # Sort by score descending, take top slots
    candidates.sort(key=lambda x: x[1], reverse=True)
    candidates = candidates[:open_slots]

    trade_amount = portfolio_value * _risk_per_trade()

    for sym, score in candidates:
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
                "order_id": result.get("id"),
            }
            trade_log.append(entry)
            bought.append(sym)
            logger.info("Bought %s qty=%.4f score=%d", sym, qty, score)
        except Exception as e:
            logger.warning("Failed to buy %s: %s", sym, e)

    return {"sold": sold, "bought": bought}
