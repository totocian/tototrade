# S&P 500 liquid large-cap universe — fast to scan, well-known stocks
SP500 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "UNH", "XOM",
    "LLY", "JPM", "V", "AVGO", "PG", "MA", "HD", "COST", "MRK", "ABBV",
    "CVX", "PEP", "KO", "ADBE", "WMT", "MCD", "CRM", "BAC", "ACN", "NFLX",
    "AMD", "TMO", "LIN", "CSCO", "ORCL", "ABT", "DHR", "TXN", "CMCSA", "NEE",
    "NKE", "PM", "INTC", "INTU", "AMGN", "HON", "IBM", "UPS", "CAT", "GS",
    "QCOM", "MS", "SPGI", "RTX", "LOW", "ELV", "AMAT", "ISRG", "BKNG", "AXP",
    "SYK", "GILD", "ADI", "VRTX", "PLD", "MDLZ", "TJX", "REGN", "BLK", "MMC",
    "CVS", "ZTS", "CI", "ETN", "DE", "BSX", "ADP", "LRCX", "MO", "CB",
    "SO", "DUK", "SLB", "CME", "AON", "BMY", "ITW", "NOC", "HCA", "GE",
    "PNC", "F", "GM", "USB", "FCX", "EOG", "PSA", "TGT", "EMR", "NSC",
    "WM", "FDX", "EW", "MCO", "MPC", "HUM", "AIG", "OXY", "APD", "TEL",
    "COP", "SHW", "JCI", "DXCM", "IDXX", "KLAC", "MCHP", "CDNS", "SNPS", "FTNT",
    "PANW", "CRWD", "ZS", "SNOW", "DDOG", "NET", "MDB", "TEAM", "OKTA", "HUBS",
    "SQ", "PYPL", "SHOP", "UBER", "LYFT", "ABNB", "DASH", "RBLX", "COIN", "HOOD",
]


CRYPTO = [
    "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "LINK/USD",
    "DOGE/USD", "SHIB/USD", "LTC/USD", "BCH/USD", "UNI/USD",
    "AAVE/USD", "DOT/USD", "MATIC/USD", "XRP/USD", "ADA/USD",
]


def get_universe(include_crypto: bool = False) -> list[tuple[str, bool]]:
    stocks = [(s, False) for s in SP500]
    if include_crypto:
        return stocks + [(c, True) for c in CRYPTO]
    return stocks
