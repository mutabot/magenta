import json
import random
import threading
import time

from core.model import SocialAccount
from core.model.model import HashItem
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
        fail_count = 0
        while not exit_flag.wait(timeout=1):
            # noinspection PyBroadException
            try:
                self.poll()
            except:
                self.logger.error('Unable to retrieve next item to poll. Dynoris offline?')
                fail_count += 1
                wait_s = 2 ^ fail_count  # XOR here
                self.logger.info('Waiting {0} seconds...'.format(wait_s))
                time.sleep(wait_s)

    def poll(self):
        next_gid_bag = self.data.poll()

        if not next_gid_bag:
            sleep_sec = self.period_s + (random.randint(2, 4) * 0.1)
            self.logger.info('No items to poll, waiting {0}s'.format(sleep_sec))
            time.sleep(sleep_sec)
        else:


            item = json.loads(next_gid_bag)
            next_gid = HashItem.split_key(item["AccountKey"])[1]
            activity_map = item["ActivityMap"] if "ActivityMap" in item else None

            now = time.time()
            minute = (now / 60) % 1440
            next_poll = now + (self.gid_poll_s if activity_map and minute in activity_map else self.gid_poll_s * 3)

            self.logger.info('Polling {0}, next poll {1}'.format(next_gid, time.ctime(next_poll)))
            try:
                document = self.google_poll.fetch(next_gid)
                if self.data.cache_provider_doc(
                        SocialAccount("google", next_gid),
                        document,
                        activity_map,
                        next_poll):
                    # build user activity map and notify publishers

                    if minute in activity_map:
                        activity_map[minute] += 1
                    else:
                        activity_map[minute] = 1

                    # second update to persist the updated activity map
                    self.data.cache_provider_doc(
                        SocialAccount("google", next_gid),
                        document,
                        activity_map,
                        next_poll)
                    self.logger.info('{0}: notifying publishers (dummy)'.format(next_gid))
                else:
                    self.logger.info('{0}: Same document, no-op'.format(next_gid))
            except Exception as ex:
                self.logger.info('{0}: Poll failed {1}'.format(next_gid, ex.message))
