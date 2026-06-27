import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

import bot.trade_log as tlog
tlog.load()

from bot.alpaca_client import get_account, get_positions
from bot.strategy import run_scan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_live_trading = os.getenv("LIVE_TRADING", "false").lower() == "true"
_scan_interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))
_last_scan: dict = {}
_scheduler = BackgroundScheduler()

# Runtime-editable settings
_settings = {
    "stop_loss_pct": float(os.getenv("STOP_LOSS_PCT", "0.05")),
    "allowed_sectors": os.getenv("ALLOWED_SECTORS", ""),
    "risk_per_trade": float(os.getenv("RISK_PER_TRADE", "0.02")),
    "max_positions": int(os.getenv("MAX_POSITIONS", "10")),
}


def _apply_settings():
    os.environ["STOP_LOSS_PCT"] = str(_settings["stop_loss_pct"])
    os.environ["ALLOWED_SECTORS"] = _settings["allowed_sectors"]
    os.environ["RISK_PER_TRADE"] = str(_settings["risk_per_trade"])
    os.environ["MAX_POSITIONS"] = str(_settings["max_positions"])


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
        "settings": _settings,
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
    return jsonify(tlog.trade_log[-limit:])


@app.route("/api/scan", methods=["POST"])
def scan():
    global _last_scan
    result = run_scan(live=_live_trading)
    _last_scan = {"time": datetime.utcnow().isoformat(), **result}
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


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(_settings)


@app.route("/api/settings", methods=["POST"])
def update_settings():
    body = request.get_json(silent=True) or {}
    if "stop_loss_pct" in body:
        _settings["stop_loss_pct"] = float(body["stop_loss_pct"])
    if "allowed_sectors" in body:
        _settings["allowed_sectors"] = str(body["allowed_sectors"])
    if "risk_per_trade" in body:
        _settings["risk_per_trade"] = float(body["risk_per_trade"])
    if "max_positions" in body:
        _settings["max_positions"] = int(body["max_positions"])
    _apply_settings()
    logger.info("Settings updated: %s", _settings)
    return jsonify(_settings)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)
