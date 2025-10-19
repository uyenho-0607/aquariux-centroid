import functools
import inspect
import json
import operator
import time

import requests
from selenium.common import StaleElementReferenceException, ElementNotInteractableException, \
    ElementClickInterceptedException

from src.data.consts import WARNING_ICON, FAILED_ICON
from src.data.data_runtime import StepLogs
from src.utils.allure_utils import attach_verify_table, log_verification_result, attach_screenshot
from src.utils.format_utils import format_request_log
from src.utils.logging_utils import logger


def attach_table_details(func):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        __tracebackhide__ = True

        # Use inspect to get all function parameters including defaults
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()  # This applies default values
        all_args = bound_args.arguments

        actual, expected, *_ = args

        # Store the comparison result if it's returned by the function
        comparison_result = None

        # Call the function and capture any returned comparison result
        result = func(*args, **kwargs)

        # Check if the function returned a comparison result (for soft_assert)
        if isinstance(result, dict) and "res" in result and "diff" in result:
            comparison_result = result

        if all([isinstance(actual, dict), isinstance(expected, dict)]):

            # Handle contains check using assert_op
            assert_op = all_args.get("assert_op", operator.eq)
            if assert_op == operator.contains:
                actual = {k: v for k, v in actual.items() if k in expected}

            title = "Verify Table Details"
            if StepLogs.test_steps:
                title += f" - {StepLogs.test_steps[-1]}"

            # Get tolerance info - check both tolerance_percent and tolerance_map
            tolerance_pct = kwargs.get("tolerance_percent")
            tolerance_map = kwargs.get("tolerance_map")
            
            # If tolerance_map is provided, extract a representative tolerance value
            if tolerance_pct is None and tolerance_map:
                # Use the first tolerance value from map as representative
                tolerance_pct = next(iter(tolerance_map.values())) if tolerance_map else None
            
            attach_verify_table(
                actual, expected,
                tolerance_percent=tolerance_pct,
                tolerance_fields=kwargs.get("tolerance_fields"),
                title=title,
                comparison_result=comparison_result
            )

        elif all_args.get("log_details"):
            name = "Verification Details"
            if StepLogs.test_steps:
                name += f" - {StepLogs.test_steps[-1]}"
            log_verification_result(
                actual, expected, result, desc=all_args.get("desc", "") + all_args.get("err_msg", "") if not result else "", name=name
            )
        
        return result

    return _wrapper


def attach_verify_logs():
    ...

def handle_stale_element(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        __tradebackhide__ = True

        # Use inspect to get all function parameters including defaults
        sig = inspect.signature(func)
        bound_args = sig.bind(self, *args, **kwargs)
        bound_args.apply_defaults()  # This applies default values
        all_args = bound_args.arguments

        max_retries = 3
        raise_exception = all_args.get("raise_exception")

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                return func(self, *args, **kwargs)
            except (StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException) as e:

                if attempt < max_retries:
                    logger.warning(f"{WARNING_ICON} {type(e).__name__} for locator {args[0]} (attempt {attempt + 1}/{max_retries + 1}), retrying...")
                    continue

                else:
                    # Final attempt failed, re-raise the exception
                    logger.error(f"{type(e).__name__} for locator {args[0]} after {max_retries + 1} attempts")

                    if raise_exception and StepLogs.test_steps:
                        StepLogs.add_failed_log(StepLogs.test_steps[-1])
                        attach_screenshot(self._driver, name="broken")  # Capture broken screenshot

                        raise e
        return None

    return wrapper


def after_request(base_delay=1.0, max_delay=10.0, max_retries=3):
    """
    Decorator to handle API requests with optional retry logic.
    Args:
        base_delay (float): Base delay for exponential backoff.
        max_delay (float): Maximum delay between retries.
        max_retries (int): Maximum retry attempts.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            __tracebackhide__ = True

            # Extract optional arguments
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            all_args = bound_args.arguments

            # Get options with defaults
            apply_retries = all_args.get("apply_retries", True)
            fields_to_show = all_args.get("fields_to_show", None)
            parse_result = all_args.get("parse_result", True)
            truncate_len = all_args.get("truncate_len", 5)

            def _parse_result(resp):
                if not parse_result:
                    return resp

                try:
                    res = resp.json()
                    return res.get("result", res) if resp.text.strip() else []
                except (json.JSONDecodeError, AttributeError):
                    return getattr(resp, "text", resp)

            # Handle single request without retries
            if not apply_retries:
                response = func(self, *args, **kwargs)
                logger.debug(f"{format_request_log(response, log_resp=True, fields_to_show=fields_to_show, truncate_len=truncate_len)}")
                return _parse_result(response)

            # Handle requests with retries
            for attempt in range(max_retries):
                try:
                    response = func(self, *args, **kwargs)
                    logger.debug(f"{format_request_log(response, log_resp=True, fields_to_show=fields_to_show, truncate_len=truncate_len)}")

                    if response.ok:
                        return _parse_result(response)

                    # Handle failed response
                    if attempt == max_retries - 1:
                        error_msg = f"{FAILED_ICON} API request failed with status_code: {response.status_code} - {response.text.strip()}"
                        logger.error(error_msg)
                        raise requests.exceptions.RequestException(error_msg)

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}), status_code: {response.status_code} - {response.text.strip()}, retrying in {delay:2f}s...")
                    time.sleep(delay)

                except Exception as e:
                    # Handle exceptions during request
                    if attempt == max_retries - 1:
                        raise e

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}), retrying in {delay:.2f}s. Error: {e}")
                    time.sleep(delay)

            return None

        return wrapper

    return decorator
