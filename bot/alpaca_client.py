import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetAssetsRequest
from alpaca.trading.enums import OrderSide, TimeInForce, AssetClass, AssetStatus
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import pandas as pd


def _get_clients(live: bool = False):
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")
    paper = not live
    trading = TradingClient(api_key, secret_key, paper=paper)
    stock_data = StockHistoricalDataClient(api_key, secret_key)
    crypto_data = CryptoHistoricalDataClient(api_key, secret_key)
    return trading, stock_data, crypto_data


def get_account(live: bool = False) -> dict:
    trading, _, __ = _get_clients(live)
    account = trading.get_account()
    return {
        "portfolio_value": float(account.portfolio_value),
        "cash": float(account.cash),
        "buying_power": float(account.buying_power),
        "equity": float(account.equity),
    }


def get_positions(live: bool = False) -> list[dict]:
    trading, _, __ = _get_clients(live)
    positions = trading.get_all_positions()
    result = []
    for p in positions:
        result.append({
            "symbol": p.symbol,
            "qty": float(p.qty),
            "avg_entry_price": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc),
            "side": p.side.value,
        })
    return result


def get_bars(symbol: str, days: int = 60, live: bool = False, crypto: bool = False) -> pd.DataFrame:
    _, stock_data, crypto_data = _get_clients(live)
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    if crypto:
        req = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
        )
        bars = crypto_data.get_crypto_bars(req)
    else:
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
        )
        bars = stock_data.get_stock_bars(req)

    df = bars.df
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level=0)
    df = df.sort_index()
    return df


def place_market_order(symbol: str, qty: float, side: str, live: bool = False, crypto: bool = False) -> dict:
    trading, _, __ = _get_clients(live)
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    # Crypto uses GTC (good till cancelled), stocks use DAY
    tif = TimeInForce.GTC if crypto else TimeInForce.DAY
    req = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=order_side,
        time_in_force=tif,
    )
    order = trading.submit_order(req)
    return {"id": str(order.id), "symbol": symbol, "qty": qty, "side": side, "status": order.status.value}


def close_position(symbol: str, live: bool = False) -> dict:
    trading, _, __ = _get_clients(live)
    response = trading.close_position(symbol)
    return {"symbol": symbol, "status": "closed", "order_id": str(response.id)}


def get_tradable_us_stocks(live: bool = False) -> list[str]:
    trading, _, __ = _get_clients(live)
    req = GetAssetsRequest(asset_class=AssetClass.US_EQUITY, status=AssetStatus.ACTIVE)
    assets = trading.get_all_assets(req)
    return [a.symbol for a in assets if a.tradable and a.fractionable and not a.easy_to_borrow is False]
