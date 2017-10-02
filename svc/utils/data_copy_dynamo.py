import json
from logging import Logger

from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

import core
from core.model import SocialAccount
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
        self.http_client = AsyncHTTPClient()

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
        # get child bindings for this account
        children = set(self.data.get_sources(root_account.pid))

        # just to be safe
        children.add(root_account.pid)
        for child in children:
            self.log.info('Copying cache [{0}:{1}]...'.format(root_account.pid, child))

            doc = self.data.get_activities(child)
            if doc is None and root_account.pid == child:
                self.log.info('Empty cache and self master, skipped: {0}'.format(child))
                return

            if doc:
                self.data_d.cache_provider_doc(SocialAccount("google", child), doc, -1.0)

    @gen.coroutine
    def migrate_records(self, root_gid):
        root = self.model.get_root_account_model(root_gid)

        # migrate google poll cache
        self.migrate_cache(root)

        # write links, logs, and accounts to dynamo
        self.log.info("Caching logs...")
        yield self.commit_object(root.Key, root.log, "Logs")

        self.log.info("Caching links...")
        yield self.commit_object(root.Key, root.links, "Links")

        self.log.info("Caching accounts...")
        yield self.commit_object(root.Key, root.accounts, "Accounts")

        self.log.info("All done.")

    @gen.coroutine
    def commit_object(self, key, obj, object_name):
        cache_key = "{0}:{1}".format(key, object_name.lower())
        req = self.get_cache_request("CacheHash", key, cache_key, object_name)
        yield self.http_client.fetch(req)

        self.data_d.set_model_document(object_name.lower(), key, obj)

        req = self.get_commit_request(cache_key)
        yield self.http_client.fetch(req)

    @staticmethod
    def get_cache_request(endpoint, root_key, cache_key, table):
        req_body = {
            "Table": table,
            "CacheKey": cache_key,
            "HashKey": "Key",
            "StoreKey": [{"Item1": "AccountKey", "Item2": root_key}]
        }
        return HTTPRequest(
            "http://localhost:4999/api/Dynoris/{0}".format(endpoint),
            "POST",
            headers={
                "Content-Type": "application/json"
            },
            body=json.dumps(req_body),
            request_timeout=120
        )

    @staticmethod
    def get_commit_request(hash_key):
        return HTTPRequest(
            "http://localhost:4999/api/Dynoris/CommitItem",
            "POST",
            headers={
                "Content-Type": "application/json"
            },
            body=json.dumps(hash_key),
            request_timeout=120
        )
