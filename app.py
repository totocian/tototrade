import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

from bot.alpaca_client import get_account, get_positions
from bot.strategy import run_scan, trade_log

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global state
_live_trading = os.getenv("LIVE_TRADING", "false").lower() == "true"
_scan_interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))
_last_scan: dict = {}
_scheduler = BackgroundScheduler()


def _scheduled_scan():
    global _last_scan
    logger.info("Scheduled scan triggered")
    result = run_scan(live=_live_trading)
    _last_scan = {"time": datetime.utcnow().isoformat(), **result}


_scheduler.add_job(_scheduled_scan, "interval", minutes=_scan_interval, id="scan_job")
_scheduler.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    try:
        account = get_account(live=_live_trading)
    except Exception as e:
        account = {"error": str(e)}
    return jsonify({
        "live_trading": _live_trading,
        "scan_interval_minutes": _scan_interval,
        "last_scan": _last_scan,
        "account": account,
    })


@app.route("/api/positions")
def positions():
    try:
        data = get_positions(live=_live_trading)
    except Exception as e:
        data = {"error": str(e)}
    return jsonify(data)


@app.route("/api/trades")
def trades():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(trade_log[-limit:])


@app.route("/api/scan", methods=["POST"])
def scan():
    result = run_scan(live=_live_trading)
    return jsonify(result)


@app.route("/api/mode", methods=["POST"])
def toggle_mode():
    global _live_trading
    body = request.get_json(silent=True) or {}
    if "live" in body:
        _live_trading = bool(body["live"])
    else:
        _live_trading = not _live_trading
    logger.info("Trading mode set to live=%s", _live_trading)
    return jsonify({"live_trading": _live_trading})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)
