import pandas as pd


def compute_rsi(df: pd.DataFrame, period: int = 14) -> float:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if pd.notna(val) else 50.0


def compute_macd(df: pd.DataFrame) -> dict:
    close = df["close"]
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return {
        "macd": float(macd.iloc[-1]),
        "signal": float(signal.iloc[-1]),
        "histogram": float(histogram.iloc[-1]),
    }


def compute_bollinger(df: pd.DataFrame, period: int = 20) -> dict:
    close = df["close"]
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    price = float(close.iloc[-1])
    u, m, l = float(upper.iloc[-1]), float(mid.iloc[-1]), float(lower.iloc[-1])
    return {"upper": u, "mid": m, "lower": l, "width": u - l, "price": price}


def compute_ma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> dict:
    close = df["close"]
    f = float(close.rolling(fast).mean().iloc[-1])
    s = float(close.rolling(slow).mean().iloc[-1])
    return {"fast": f, "slow": s, "bullish": f > s}


def combined_score(df: pd.DataFrame) -> int:
    score = 0

    rsi = compute_rsi(df)
    if rsi < 35:
        score += 1
    elif rsi > 65:
        score -= 1

    macd = compute_macd(df)
    if macd["histogram"] > 0:
        score += 1
    elif macd["histogram"] < 0:
        score -= 1

    bb = compute_bollinger(df)
    if bb["width"] > 0:
        band_pos = (bb["price"] - bb["lower"]) / bb["width"]
        if band_pos < 0.2:
            score += 1
        elif band_pos > 0.8:
            score -= 1

    ma = compute_ma_crossover(df)
    if ma["bullish"]:
        score += 1
    else:
        score -= 1

    return max(-4, min(4, score))
