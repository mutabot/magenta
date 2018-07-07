import json
import random
import threading
import time
import traceback

from tornado import gen

from core import DataDynamo
from core.data_base import DataBase
from core.model.model import HashItem, RootAccount, Link, SocialAccount
from core.schema import S1
from providers.bitly_short import BitlyShorten
from providers.google_poll import GooglePollAgent
from providers.google_rss import GoogleRSS
from utils import config


class Poller(object):
    def __init__(self, logger, name, data, providers, config_path, dummy=False):
        """
        @type data: DataDynamo
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
        self.shortener = BitlyShorten(logger, config_path)

        self.gid_poll_s = cfg['gid_poll_s'] if 'gid_poll_s' in cfg else self.gid_poll_s
        self.period_s = cfg['period_s'] if 'period_s' in cfg else self.period_s
        self.workers_min = cfg['workers_min'] if 'workers_min' in cfg else self.workers_min
        self.workers_max = cfg['workers_max'] if 'workers_max' in cfg else self.workers_max

        self.google_poll = GooglePollAgent(logger, data, config_path)

    @gen.coroutine
    def run(self, *args, **kwargs):
        info = [config.version, self.name, self.gid_poll_s, self.period_s]
        self.logger.info('Poller(d) v[{0}], name=[{1}], poll delay=[{2}]s, period=[{3}]s starting...'.format(*info))

        random.seed(time.time())

        exit_flag = threading.Event()
        fail_count = 0
        while not exit_flag.wait(timeout=1):
            # noinspection PyBroadException
            try:
                yield self.poll()
            except Exception as ex:
                exception_info = traceback.format_exc()
                self.logger.error('Unable to retrieve next item to poll. Dynoris offline? {0}'.format(exception_info))
                fail_count += 1
                wait_s = 2 ^ fail_count  # XOR here
                self.logger.info('Waiting {0} seconds...'.format(wait_s))
                yield gen.sleep(wait_s)

    @gen.coroutine
    def poll(self):
        next_gid_bag = yield self.data.poll()

        if not next_gid_bag:
            # nothing to poll -- waiting
            sleep_sec = self.period_s + (random.randint(2, 4) * 0.1)
            self.logger.info('No items to poll, waiting {0}s'.format(sleep_sec))
            yield gen.sleep(sleep_sec)

        else:
            # fetch the document from the provider (google)
            item = json.loads(next_gid_bag)
            next_gid = HashItem.split_key(item["AccountKey"])[1]
            owner = item["OwnerKey"]
            cached_map = item["ActivityMap"] if "ActivityMap" in item and item["ActivityMap"] else {}
            cached_stamp = item["Updated"] if "Updated" in item else None

            now = int(time.time())
            minute_start_s, updates_in_range = self.count_updates_80(cached_map, now)
            next_poll = now + (self.gid_poll_s if updates_in_range else self.gid_poll_s * 3)

            self.logger.info('Polling {0}, next poll {1}'.format(next_gid, time.ctime(next_poll)))
            try:
                new_document = self.google_poll.poll(next_gid)

                # compare with the existing document
                new_stamp = GoogleRSS.get_update_timestamp(new_document)
                notify = cached_stamp != new_stamp
                # TODO: add etag comparison
                notify = True
                if notify:
                    cached_map[minute_start_s] = cached_map[minute_start_s] + 1 if minute_start_s in cached_map else 1

                    source = SocialAccount(owner, "google", next_gid)
                    # enqueue the next poll first
                    yield self.data.cache_provider_doc(
                        source,
                        new_document,
                        cached_map,
                        next_poll)

                    self.logger.info('{0}: notifying publishers...'.format(next_gid))

                    # TODO: notify publishers
                    yield self._process_new_document(source, new_document, cached_stamp)

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
        updates_in_range = sum([cached_map[str(m)] for m in minute_range if str(m) in cached_map]) if cached_map else 0
        return str(minute_start % 144), updates_in_range

    @gen.coroutine
    def _process_new_document(self, source, activities_doc, last_updated):
        """

        @type source: SocialAccount
        """
        # load the owner record
        root = yield self.data.load_account_async(source.owner)  # type: RootAccount

        account = DataDynamo.get_account(root, source.Key)  # type: SocialAccount

        # shorten reshares urls
        items = GoogleRSS.get_updated_since(activities_doc, last_updated)
        shorten = account.options[S1.cache_shorten_urls()] if S1.cache_shorten_urls() in account.options else False

        urls = set([item for item in items if shorten or GoogleRSS.get_item_is_share(item)
                    for item in GoogleRSS.get_long_urls(item)])

        for url in urls:
            u = self.data.cache.get_short_url(url)
            if not u:
                u = self.shortener.get_short_url(url)
                self.data.cache.cache_short_url(url, u)

        # notify publishers
        destinations = (DataBase.long_provider(Link.split_key(link.target)[0]) for link in root.links.itervalues())

        for provider in destinations:
            # must send root account and account triggered the update
            self.data.pubsub.broadcast_command(S1.publisher_channel_name(provider), S1.msg_publish(), root.account.pid, account.pid)
            self.logger.info('Notified: {0}'.format(provider))
