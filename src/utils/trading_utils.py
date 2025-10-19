import random
import re

from src.data.enums.trade import OrderType, TradeType, SLTPType
from src.data.objects.trade import ObjectTrade
from src.utils import DotDict
from src.utils.format_utils import remove_comma, get_decimal, format_str_price

RR_RATIO = [1.0, 1.5, 2.0]
"""SUMMARY PRICES LOGIC"""


def _point_step(current_price):
    """Get point step value"""
    point_step = ObjectTrade.POINT_STEP
    if not point_step:
        # extract point step from current price
        str_price = str(current_price)
        if '.' not in str_price:
            point_step = 1.0

        else:
            decimal_part = str_price.split('.')[1]
            point_step = 1.0 / (10 ** len(decimal_part))

    return point_step


def _decimal(current_price):
    """Get decimal places"""
    decimal = ObjectTrade.DECIMAL
    if decimal is None:
        # extract decimal from current price
        decimal = get_decimal(current_price)

    return decimal


def _rr_ratio():
    return random.choice(RR_RATIO)


def _adjust_prices(price, diff_price, format_round=True):
    result = [price + diff_price, price - diff_price]

    if format_round:
        decimal = _decimal(price)
        result = [round(item, decimal) for item in result]

    return result


def random_points(current_price: float, min_pct_dis=0.2, max_pct_dis=0.3):
    """Random points with safe range"""
    stop_level = ObjectTrade.STOP_LEVEL
    point_step = _point_step(current_price)

    min_price_dist = max(current_price * min_pct_dis, 0.005)
    max_price_dist = current_price * max_pct_dis

    min_points = max(int(min_price_dist / point_step), stop_level + 10)
    max_points = max(int(max_price_dist / point_step), stop_level + 20)

    points = random.randint(min_points, max_points)

    return points


def get_sl_tp(current_price, trade_type: TradeType, sl_type: SLTPType = SLTPType.PRICE, tp_type: SLTPType = SLTPType.PRICE, is_invalid=False, is_modify=False):
    """Calculate SL and TP with configurable risk-reward ratio"""
    current_price = remove_comma(current_price)
    point_step = _point_step(current_price)

    # Generate random points for stop loss
    sl_points = random_points(current_price)

    if is_modify:
        # random points with other realistic min_pct_dis and max_pct_dis
        increase_risk = random.randint(0, 1)
        sl_points = random_points(
            current_price,
            min_pct_dis=0.05 if increase_risk else 0.02,
            max_pct_dis=0.3 if increase_risk else 0.15
        )

    tp_points = int(sl_points * _rr_ratio())

    # Calculate price differences
    sl_diff, tp_diff = [points * point_step for points in [sl_points, tp_points]]

    # Reverse logic for invalid orders
    if is_invalid:
        sl_diff = -sl_diff
        tp_diff = -tp_diff

    is_buy = trade_type == TradeType.BUY

    inc_sl, dec_sl = _adjust_prices(current_price, sl_diff)
    inc_tp, dec_tp = _adjust_prices(current_price, tp_diff)

    price_map = {
        "sl": {SLTPType.PRICE: dec_sl if is_buy else inc_sl, SLTPType.POINTS: sl_points},
        "tp": {SLTPType.PRICE: inc_tp if is_buy else dec_tp, SLTPType.POINTS: tp_points}
    }
    return DotDict(sl=price_map["sl"].get(sl_type, None), tp=price_map["tp"].get(tp_type, None))


def get_modified_sl_tp(current_price, trade_type: TradeType, increase_risk=False, is_invalid=False):
    """
    Generate new modified SL/TP prices with a new RR ratio.
    Optionally increases risk by using a wider stop distance.
    """
    point_step = _point_step(current_price)
    is_buy = trade_type == TradeType.BUY

    # Use wider points if increasing risk (simulate wider SL)
    sl_points = random_points(
        current_price,
        min_pct_dis=0.05 if increase_risk else 0.02,
        max_pct_dis=0.3 if increase_risk else 0.15
    )
    tp_points = int(sl_points * _rr_ratio())

    sl_diff = sl_points * point_step
    tp_diff = tp_points * point_step

    if is_invalid:
        sl_diff = -sl_diff
        tp_diff = -tp_diff

    inc_sl, dec_sl = _adjust_prices(current_price, sl_diff)
    inc_tp, dec_tp = _adjust_prices(current_price, tp_diff)

    return {"stop_loss": dec_sl if is_buy else inc_sl, "take_profit": inc_tp if is_buy else dec_tp}


def get_pending_price(current_price, trade_type: TradeType, order_type: OrderType, is_invalid=False):
    """Calculate pending order price with crypto-optimized gap percentages"""
    if order_type.is_market():
        return None

    current_price = remove_comma(current_price)
    point_step = _point_step(current_price)
    stop_level = ObjectTrade.STOP_LEVEL or 10

    # safe price gap between pending and current price
    gap_buffer = stop_level * point_step * random.randint(2, 5)

    # Crypto-optimized gap percentages
    gap_percent_range = (2.0, 3.0)
    random_percent = round(random.uniform(*gap_percent_range), 5)

    gap_price = gap_buffer + current_price * (random_percent / 100)

    # Reverse logic for invalid orders
    if is_invalid:
        gap_price = -gap_price

    inc_price, dec_price = _adjust_prices(current_price, gap_price)

    # Price calculation based on order type and trade direction
    price_map = {
        OrderType.STOP: {TradeType.BUY: inc_price, TradeType.SELL: dec_price},
        OrderType.LIMIT: {TradeType.BUY: dec_price, TradeType.SELL: inc_price}
    }

    return price_map.get(order_type, price_map[OrderType.STOP])[trade_type]


def get_stop_price(current_price, trade_type, is_invalid=False):
    """Get stop price using LIMIT order logic"""
    price = get_pending_price(current_price, trade_type, OrderType.STOP_LIMIT, is_invalid=is_invalid)
    return round(price, _decimal(current_price))


def calculate_trading_params(
        current_price: float | str,
        trade_type: TradeType,
        order_type: OrderType,
        sl_type: SLTPType = SLTPType.PRICE,
        tp_type: SLTPType = SLTPType.PRICE,
        is_invalid=False
):
    """
    Main calculation function for trading parameters
    Args:
        current_price: Current market price
        order_type: Type of order (MARKET, LIMIT, STOP)
        trade_type: Trade direction (BUY, SELL)
        sl_type: Stop loss type (PRICE or POINT)
        tp_type: Take profit type (PRICE or POINT)
        is_invalid: Generate invalid orders for testing
    """
    current_price = remove_comma(current_price)

    # Calculate stop price for stop limit orders
    stop_price = None
    if order_type.is_stp_limit():
        stop_price = get_stop_price(current_price, trade_type, is_invalid)

    # Calculate pending price
    pending_price = get_pending_price(stop_price or current_price, trade_type, order_type, is_invalid)

    # Calculate SL and TP
    sl, tp = get_sl_tp(stop_price or pending_price or current_price, trade_type, sl_type, tp_type, is_invalid).values()

    result = {
        "stop_loss": sl,
        "take_profit": tp,
        "entry_price": current_price if order_type.is_market() else pending_price,
        "stop_limit_price": stop_price,
    }

    if ObjectTrade.DECIMAL == 0:
        for key in result:
            if result[key]:
                result[key] = int(result[key])

    return DotDict(result)


def calculate_partial_close(volume, units):
    volume, units = int(volume), int(remove_comma(units))
    close_volume = random.randint(1, volume - 1)
    left_volume = volume - close_volume
    left_units = int(units * left_volume / volume)
    close_units = int(units - left_units)

    return DotDict(
        left_volume=format_str_price(left_volume, 0),
        close_volume=format_str_price(close_volume, 0),
        left_units=format_str_price(left_units, 0),
        close_units=format_str_price(close_units, 0),
    )


# ------ NOTIFICATION HANDLER ------ #
"""
ALL TRADING NOTIFICATION SAMPLE
1. Banner
- XRPUSD.std - BUY ORDER placed, Size: 1 / Units: 1,000. Stop Loss: 2.5649. Take Profit: 2.5895.
- XRPUSD.std - BUY LIMIT ORDER placed, Size: 1 / Units: 1,000. Price: 2.2000. Stop Loss: 2.1877. Take Profit: 2.2123.
- ETH.USD - BUY STOP LIMIT ORDER placed, Volume: 0.1 / Units: 0.1. Stop Limit Price: 2,993.22. Price: 2,994.18. Stop Loss: 2,991.99. Take Profit: 2,994.45.
- ETH.USD - BUY ORDER updated, Volume: 9 / Units: 9. Entry Price: 2,520.70. Stop Loss: 2,994.23. Take Profit: 2,996.69.

2. Details
- Open Position: Open Position: #8526920 AUDNZD.std: Size 0.02 / Units 2,000 @ 1.07698 
- Position Closed: #7592152 DASHUSD.std: Size 0.02 / Units 0.2 @ 19.92, Loss of -1.82
"""

def parse_noti_prices(noti: str) -> dict[str, float]:
    price_patterns = [
        r'@\s*([\d,]+\.?\d*)',  # Price after @ symbol
        r'\.\s+Price:\s*([\d,]+\.?\d*)',  # Exact ". Price:"
        r'Entry Price:\s*([\d,]+\.?\d*)',
        r'Stop Loss:\s*([\d,]+\.?\d*)',
        r'Take Profit:\s*([\d,]+\.?\d*)',
        r'Stop Limit Price:\s*([\d,]+\.?\d*)',
    ]

    res = {}

    for pattern in price_patterns:
        match = re.search(pattern, noti)
        if match:
            try:
                price_str = match.group(1).replace(',', '')

                raw_key = match.group(0).split(":")[0]
                raw_key = raw_key.strip().lstrip(".").strip()  # remove leading period if present
                key = "entry_price" if "@" in match.group(0) else raw_key.lower().replace(" ", "_")

                res[key] = float(price_str)
            except ValueError:
                continue

        # Remove duplicate "price" if "entry_price" exists
        if "price" in res and "entry_price" in res:
            res.pop("price", None)

    return res


def normalize_noti_prices(
       noti: str, price_dict: dict[str, float], decimal: int = 0
):
    """
    Replace prices value in notification with extracted price values from price_dict. Used for compare notification with tolerance
    :param noti: Original notification text
    :param price_dict: output from parse_noti_prices
    :param decimal: Decimal places of price
    :return: Normalized notification with replaced prices
    """
    pattern_key_mapping = {
        r'@\s*[\d,]+\.?\d*': 'entry_price',
        r'Entry Price:\s*[\d,]+\.?\d*': 'entry_price',
        r'\.\s+Price:\s*([\d,]+\.?\d*)': 'price',
        r'Stop Loss:\s*[\d,]+\.?\d*': 'stop_loss',
        r'Take Profit:\s*[\d,]+\.?\d*': 'take_profit',
        r'Stop Limit Price:\s*[\d,]+\.?\d*': 'stop_limit_price'
    }

    result = noti

    for pattern, key in pattern_key_mapping.items():
        if key in price_dict:
            result = re.sub(
                pattern,
                lambda m: m.group(0).replace(
                    re.search(r'[\d,]+\.?\d*', m.group(0)).group(0),
                    format_str_price(price_dict[key], decimal)
                ),
                result
            )

    return result

