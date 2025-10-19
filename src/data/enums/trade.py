from src.data.enums import BaseEnum


class TradeType(BaseEnum):
    """Enum representing trade direction types."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(BaseEnum):
    """Enum representing different types of trading orders."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop limit"  # MT5 only


class SLTPType(BaseEnum):
    """Enum representing Stop Loss/Take Profit available types."""
    PRICE = "price"
    POINTS = "points"
