from typing import Any

from src.core.driver.web_driver import WebDriver
from src.data.data_runtime import DataRuntime
from src.utils.logging_utils import logger


class DriverManager:
    driver_list = []

    @classmethod
    def get_driver(cls) -> Any:
        """
        Get a driver instance for the specified platform.
        """
        platform = DataRuntime.option.platform
        match platform.lower():
            case "web" | "web-app":
                _driver = WebDriver.init_driver()
                cls.driver_list.append(_driver)

                return _driver

            case "ios":
                # to be defined
                return None

            case "android":
                # to be defined
                return None

            case _:
                raise ValueError(f"Invalid platform: {platform}")

    @classmethod
    def quit_driver(cls):
        platform = DataRuntime.option.platform

        match platform.lower():
            case "web" | "web-app":
                WebDriver.quit()

            case "ios":
                ...

            case "android":
                ...

            case _:
                logger.warning(f"- Invalid platform provided: {platform!r}")
