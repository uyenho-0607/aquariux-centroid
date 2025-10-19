import logging

import pytest

from src.data.data_runtime import DataRuntime
from src.utils.logging_utils import logger, setup_logging


def pytest_addoption(parser):
    parser.addoption("--env", action="store", default="sit")
    parser.addoption("--source", action="store", default="centroid", choices=["centroid", "metatrader"])
    parser.addoption("--client", action="store", default="", help="client to test")
    parser.addoption("--server", action="store", default="mt5", help="specific server when source is metatrader")
    parser.addoption("--account", action="store", default="live", help="")
    parser.addoption("--user", action="store", default="", help="user to test")
    parser.addoption("--password", action="store", default="", help="password of the user")
    parser.addoption("--url", action="store", default="", help="custom url of the tenant to test")
    parser.addoption("--debuglog", action="store_true", help="enable debug logging")
    parser.addoption("--cd", action="store_true", help="Whether is run on argo CD")
    parser.addoption("--browser", action="store", default="chrome")
    parser.addoption("--headless", action="store_true")


def pytest_configure(config):
    ...


def pytest_sessionstart(session):
    """Initialize configuration and logging."""
    opts = vars(session.config.option)
    setup_logging(log_level=logging.DEBUG if opts["debuglog"] else logging.INFO)
    
    DataRuntime.initialize(session)
    
    logger.info("=" * 60)
    logger.info(f"Env: {DataRuntime.config.env} | Source: {DataRuntime.config.source}")
    logger.info("=" * 60)
    


def pytest_collection_modifyitems(session, config, items):
    ...


def pytest_runtest_setup(item):
    ...


def pytest_runtest_teardown(item):
    ...

def pytest_sessionfinish(session, exitstatus):
    ...


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    return outcome


def pytest_terminal_summary(terminalreporter):
    ...
