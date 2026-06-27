import json
import os
import logging

logger = logging.getLogger(__name__)

_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "trades.json")
_LOG_FILE = os.path.abspath(_LOG_FILE)

trade_log: list[dict] = []


def load() -> None:
    global trade_log
    if os.path.exists(_LOG_FILE):
        try:
            with open(_LOG_FILE, "r") as f:
                trade_log = json.load(f)
            logger.info("Loaded %d trades from %s", len(trade_log), _LOG_FILE)
        except Exception as e:
            logger.error("Failed to load trade log: %s", e)
            trade_log = []


def append(entry: dict) -> None:
    trade_log.append(entry)
    try:
        with open(_LOG_FILE, "w") as f:
            json.dump(trade_log, f, indent=2)
    except Exception as e:
        logger.error("Failed to save trade log: %s", e)
