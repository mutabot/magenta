from tornado import gen

from core.model.schema2 import S2
from dynoris_api import DynorisApi, ApiClient, Configuration, ExpiringStampApi
from dynoris_api.models import CacheItemRequest, ExpiringStampRequest


class CacheProvider(object):
    def __init__(self, dynoris_url):
        self.base_url = dynoris_url
        self.poll_table_name = 'GidSet'
        self.poll_table_index_name = 'PollIndex'

        configuration = Configuration()
        configuration.host = dynoris_url
        self.dynoris_poll_client = ExpiringStampApi(ApiClient(configuration))
        self.dynoris_client = DynorisApi(ApiClient(configuration))

    @gen.coroutine
    def cache_object(self, key, object_name):
        cache_key = "{0}:{1}".format(key, object_name)
        req = CacheItemRequest(cache_key, object_name, [{"Item1": "AccountKey", "Item2": key}], hash_key="Key")
        yield self.dynoris_client.cache_hash(req=req)

    @gen.coroutine
    def cache_poll_item(self, key):
        cache_key = S2.cache_key(self.poll_table_name, key)
        store_key = [
            {"Item1": "AccountKey", "Item2": key}
        ]

        req = CacheItemRequest(cache_key=cache_key, table=self.poll_table_name, store_key=store_key)
        yield self.dynoris_client.cache_item(req=req)

        raise gen.Return(cache_key)

    @gen.coroutine
    def remove_poll_item(self, key):
        # cache item first as dynoris needs up do date item before deletion
        yield self.cache_poll_item(key)

        # ask to remove the item
        cache_key = S2.cache_key(self.poll_table_name, key)
        yield self.dynoris_client.delete_item(cache_key=cache_key)
        raise gen.Return(cache_key)

    @gen.coroutine
    def commit_object(self, key, object_name):
        cache_key = "{0}:{1}".format(key, object_name)
        yield self.commit_item(cache_key, cache_key)

    @gen.coroutine
    def commit_item(self, cache_key, update_key):
        yield self.dynoris_client.commit_item(cache_key, update_key)
        # raise gen.Return(r)

    @gen.coroutine
    def delete_item(self, cache_key, update_key):
        yield self.dynoris_client.delete_item(cache_key)
        # raise gen.Return(r)

    @gen.coroutine
    def get_next_expired(self, now):
        req = ExpiringStampRequest(
            table=self.poll_table_name,
            index=self.poll_table_index_name,
            store_key=[{"Item1": "Active", "Item2": "Y"}],
            stamp_key={"Item1": "Expires", "Item2": "{0}".format(now)})
        r1 = yield self.dynoris_poll_client.expire_next(req=req)
        raise gen.Return(r1)
