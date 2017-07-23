import json
import logging
from logging import handlers
import os

version = '8.8'

DEFAULT_FORCE_MISS_TIMEOUT = 20
DEFAULT_ORPHANED_TIMEOUT = 3600  # 1 hr timeout
DEFAULT_MAX_ERROR_COUNT = 7  # max number of errors before crosspost is disabled

DEFAULT_MAX_RESULTS = 10  # max items to fetch from google
DEFAULT_MAX_RESULTS_MAP = 128  # max items to keep history of
DEFAULT_MIN_TIME_SPACE = 5  # minimum post time-space in minutes

DEFAULT_LOG_LEN = 20

USER_ID_COOKIE_NAME = 'mr_siid_u'
USER_SESSION_COOKIE_NAME = 'mr_siid_t'


def getLogHandler(file_name):
    channel = handlers.RotatingFileHandler(file_name, maxBytes=2621440, backupCount=5)
    channel.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t[%(message)s]", "%Y-%m-%d %H:%M:%S"))
    return channel


def get_logger(log_path, name):
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.addHandler(getLogHandler(os.path.join(log_path, name + '.log')))
    logger.level = logging.DEBUG
    return logger


def load_config(config_path, config_name):
    f_meta = file(os.path.join(config_path, config_name), 'rb')
    data = json.load(f_meta)
    return data
