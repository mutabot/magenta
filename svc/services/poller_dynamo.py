import random
import threading
import time
from decimal import Decimal

from core import DataDynamo
from providers.google_poll import GooglePollAgent
from utils import config


class Poller(object):
    def __init__(self, logger, name, data, providers, config_path, dummy=False):
        """
        @param logger:
        @param name:
        @param data:
        @param providers:
        @param config_path:
        @param dummy:
        """
        cfg = config.load_config(config_path, 'poller.json')

        self.logger = logger
        self.name = name
        self.data = data

        self.gid_poll_s = cfg['gid_poll_s'] if 'gid_poll_s' in cfg else self.gid_poll_s
        self.period_s = cfg['period_s'] if 'period_s' in cfg else self.period_s
        self.workers_min = cfg['workers_min'] if 'workers_min' in cfg else self.workers_min
        self.workers_max = cfg['workers_max'] if 'workers_max' in cfg else self.workers_max

        self.google_poll = GooglePollAgent(logger, data, config_path)

    def run(self, *args, **kwargs):
        info = [config.version, self.name, self.gid_poll_s, self.period_s]
        self.logger.info('Poller(d) v[{0}], name=[{1}], poll delay=[{2}]s, period=[{3}]s starting...'.format(*info))

        random.seed(time.time())

        exit_flag = threading.Event()
        while not exit_flag.wait(timeout=1):
            self.poll()

    def poll(self):

        next_gid = self.data.poll()

        if not next_gid:
            sleep_sec = self.period_s + (random.randint(2, 4) * 0.1)
            self.logger.info('No items to poll, waiting {0}s'.format(sleep_sec))
            time.sleep(sleep_sec)
        else:
            self.logger.info('Polling {0}'.format(next_gid))
            try:
                document = self.google_poll.fetch(next_gid)
                if self.data.cache_activities_doc(next_gid, document, self.gid_poll_s / 3.0):
                    # TODO: build user activity map and notify publishers
                    self.logger.info('{0}: notifying publishers (dummy)'.format(next_gid))
                else:
                    self.logger.info('{0}: Same document, no-op'.format(next_gid))
            except Exception as ex:
                self.logger.info('{0}: Poll failed {1}'.format(next_gid, ex.message))
