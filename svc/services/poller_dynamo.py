import json
import random
import threading
import time

from core.model import SocialAccount
from core.model.model import HashItem
from providers.google_poll import GooglePollAgent
from providers.google_rss import GoogleRSS
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
            cached_map = item["ActivityMap"] if "ActivityMap" in item else {}
            cached_stamp = item["Updated"] if "Updated" in item else None

            now = int(time.time())
            minute_start_s, updates_in_range = self.count_updates_80(cached_map, now)
            next_poll = now + (self.gid_poll_s if updates_in_range else self.gid_poll_s * 3)

            self.logger.info('Polling {0}, next poll {1}'.format(next_gid, time.ctime(next_poll)))
            try:
                new_document = self.google_poll.fetch(next_gid)

                # compare with the existing document
                new_stamp = GoogleRSS.get_update_timestamp(new_document)
                notify = cached_stamp != new_stamp

                if notify:
                    cached_map[minute_start_s] = cached_map[minute_start_s] + 1 if minute_start_s in cached_map else 1

                # enqueue the next poll first
                self.data.cache_provider_doc(
                    SocialAccount("google", next_gid),
                    new_document,
                    cached_map,
                    next_poll)

                # notify if needed
                if notify:
                    self.logger.info('{0}: notifying publishers (dummy)'.format(next_gid))
                else:
                    self.logger.info('{0}: Same document, no-op'.format(next_gid))

            except Exception as ex:
                self.logger.info('{0}: Poll failed {1}'.format(next_gid, ex.message))

    @staticmethod
    def count_updates_80(cached_map, now):
        # ActivityMap is a 10 minute interval map
        # use 80 minute window to deduce the next poll wait time
        minute_start = int(now) / 600
        minute_range = [m % 144 for m in range(minute_start - 4, minute_start + 4)]
        updates_in_range = sum([cached_map[str(m)] for m in minute_range if str(m) in cached_map])
        return str(minute_start % 144), updates_in_range
