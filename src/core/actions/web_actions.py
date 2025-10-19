import builtins
import time
from typing import Literal

from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.core.actions.base_actions import BaseActions
from src.core.decorators import handle_stale_element
from src.core.softcheck import assert_equal
from src.data.consts import EXPLICIT_WAIT
from src.utils.logging_utils import logger


class WebActions(BaseActions):
    def __init__(self, driver=None):
        super().__init__(driver or builtins.web_driver)
        self._action_chains = ActionChains(self._driver)

    # ------- ACTIONS ------ #
    def _send_keys(self, value, locator: tuple[str, str] = None, element=None, timeout=EXPLICIT_WAIT):
        if locator:
            element = self.find_element(locator, timeout)

        if element:
            self._action_chains.double_click(element).perform()
            element.send_keys(str(value))

    @handle_stale_element
    def send_keys(self, locator, value, use_action_chain=False, timeout=EXPLICIT_WAIT):

        max_retries = 3
        element = self.find_element(locator, timeout)

        self._action_chains.double_click(element).perform()
        element.send_keys(str(value))

        # Fall back
        sent_value = element.get_attribute("value")

        while str(sent_value) != str(value) and max_retries:
            max_retries -= 1

            logger.warning(f"> Sent value: {sent_value} != Input value: {value}. Retry sending: {value!r}")
            self._action_chains.double_click(element).perform()
            element.send_keys(str(value))

            sent_value = element.get_attribute("value")
            logger.debug(f"> Resent value: {sent_value!r}")

    @handle_stale_element
    def click_by_offset(
            self,
            locator: tuple[str, str],
            x_offset=0, y_offset=0,
            timeout=EXPLICIT_WAIT,
            raise_exception=True,
            show_log=True
    ) -> None:
        """Click on an element by an offset of x and y coordinates."""
        element = self.find_element(
            locator, timeout, EC.element_to_be_clickable,
            raise_exception=raise_exception,
            show_log=show_log
        )
        if element:
            self._action_chains.move_to_element_with_offset(element, x_offset, y_offset).click().perform()

    @handle_stale_element
    def get_value(
            self,
            locator: tuple[str, str],
            timeout=EXPLICIT_WAIT,
    ) -> str:
        """Get value from an element."""
        element = self.find_element(locator, timeout, raise_exception=False, show_log=False)
        res = element.get_attribute("value") if element else ""
        return res

    def goto(self, url):
        """Navigate to a URL and wait for the page to be fully loaded."""
        self._driver.get(url)

    def refresh(self):
        self._driver.refresh()

    def get_current_url(self):
        return self._driver.current_url

    def scroll_to_element(self, locator: tuple[str, str], timeout=EXPLICIT_WAIT):
        element = self.find_element(locator, timeout)
        self._driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)

    def scroll_picker_down(self, locator: tuple[str, str], timeout=EXPLICIT_WAIT):
        wheel = self.find_element(locator, timeout)
        self._action_chains.click_and_hold(wheel).move_by_offset(0, -50).release().pause(0.5).perform()

    def scroll_container_down(self, locator: tuple[str, str], scroll_step: float = 0.5):
        """Scroll a container element down by a smaller step to avoid missing items"""
        try:
            container = self.find_element(locator)
            self._driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollTop + (arguments[0].clientHeight * arguments[1]);",
                container, scroll_step
            )
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Error scrolling container {locator}: {e}")

    def drag_element_horizontal(self, locator: tuple[str, str], direction: Literal["left", "right"] | str = "left", timeout=EXPLICIT_WAIT):
        x_offset = -200 if direction == "left" else 200

        element = self.find_element(locator, timeout)
        if element:
            finger = PointerInput("touch", "finger")
            action = ActionBuilder(self._driver, mouse=finger)
            action.pointer_action.move_to(element)
            action.pointer_action.pointer_down()
            action.pointer_action.move_by(x=x_offset, y=0)
            action.pointer_action.pointer_up()
            action.perform()

    def wait_for_url(self, url: str, timeout: int = EXPLICIT_WAIT):
        """Wait for the current URL to match the expected URL with retry mechanism."""
        wait = self._wait if timeout == EXPLICIT_WAIT else WebDriverWait(self._driver, timeout)
        try:
            wait.until(EC.url_to_be(url))
            return self._driver.current_url

        except TimeoutException as e:
            logger.warning(f"URL does not match after {timeout}(sec) '{url}': {type(e).__name__}")

        except Exception as e:
            logger.error(f"Unexpected error for URL '{url}': {type(e).__name__}")

        return self._driver.current_url

    def switch_to_iframe(self):
        iframe = self._wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        self._driver.switch_to.frame(iframe)

    def switch_to_default(self):
        self._driver.switch_to.default_content()

    # ------- VERIFY ------ #

    def verify_site_url(self, expected_url: str, timeout: int = EXPLICIT_WAIT):
        """Verify that the current URL matches the expected URL"""
        actual_url = self.wait_for_url(expected_url, timeout)
        assert_equal(actual_url, expected_url)
