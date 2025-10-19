import builtins
import os

import boto3
from botocore.config import Config
from selenium import webdriver
from selenium.webdriver import ChromeOptions, FirefoxOptions, SafariOptions

from src.data.consts import WEB_APP_DEVICE
from src.data.data_runtime import DataRuntime

proxy_server = os.getenv('PROXY_SERVER')
project_arn = os.getenv('DF_PROJECT_ARN')


class WebDriver:
    _driver = None

    @classmethod
    def init_driver(cls):
        # get driver options
        browser = DataRuntime.option.browser
        headless = DataRuntime.option.headless
        cd = DataRuntime.option.cd

        match browser.lower():
            case "chrome":
                options = ChromeOptions()
                options.add_experimental_option('excludeSwitches', ['enable-logging', "enable-automation"])
                if DataRuntime.option.platform == 'web-app':
                    options.add_experimental_option("mobileEmulation", {"deviceName": WEB_APP_DEVICE})

                options.add_argument("--incognito")
                prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
                options.add_experimental_option("prefs", prefs)

                if headless:
                    options.add_argument("--headless")

                if cd:
                    options.add_argument(f"--proxy-server={proxy_server}")
                    options.set_capability("aws:maxDurationSecs", 2400)

                    config = Config(region_name='us-west-2', retries={'max_attempts': 10})
                    testgrid_url = os.getenv('TESTGRID_URL')

                    if testgrid_url is None:
                        devicefarm_client = boto3.client("devicefarm", config=config)
                        testgrid_url_response = devicefarm_client.create_test_grid_url(
                            projectArn=project_arn,
                            expiresInSeconds=86400
                        )
                        os.environ["TESTGRID_URL"] = testgrid_url_response['url']
                        testgrid_url = testgrid_url_response['url']

                    driver = webdriver.Remote(command_executor=testgrid_url, options=options)
                else:
                    driver = webdriver.Chrome(options=options)

            case "firefox":
                options = FirefoxOptions()
                if headless:
                    options.add_argument("--headless")
                driver = webdriver.Firefox(options=options)

            case "safari":
                options = SafariOptions()
                if headless:
                    options.add_argument("--headless")
                driver = webdriver.Safari(options=options)

            case _:
                raise ValueError(f"Invalid browser value: {browser!r} !!!")

        setattr(builtins, "web_driver", driver)
        driver.maximize_window()
        cls._driver = driver
        return driver

    @classmethod
    def quit(cls):
        if cls._driver:
            cls._driver.quit()
            cls._driver = None
