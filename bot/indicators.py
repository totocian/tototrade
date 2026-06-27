import pandas as pd
import pandas_ta as ta
import numpy as np


def compute_rsi(df: pd.DataFrame, period: int = 14) -> float:
    rsi_series = ta.rsi(df["close"], length=period)
    return float(rsi_series.iloc[-1]) if rsi_series is not None and not rsi_series.empty else 50.0


def compute_macd(df: pd.DataFrame) -> dict:
    macd_df = ta.macd(df["close"])
    if macd_df is None or macd_df.empty:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
    return {
        "macd": float(macd_df["MACD_12_26_9"].iloc[-1]),
        "signal": float(macd_df["MACDs_12_26_9"].iloc[-1]),
        "histogram": float(macd_df["MACDh_12_26_9"].iloc[-1]),
    }


def compute_bollinger(df: pd.DataFrame, period: int = 20) -> dict:
    bb = ta.bbands(df["close"], length=period)
    if bb is None or bb.empty:
        return {"upper": 0.0, "mid": 0.0, "lower": 0.0, "width": 0.0}
    price = float(df["close"].iloc[-1])
    upper = float(bb[f"BBU_{period}_2.0"].iloc[-1])
    mid = float(bb[f"BBM_{period}_2.0"].iloc[-1])
    lower = float(bb[f"BBL_{period}_2.0"].iloc[-1])
    width = upper - lower
    return {"upper": upper, "mid": mid, "lower": lower, "width": width, "price": price}


def compute_ma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> dict:
    close = df["close"]
    fast_ma = ta.sma(close, length=fast)
    slow_ma = ta.sma(close, length=slow)
    if fast_ma is None or slow_ma is None or fast_ma.empty or slow_ma.empty:
        return {"fast": 0.0, "slow": 0.0, "bullish": False}
    f = float(fast_ma.iloc[-1])
    s = float(slow_ma.iloc[-1])
    return {"fast": f, "slow": s, "bullish": f > s}


def combined_score(df: pd.DataFrame) -> int:
    """Returns a signal score in the range [-4, +4]."""
    score = 0

    # RSI signal: oversold = bullish (+1), overbought = bearish (-1)
    rsi = compute_rsi(df)
    if rsi < 35:
        score += 1
    elif rsi > 65:
        score -= 1

    # MACD histogram positive = bullish (+1), negative = bearish (-1)
    macd = compute_macd(df)
    if macd["histogram"] > 0:
        score += 1
    elif macd["histogram"] < 0:
        score -= 1

    # Bollinger Bands: price near lower band = bullish, near upper = bearish
    bb = compute_bollinger(df)
    if bb["width"] > 0:
        price = bb["price"]
        band_pos = (price - bb["lower"]) / bb["width"]
        if band_pos < 0.2:
            score += 1
        elif band_pos > 0.8:
            score -= 1

    # MA crossover: fast > slow = bullish (+1)
    ma = compute_ma_crossover(df)
    if ma["bullish"]:
        score += 1
    else:
        score -= 1

    return max(-4, min(4, score))
