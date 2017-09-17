import json
from logging import Logger

from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

import core
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
        self.migrate_cache(root_gid)
        yield self.migrate_records(root_gid)

    def migrate_cache(self, root_gid):
        # get child bindings for this account
        children = set(self.data.get_sources(root_gid))

        # just to be safe
        children.add(root_gid)
        for child in children:
            self.log.info('Copying cache [{0}:{1}]...'.format(root_gid, child))

            doc = self.data.get_activities(child)
            if doc is None and root_gid == child:
                self.log.info('Empty cache and self master, skipped: {0}'.format(child))
                return

            #self.data_d.register_gid(child)
            if doc:
                self.data_d.cache_activities_doc(child, doc, -1.0)

    @gen.coroutine
    def migrate_records(self, root_gid):
        root = self.model.get_root_account_model(root_gid)

        self.log.info("Caching links...")
        req = self.get_cache_request("CacheHash", root.pid, "{0}:{1}".format(root.pid, "links"), "Links", "key")
        yield self.http_client.fetch(req)

        self.data_d.set_model_document("links", root.pid, root.links)

        req = self.get_commit_request(root.pid, "links")
        yield self.http_client.fetch(req)

        self.log.info("Caching logs...")
        # write all to dynamo
        req = self.get_cache_request("CacheHash", root.pid, "{0}:{1}".format(root.pid, "logs"), "Logs", "key")
        yield self.http_client.fetch(req)

        self.data_d.set_log(root.pid, root.log)

        req = self.get_commit_request(root.pid, "logs")
        yield self.http_client.fetch(req)

        self.log.info("Caching accounts...")
        req = self.get_cache_request("CacheHash", root.pid, "{0}:{1}".format(root.pid, "accounts"), "Accounts", "key")
        yield self.http_client.fetch(req)

        self.data_d.set_model_document("accounts", root.pid, root.accounts)

        req = self.get_commit_request(root.pid, "accounts")
        yield self.http_client.fetch(req)

        self.log.info("All done.")

    @staticmethod
    def get_cache_request(endpoint, root_pid, cache_key, table, hash_key):
        req_body = {
            "Table": table,
            "CacheKey": cache_key,
            "HashKey": hash_key,
            "StoreKey": [{"Item1": "gid", "Item2": root_pid}]
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
    def get_commit_request(root_pid, hash_key):
        return HTTPRequest(
            "http://localhost:4999/api/Dynoris/CommitItem",
            "POST",
            headers={
                "Content-Type": "application/json"
            },
            body=json.dumps("{0}:{1}".format(root_pid, hash_key)),
            request_timeout=120
        )
