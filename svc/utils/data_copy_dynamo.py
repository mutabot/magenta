import time
from logging import Logger

from tornado import gen

import core
from core.cache_provider import CacheProvider
from core.model import SocialAccount
from services.poller_dynamo import Poller
from utils.data_model import DataCopyModel


class DataCopyDynamo(object):
    def __init__(self, log, data, data_d=None, gid=None):
        """
        @type log: Logger
        @type data: core.Data
        @type data_d: core.DataInterface
        """
        self.gid = gid
        self.data = data
        self.data_d = data_d
        self.log = log
        self.model = DataCopyModel(log, data)
        self.cache = CacheProvider(data_d.dynoris_url)

    @gen.coroutine
    def run(self):
        if self.gid:
            yield self.dump_gid(self.gid)
        else:
            yield self.dump_gids()

    @gen.coroutine
    def dump_gids(self):
        total = 0
        c = self.data.scan_gid()
        while len(c) > 1 and c[1]:
            total += len(c[1])
            for gid in c[1]:
                yield self.dump_gid(gid)

            # check if the next cursor is zero
            if c[0] == '0' or c[0] == 0:
                break

            # grab next set
            c = self.data.scan_gid(c[0])
            # if total > 20:
            #    break

        self.log.info('End of gid_set, total [{0}] GIDs.'.format(total))

    @gen.coroutine
    def dump_gid(self, root_gid):
        self.log.info('Dumping user, GID: {0}'.format(root_gid))
        yield self.migrate_records(root_gid)

    def migrate_cache(self, root_account):
        pid = root_account.account.pid
        # get child bindings for this account
        children = set(self.data.get_sources(pid))

        # just to be safe
        children.add(pid)
        for child in children:
            self.log.info('Copying cache [{0}:{1}]...'.format(pid, child))

            doc = self.data.get_activities(child)
            cached_map = self.data.cache.get_activity_update_map(child)
            if doc is None and pid == child:
                self.log.info('Empty cache and self master, skipped: {0}'.format(child))
                continue

            if doc:
                now = time.time()
                minute_start_s, updates_in_range = Poller.count_updates_80(cached_map, now)
                next_poll = now + (600 if updates_in_range else 600 * 3)

                self.log.info('Storing {0}, next poll {1}'.format(child, time.ctime(next_poll)))

                self.data_d.cache_provider_doc(SocialAccount("google", child), doc, cached_map)

    @gen.coroutine
    def migrate_records(self, root_gid):

        # verify
        # acc = yield self.data_d.load_account_async(root_gid)

        root = self.model.get_root_account_model(root_gid)

        # migrate google poll cache
        self.migrate_cache(root)

        # write links, logs, and accounts to dynamo
        self.log.info("Caching logs...")
        yield self.cache.cache_object(root.Key, "Logs")
        self.data_d.set_model_document("Logs", root.Key, root.logs)
        yield self.cache.commit_object(root.Key, "Logs")

        self.log.info("Caching links...")
        yield self.cache.cache_object(root.Key, "Links")
        self.data_d.set_model_document("Links", root.Key, root.links)
        yield self.cache.commit_object(root.Key, "Links")

        self.log.info("Caching accounts...")
        yield self.cache.cache_object(root.Key, "Accounts")
        self.data_d.set_model_document("Accounts", root.Key, root.accounts)
        yield self.cache.commit_object(root.Key, "Accounts")

        self.log.info("All done.")
