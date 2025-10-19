import json
import re
from enum import Enum
from typing import Dict, Any

from requests import Response

from src.data.consts import SEND_ICON, RECEIVE_ICON
from src.utils.logging_utils import logger


def format_display_dict(data, flatten: bool = True) -> str:
    """Format data for display in reports with enum handling.
    Args:
        data: Object with/without to_dict() method or dictionary
        flatten: If True, return single-line format; if False, return JSON format
    Returns:
        Formatted string with enum values converted to title case
    """
    # Get dictionary representation
    if hasattr(data, 'to_dict') and callable(getattr(data, 'to_dict')):
        dict_data = data.to_dict()
    else:
        dict_data = data

    # Convert enums to their title-cased values
    def convert_enums(obj):
        if isinstance(obj, dict):
            return {k: convert_enums(v) for k, v in obj.items()}
        elif isinstance(obj, Enum):
            return obj.value.title() if isinstance(obj.value, str) else obj.value
        else:
            return obj

    converted_data = convert_enums(dict_data)

    if flatten:
        # Return flattened single-line format
        items = [f"{k}: {v}" for k, v in converted_data.items()]
        return ", ".join(items)
    else:
        # Return JSON format
        return json.dumps(converted_data, indent=2)


def locator_format(value: str):
    """return the string as locator format: EX: Good Till Cancelled -> good-till-cancel"""
    return value.lower().replace(" ", "-").lower()


def is_integer(s):
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


def is_float(s):
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def extract_asset_tab_number(text: str) -> int | None:
    """Extract number from text, Example: "Open Position (13)" 13"""
    match = re.search(r"\((\d+)\)", text)
    return int(match.group(1)) if match else 0


def get_decimal(number):
    """ Return the decimal places: EX: 123 >> 0, 123.10 >> 2, 123.123 >> 3"""
    decimal_places = 0

    if "." in str(number):
        decimal_places = len(str(number).split(".")[-1])

    return decimal_places


def remove_comma(input_str: str, to_float: bool = True) -> float | int | str:
    """Remove commas from a string and return a float or int if possible."""
    res = str(input_str).replace(",", "")
    if to_float:
        try:
            res = float(res)

        except (ValueError, TypeError):
            logger.debug(f"Failed to convert {input_str} to float")
            res = input_str

    return res


def format_with_decimal(num_to_convert: int | float, decimal_places: float | str):
    """Add specific decimal places based on decimal_places: number = 123.1, decimal_places = 1.12 >> number = 123.10"""
    if isinstance(num_to_convert, str):
        return num_to_convert

    decimal_places = decimal_places if isinstance(decimal_places, int) else get_decimal(decimal_places)
    if not decimal_places:
        return num_to_convert

    return f"{num_to_convert:.{decimal_places}f}"


def format_str_price(number: float | int | str, decimal_places: int = None) -> str:
    """Format a number with commas as thousand separators and specified decimal places."""
    if not number:
        return number

    if is_float(number) or is_integer(number):
        number = remove_comma(number)
        if number.is_integer():
            number = int(number)

        format_str = "{:,.%df}" % (decimal_places if decimal_places is not None else get_decimal(number))
        return format_str.format(number)

    return number


def format_str_prices(prices, decimal: int = None):
    """
    Format all prices value back to one general format for more stable
    Sample: 1,234.10
    """
    prices = prices if isinstance(prices, list) else [prices]
    res = []
    # Add comas if not yet - convert to float
    for price in prices:
        price = format_str_price(price, decimal_places=decimal)
        res.append(price)

    return res if len(prices) > 1 else res[0]


def format_acc_balance(value: str, to_float=True):
    res = value.replace("$", "").replace(",", "").replace("+", "").replace("%", "")
    if to_float and is_float(res):
        res = float(res)
    return res


def format_dict_to_string(
        data: Dict[str, Any] = None,
        expected: Dict[str, Any] = None,
        actual: Dict[str, Any] = None
) -> str:
    """
    Format a dictionary or compare two dictionaries into a readable string.

    Args:
        data: Single dictionary to format (used when not comparing)
        expected: Expected dictionary for comparison
        actual: Actual dictionary for comparison

    Examples:
        Single dictionary:
            data = {'name': 'John', 'age': 30}
            print(format_dict_to_string(data))
            ==================================================
            name         : John
            age          : 30
            ==================================================

        Dictionary comparison:
            expected = {'name': 'John', 'age': 30}
            actual = {'name': 'John', 'status': 'active'}
            print(format_dict_to_string(None, expected, actual))
            =================================================================================
            Field               | Expected                | Actual
            ---------------------------------------------------------------------------------
            name                | John                    | John
            age                | 30                      | MISSING
            status             | MISSING                 | active
            =================================================================================
    """
    if expected is not None and actual is not None:
        # Comparison mode
        all_keys = sorted(set(list(expected.keys()) + list(actual.keys())))

        # Column widths
        field_width = 20
        value_width = 25

        # Format header
        formatted_lines = [
            f"{'Field':<{field_width}} | {'Expected':<{value_width}} | {'Actual':<{value_width}}",
            "-" * (field_width + value_width * 2 + 5)  # 5 is for the separators and spacing
        ]

        # Format each field
        for key in all_keys:
            expected_value = expected.get(key, "MISSING")
            actual_value = actual.get(key, "MISSING")

            # Convert enum values to their string representation
            if isinstance(expected_value, Enum):
                expected_value = expected_value.value
            if isinstance(actual_value, Enum):
                actual_value = actual_value.value

            formatted_lines.append(
                f"{str(key):<{field_width}} | {str(expected_value):<{value_width}} | {str(actual_value)}"
            )

    else:
        # Single dictionary mode
        field_names = {}
        fields = list(data.keys())
        formatted_lines = []

        for key in fields:
            if key in data:
                display_name = field_names.get(key, key)
                value = data[key]

                if isinstance(value, Enum):
                    value = value.value

                indent_str = " " * 0
                formatted_lines.append(f"{indent_str}{display_name:<15}: {value}")

    # Create border and format output
    border = "=" * (field_width + value_width * 2 + 5 if expected is not None and actual is not None else 50)
    indent_str = " " * 0

    return f"\n{indent_str}{border}\n" + "\n".join(formatted_lines) + f"\n{indent_str}{border}"


def format_request(resp: Response):
    # Format request content
    method = resp.request.method.upper()
    lines = [f"curl --location --request {method} '{resp.request.url}'"]

    for key, value in resp.request.headers.items():
        lines.append(f"--header '{key}: {value}'")

    if resp.request.body and isinstance(resp.request.body, (str, bytes)):
        try:
            data = json.loads(resp.request.body)
            json_data = json.dumps(data)  # compact form

        except Exception:
            json_data = resp.request.body.decode() if isinstance(resp.request.body, bytes) else resp.request.body

        lines.append(f"--data-raw '{json_data}'")

    curl_command = " \n".join(lines)
    return curl_command


def format_response(resp: Response, fields_to_show: list[str] = None, truncate_len: int = 5):
    """Format response content with optional field filtering for both list and dictionary responses.
    Args:
        resp: Response object to format
        fields_to_show: Optional list of field names to include in the output. If None, all fields will be shown.
    """
    try:
        content = resp.json()

        # Handle both list and dictionary responses with field filtering
        if "result" in content:
            result = content["result"]

            if isinstance(result, list):
                # Handle list responses
                if fields_to_show and len(result) > 0 and isinstance(result[0], dict):
                    filtered_result = []
                    for item in result:
                        # Get requested fields
                        filtered_item = {k: item[k] for k in fields_to_show if k in item}
                        # Add ellipsis if there are more fields than shown
                        if len(item) > len(filtered_item):
                            filtered_item["..."] = f"({len(item) - len(filtered_item)} more fields)"
                        filtered_result.append(filtered_item)
                    result = filtered_result

                # Truncate long lists
                if len(result) > truncate_len:
                    left_resp = len(result) - truncate_len
                    content["result"] = result[:truncate_len] + [f"... ({left_resp} more)"]
                else:
                    content["result"] = result

            elif isinstance(result, dict) and fields_to_show:
                # Handle dictionary responses
                filtered_result = {k: result[k] for k in fields_to_show if k in result}
                # Add ellipsis if there are more fields than shown
                if len(result) > len(filtered_result):
                    filtered_result["..."] = f"({len(result) - len(filtered_result)} more fields)"
                content["result"] = filtered_result

        response_text = json.dumps(content, indent=4)

    except ValueError:
        response_text = resp.text.strip()

    return response_text


def format_request_log(resp: Response, log_resp=False, fields_to_show=None, truncate_len=5) -> str:
    # Format request content
    request = format_request(resp)
    response = format_response(resp, fields_to_show, truncate_len)

    if log_resp:
        return f"{SEND_ICON}  Request Sent: \n{request}\n\n {RECEIVE_ICON}  Response Received: \n{response}\n\n"

    return f"{SEND_ICON}  Request Sent: \n{request}\n\n"
