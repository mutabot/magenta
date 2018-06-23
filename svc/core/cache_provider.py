import json
import urllib

from tornado.httpclient import HTTPRequest

from core.model.schema2 import S2
from dynoris_client import DynorisClient
from dynoris_client.models import CacheItemRequest


class CacheProvider(object):
    def __init__(self, dynoris_url):
        self.poll_table_name = 'GidSet'
        self.poll_table_index_name = 'PollIndex'

        # self.http_client = AsyncHTTPClient()
        self.dynoris_client = DynorisClient(dynoris_url)

    # @staticmethod
    # def get_cache_request(endpoint, root_key, cache_key, table):
    #     req_body = {
    #         "Table": table,
    #         "CacheKey": cache_key,
    #         "HashKey": "Key",
    #         "StoreKey": [{"Item1": "AccountKey", "Item2": root_key}]
    #     }
    #     return HTTPRequest(
    #         "http://localhost:4999/api/Dynoris/{0}".format(endpoint),
    #         "POST",
    #         headers={
    #             "Content-Type": "application/json"
    #         },
    #         body=json.dumps(req_body),
    #         request_timeout=120
    #     )
#
    # @staticmethod
    # def get_commit_request(hash_key, hash_data_key=None):
    #     return HTTPRequest(
    #         "http://localhost:4999/api/Dynoris/CommitItem/{0}/{1}".format(urllib.quote_plus(hash_key), urllib.quote_plus(hash_data_key or hash_key)),
    #         "GET",
    #         request_timeout=120
    #     )
#
    def cache_object(self, key, object_name):
        cache_key = "{0}:{1}".format(key, object_name)
        # req = self.get_cache_request("CacheHash", key, cache_key, object_name)
        req = CacheItemRequest(cache_key, object_name, [{"Item1": "AccountKey", "Item2": key}], hash_key="Key")
        self.dynoris_client.cache_hash(req)

    def commit_object(self, key, object_name):
        cache_key = "{0}:{1}".format(key, object_name)
        self.dynoris_client.commit_item(cache_key, cache_key)

    def cache_poll_item(self, key):
        cache_key = S2.cache_key(self.poll_table_name, key)
        store_key = [
            {"Item1": "AccountKey", "Item2": key}
        ]

        self.dynoris_client.cache_item(
            req={
                "Table": self.poll_table_name,
                "CacheKey": cache_key,
                "StoreKey": store_key
            }
        )

        return cache_key

    def commit_item(self, cache_key):
        r = self.dynoris_client.commit_item(cache_key, cache_key)
        return json.loads(r) if r else None

    def get_next_expired(self, now):
        r1 = self.dynoris_client.expire_next(
            req={
                "Table": self.poll_table_name,
                "Index": self.poll_table_index_name,
                "StoreKey": [{"Item1": "Active", "Item2": "Y"}],
                "StampKey": {"Item1": "Expires", "Item2": "{0}".format(now)}
            }
        )
        # the response is a list of jsons
        return r1
