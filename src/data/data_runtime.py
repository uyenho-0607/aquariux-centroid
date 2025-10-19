import yaml
from allure_commons.utils import now

from src.utils import DotDict


class DataRuntime:
    """Single source of truth for configuration and runtime options."""
    config = DotDict()  # From YAML
    option = DotDict()  # From CLI

    @classmethod
    def initialize(cls, pytest_session):
        """Load configuration from YAML and CLI options."""
        from src.data.consts import CONFIG_DIR

        cli = vars(pytest_session.config.option)
        cls.option = DotDict(cli)

        # Load YAML
        env = cli['env']
        source = cli['source']
        client = cli['client'] or ('main' if source == 'centroid' else 'lirunex')

        config_path = CONFIG_DIR / f"{env}.yaml"
        with open(config_path) as f:
            yaml_data = yaml.safe_load(f)

        # Extract client config
        client_config = yaml_data.get(source, {}).get(client, {})

        # Build config
        config = DotDict()
        config.env = env
        config.source = source
        config.client = client
        config.base_url = cli.get('url') or client_config.get('base_url', '')
        config.app_package = client_config.get('app_package', '')
        config.app_bundle = client_config.get('app_bundle', '')

        # Extract credentials
        if cli.get('user'):
            config.user = cli['user']
            config.password = cli.get('password', '')
        else:
            creds = client_config.get('credentials', {})
            account = cli.get('account', 'live')

            if source == "centroid":
                config.user = creds.get('user', '')
            else:  # metatrader
                server = cli.get('server', 'mt5')
                config.user = creds.get(server, {}).get(account, '')
                config.server = server
                config.account = account

            # Get password
            config.password = yaml_data.get('password_crm' if account == 'crm' else 'password', '')

        cls.config = config

    @classmethod
    def is_centroid(cls):
        return cls.config.source == "centroid"

    @classmethod
    def is_mt4(cls):
        ...

    @classmethod
    def is_multi_oms(cls):
        from src.data.consts import MULTI_OMS
        return cls.config.client in MULTI_OMS


# handle save steps information
class StepLogs:
    steps_with_time = {}
    test_steps = []
    setup_steps = dict()
    teardown_steps = dict()
    broken_steps = []
    all_failed_logs = []
    failed_logs_dict = {}

    TEST_ID = ""

    @classmethod
    def init_test_logs(cls):
        cls.steps_with_time[cls.TEST_ID] = []
        cls.failed_logs_dict[cls.TEST_ID] = []

    @classmethod
    def add_step(cls, msg_log):
        cls.test_steps.append(msg_log)
        cls.steps_with_time[cls.TEST_ID].append((msg_log, now()))

    @classmethod
    def add_setup_step(cls, msg_log):
        cls.setup_steps |= msg_log

    @classmethod
    def add_teardown_step(cls, msg_log):
        cls.teardown_steps |= msg_log

    @classmethod
    def add_failed_log(cls, msg_log, failed_detail=""):
        cls.all_failed_logs.append((msg_log, failed_detail))
        cls.failed_logs_dict[cls.TEST_ID].append((msg_log, failed_detail))
