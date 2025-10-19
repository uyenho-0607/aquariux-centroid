import operator
from typing import Any, Callable

import pytest_check as check

from src.core.decorators import attach_table_details
from src.core.driver.driver_manager import DriverManager
from src.data.consts import FAILED_ICON_COLOR
from src.data.data_runtime import StepLogs
from src.data.objects.trade import ObjectTrade
from src.utils.allure_utils import attach_screenshot
from src.utils.format_utils import format_dict_to_string, remove_comma, is_float
from src.utils.logging_utils import logger

__all__ = [
    "assert_dict",
    "assert_contains",
    "assert_equal",
    "assert_not_equal",
    "assert_almost_equal",
    "assert_less_than",
    "assert_less_than_or_equal",
    "assert_greater_than",
    "assert_greater_than_or_equal",
    "assert_true",
    "assert_false",
    "assert_notification"
]


# ===================== UTILITIES ======================== #

def _handle_failure(error_message: str) -> None:
    """Handle assertion failure by logging, capturing screenshots, and recording failed steps."""
    # log error message
    logger.error(error_message)

    # capture failed screenshot
    for driver in DriverManager.driver_list:
        attach_screenshot(driver)

    # record failed logs
    if StepLogs.test_steps:
        verify_steps = [item.lower() for item in StepLogs.test_steps if "verify" in item.lower()]
        if verify_steps:
            failed_step = verify_steps[-1]
            StepLogs.add_failed_log(failed_step, error_message)


def _extract_diff_list(actual: dict, expected: dict, diff_keys: list) -> list[dict]:
    """
    Extract only the differing fields from actual and expected dicts.
    Args Note:
        diff_keys: List of keys that differ between the two dicts
    Returns:
        List containing [actual_diff_dict, expected_diff_dict]
    """
    res = [{k: item.get(k, "") for k in diff_keys} for item in [actual, expected]]
    return res


# ===================== CORE COMPARISON ======================== #

def _compare_with_tolerance(
        num1: str | float,
        num2: str | float,
        tolerance_percent: float = 0.1,
) -> dict:
    """
    Compare numeric values with percentage-based tolerance.
    Args Note:
        tolerance_percent: Tolerance as percentage (e.g., 0.1 for 0.1%)
    Returns:
        Dict with keys: res (bool), diff (str), diff_percent (str), tolerance (str)
    """

    epsilon = 1e-10  # For float comparisons

    # Remove commas and validate
    actual = remove_comma(num1, to_float=True)
    expected = remove_comma(num2, to_float=True)

    if not is_float(expected) or not is_float(actual):
        logger.debug(
            f"Value is not numeric - expected: {expected} ({type(expected)}), "
            f"actual: {actual} ({type(actual)})"
        )
        return dict(res=False, diff=0, diff_percent=0, tolerance="")

    # Calculate difference
    diff = abs(actual - expected)
    tol_frac = tolerance_percent / 100.0

    # Handle zero or near-zero expected value
    if abs(expected) < epsilon:
        if diff < epsilon:
            diff_percent = 0.0
        else:
            # When expected is ~0 but diff is significant, treat as infinite percent difference
            diff_percent = 999999.0  # Large number for better formatting
        tolerance_value = 0.0
    else:
        baseline = abs(expected)
        diff_percent = (diff / baseline) * 100  # Calculate as percent directly
        tolerance_value = tol_frac * baseline

    # Compare
    res = diff <= tolerance_value

    # Log failure
    if not res:
        logger.warning(
            f"Tolerance check failed - Expected: {expected}, Actual: {actual}, "
            f"Tolerance: ±{tolerance_value:.6f} ({tolerance_percent}%), "
            f"Diff: {diff:.6f} ({diff_percent:.2f}%)"
        )

    return dict(
        res=res,
        diff=f"{diff:.4f}",
        diff_percent=f"{diff_percent:.4f}",
        tolerance=f"±{tolerance_value:.2f} ({tolerance_percent:.2f}%)"
    )


def _compare_dict(
        actual: dict,
        expected: dict,
        tolerance_percent: float = 0.5,
        tolerance_fields: list[str] = None,
        tolerance_map: dict = None,
        assert_op: Callable = operator.eq
) -> dict:
    """
    Compare dictionaries field-by-field with optional tolerance for numeric fields.
    Args Note:
        tolerance_percent: Global tolerance percentage for specified fields
        tolerance_fields: List of field names to apply global tolerance to
        tolerance_map: Dict mapping field names to their specific tolerance percentages
        assert_op: Comparison operator for non-tolerance fields
    Returns:
        Dict with keys: res (bool), missing (list), redundant (list), diff (list), tolerance_info (dict)
    """
    diff_keys = []
    tolerance_info = {}
    compare_res = []

    logger.debug(f"> Compare data: {format_dict_to_string(expected=expected, actual=actual)}")

    for key in expected:

        # missing key
        if key not in actual:
            compare_res.append(False)
            continue

        # handle comparison
        act, exp = actual[key], expected[key]

        # Check if field has specific tolerance
        if tolerance_map and key in tolerance_map:
            field_tolerance = tolerance_map[key]
            res_tolerance = _compare_with_tolerance(act, exp, field_tolerance)
            res = res_tolerance["res"]
            tolerance_info[key] = dict(diff_percent=res_tolerance["diff_percent"], tolerance=res_tolerance["tolerance"])

        # Check if field should use global tolerance
        elif tolerance_percent is not None and tolerance_fields and key in tolerance_fields:
            res_tolerance = _compare_with_tolerance(act, exp, tolerance_percent)
            res = res_tolerance["res"]
            tolerance_info[key] = dict(diff_percent=res_tolerance["diff_percent"], tolerance=res_tolerance["tolerance"])

        else:
            res = assert_op(act, exp)

        compare_res.append(res)
        if not res:
            diff_keys.append(key)

    # Find missing and redundant keys
    missing = [key for key in expected.keys() if key not in actual.keys()]
    redundant = [key for key in actual.keys() if key not in expected.keys()]

    res_dict = dict(
        res=all(compare_res) and not missing and not redundant,
        missing=missing,
        redundant=redundant,
        diff=diff_keys
    )

    if (tolerance_percent is not None and tolerance_fields) or tolerance_map:
        res_dict |= {"tolerance_info": tolerance_info}

    return res_dict


@attach_table_details
def _soft_assert(
        actual: Any,
        expected: Any,
        assert_op: Callable = operator.eq,
        error_message: str = "",
        tolerance_percent: float = None,
        tolerance_fields: list[str] = None,
        tolerance_map: dict = None
) -> dict | bool:
    """
    Core soft assertion
    Args Note:
        assert_op: Comparison operator (e.g., operator.eq, operator.gt)
        tolerance_percent: Tolerance percentage for numeric comparisons
        tolerance_fields: Field names to apply global tolerance (for dicts)
        tolerance_map: Field-specific tolerance percentages (for dicts)
    Returns:
        dict for dict comparisons, bool for simple value comparisons
    """
    __tracebackhide__ = True
    validation_err_msg = f"\n {FAILED_ICON_COLOR} Validation Failed ! "

    # === Handle dictionary comparisons ===
    if isinstance(actual, dict) and isinstance(expected, dict):

        # Log tolerance info
        if tolerance_percent is not None and tolerance_fields:
            logger.debug(f"Global tolerance: {tolerance_percent}%, apply for fields: {tolerance_fields}")

        if tolerance_map:
            logger.debug(f"Field-specific tolerances: {tolerance_map}")

        # Compare dictionaries
        result = _compare_dict(
            actual, expected,
            tolerance_percent=tolerance_percent,
            tolerance_fields=tolerance_fields,
            tolerance_map=tolerance_map,
            assert_op=assert_op
        )

        # Build error message
        if result["missing"]:
            validation_err_msg += f"\n>>> Missing Fields: {result['missing']}"

        if result["redundant"]:
            validation_err_msg += f"\n>>> Redundant Fields: {result['redundant']}"

        if result["diff"]:
            diff_list = _extract_diff_list(actual, expected, result["diff"])
            validation_err_msg += (
                f"\n>>> Different Fields: "
                f"\nActual: {format_dict_to_string(diff_list[0])} "
                f"\nExpected: {format_dict_to_string(diff_list[-1])}"
            )

        # Report via pytest-check
        assertion_result = check.equal(result["res"], True, validation_err_msg)
        if not assertion_result:
            _handle_failure(validation_err_msg)

        return result

    # === Handle simple values ===
    validation_err_msg += (error_message or f"\n>>> Actual:   {actual!r} \n>>> Expected: {expected!r}")

    if tolerance_percent is not None:
        assertion_result = _compare_with_tolerance(actual, expected, tolerance_percent)["res"]

    elif assert_op is operator.contains:

        # check actual contains expected
        if isinstance(actual, (list, tuple, set)) and isinstance(expected, (list, tuple, set)):
            assertion_result = all(item in actual for item in expected)

        else:
            try:
                assertion_result = expected in actual

            except Exception as e:
                logger.error(f"Exception checking: {e}")
                assertion_result = False

    else:
        assertion_result = assert_op(actual, expected)

    # Report via pytest-check
    result = check.equal(assertion_result, True, validation_err_msg)

    # Handle failure
    if not result:
        _handle_failure(validation_err_msg)

    return result


# ===================== PUBLIC APIs ======================== #

def assert_equal(actual: Any, expected: Any, error_message: str = "") -> bool:
    """
    Soft assertion: actual == expected (no dicts).
    Examples:
        assert_equal(5, 5)
        assert_equal([1, 2, 5], [1, 2, 5])
        assert_equal("hello", "hello")
    """
    if isinstance(actual, dict) or isinstance(expected, dict):
        raise TypeError("Use assert_dict() for dictionaries")

    return _soft_assert(actual, expected, error_message=error_message)


def assert_contains(actual: Any, expected: Any, error_message: str = "") -> bool:
    """
    Soft assertion: expected in actual (no dicts).
    Examples:
        assert_contains([1, 2, 3], 2)
        assert_contains("hello world", "world")
    """
    if isinstance(actual, dict) or isinstance(expected, dict):
        raise TypeError("Use assert_dict() for dictionaries")

    return _soft_assert(actual, expected, operator.contains, error_message)


def assert_dict(
        actual: dict,
        expected: dict,
        error_message: str = "",
        tolerance_percent: float = None,
        tolerance_fields: list[str] = None,
        tolerance_map: dict = None
) -> dict:
    """
    Soft assertion for dict comparison with optional numeric tolerance.
    Args Note:
        tolerance_percent: Global tolerance % for fields in tolerance_fields
        tolerance_fields: List of field names to apply global tolerance (e.g., ['stop_loss', 'take_profit'])
        tolerance_map: Dict mapping field names to specific tolerance % (e.g., {"price": 0.1})
    
    Examples:
        assert_dict({"a": 1, "b": 'hi', "c": 10.5}, {"a": 1, "b": 'hi', "c": 10.0}, tolerance_fields=["a"], tolerance_map={"c": 5.0})
    """
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        raise TypeError("Both arguments must be dicts. Use assert_equal() for simple values")

    return _soft_assert(
        actual, expected,
        error_message=error_message,
        tolerance_percent=tolerance_percent,
        tolerance_fields=tolerance_fields,
        tolerance_map=tolerance_map
    )


def assert_true(actual: Any, error_message: str = "") -> bool:
    """Soft assertion: actual is True."""
    return _soft_assert(actual, True, error_message=error_message)


def assert_false(actual: Any, error_message: str = "") -> bool:
    """Soft assertion: actual is False."""
    return _soft_assert(actual, False, error_message=error_message)


def assert_not_equal(actual: Any, expected: Any, error_message: str = "") -> bool:
    """Soft assertion: actual != expected."""
    return _soft_assert(actual, expected, assert_op=operator.ne, error_message=error_message)


def assert_less_than(actual: Any, expected: Any, error_message: str = "") -> bool:
    """Soft assertion: actual < expected (strict)."""
    return _soft_assert(actual, expected, assert_op=operator.lt, error_message=error_message)


def assert_less_than_or_equal(actual: Any, expected: Any, error_message: str = "") -> bool:
    """Soft assertion: actual <= expected."""
    return _soft_assert(actual, expected, assert_op=operator.le, error_message=error_message)


def assert_greater_than(actual: Any, expected: Any, error_message: str = "") -> bool:
    """Soft assertion: actual > expected (strict)."""
    return _soft_assert(actual, expected, assert_op=operator.gt, error_message=error_message)


def assert_greater_than_or_equal(actual: Any, expected: Any, error_message: str = "") -> bool:
    """Soft assertion: actual >= expected."""
    return _soft_assert(actual, expected, assert_op=operator.ge, error_message=error_message)


def assert_almost_equal(
        actual: Any,
        expected: Any,
        error_message: str = "",
        tolerance_percent: float = 1
) -> bool:
    """
    Soft assertion for numeric values with percentage-based tolerance.
    Args Note:
        tolerance_percent: Tolerance as percentage (default 1%)
    Note: Only use with numeric values. For non-numeric values, use assert_equal().
    Example:
        assert_almost_equal(99.5, 100, tolerance_percent=1)  # Pass (within 1%)
    """
    return _soft_assert(actual, expected, tolerance_percent=tolerance_percent, error_message=error_message)


def assert_notification(actual: str, expected: str, error_message="", tolerance_percent=0.1):
    """Soft assertion for notification specific checking"""
    from src.utils.trading_utils import normalize_noti_prices, parse_noti_prices

    # extract prices from noti string for compare with tolerance
    act_prices = parse_noti_prices(actual)
    exp_prices = parse_noti_prices(expected)

    price_fields = ["stop_loss", "take_profit", "price", "entry_price"]
    decimal = ObjectTrade.DECIMAL  # for format prices in noti banner

    if act_prices and exp_prices:
        res_dict = _compare_dict(act_prices, exp_prices, tolerance_percent=tolerance_percent, tolerance_fields=price_fields)
        compare_res = res_dict["res"]

        if compare_res:
            # result is passed with tolerance, replaced updated price back to noti string
            actual = normalize_noti_prices(actual, exp_prices, decimal)
            expected = normalize_noti_prices(expected, exp_prices, decimal)

    # report result via pytest-check
    return _soft_assert(actual, expected, error_message=error_message)

