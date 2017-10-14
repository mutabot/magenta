import json
import time
import uuid
from decimal import Decimal

import jsonpickle
from python_http_client import Client

from core import provider_dynamo
from core.data_base import DataBase
from core.data_interface import DataInterface
from core.model import SocialAccount
from core.model.model import HashItem
from core.model.schema2 import S2
from providers.google_rss import GoogleRSS
from utils import config


class DataDynamo(DataBase, DataInterface):

    def commit_pid_records(self, root_pid):
        pass

    def cache_pid_records(self, root_pid):
        pass

    def get_accounts(self, root_pid, accounts):
        pass

    def add_log(self, gid, message):
        pass

    def set_links(self, root_pid, links):
        pass

    def flush(self, root_pid):
        pass

    def unregister_gid(self, gid):
        pass

    def remove_from_poller(self, gid):
        pass

    def is_loading(self):
        pass

    def __init__(self, logger, dynoris_url, redis_connection):
        DataInterface.__init__(self)
        DataBase.__init__(self,
                          logger,
                          redis_connection['host'],
                          redis_connection['port'],
                          redis_connection['db'])

        # stub for backward compatibility
        self.cache = self
        self.logger = logger
        self.dynoris_url = dynoris_url
        self.dynoris_client = Client(
            host=dynoris_url,
            request_headers={
                "Content-Type": "application/json"
            }
        )

        self.poll_table_name = 'GidSet'
        self.poll_table_index_name = 'PollIndex'

        self.provider = {
            'facebook': provider_dynamo.ProviderDynamo(self.rc, 'facebook'),
            'twitter': provider_dynamo.ProviderDynamo(self.rc, 'twitter'),
            'tumblr': provider_dynamo.ProviderDynamo(self.rc, 'tumblr'),
            'flickr': provider_dynamo.ProviderDynamo(self.rc, 'flickr'),
            '500px': provider_dynamo.ProviderDynamo(self.rc, '500px'),
            'linkedin': provider_dynamo.ProviderDynamo(self.rc, 'linkedin'),
        }

    def set_model_document(self, document_name, root_key, items):
        """
        Stores the items as a hash value in redis
        @type items: list of HashItem
        @param document_name: name of the items document
        @param root_key:
        @param items:
        @return:
        """
        key_name = S2.document_key_name(root_key, document_name)
        self.rc.delete(key_name)
        for item in items:
            js = jsonpickle.dumps(item)
            self.rc.hset(key_name, item.Key, js)

    def get_log(self, root_key):
        key_name = S2.document_key_name(root_key, "logs")
        log_raw = self.rc.hgetall(key_name)
        result = {key: json.loads(value)["Items"] for key, value in log_raw.iteritems()}
        return result

    def set_log(self, root_key, log):
        key_name = S2.document_key_name(root_key, "logs")
        self.rc.delete(key_name)
        for key, value in log.iteritems():
            self.rc.hset(key_name, key, json.dumps({"Items": value}))

    def register_gid(self, gid):
        # simply register for a poll
        self.cache_provider_doc(SocialAccount("google", gid), None, None)

    def cache_activities_doc(self, gid, activities_doc, collision_window=0.0):
        pass

    def cache_provider_doc(self, social_account, activities_doc, activity_map, expires=0.0):
        # type: (SocialAccount, object, object, float) -> bool
        updated = GoogleRSS.get_update_timestamp(activities_doc)

        item = {
            "AccountKey": social_account.Key,
            "Active": "Y",
            "Expires": "{0}".format(expires),
            "Updated": "{0}".format(updated),
            "ActivityMap": activity_map,
            "cacheGoogle": activities_doc
        }

        try:
            cache_key = S2.cache_key(self.poll_table_name, social_account.Key)
            self.cache_item(
                cache_key,
                self.poll_table_name,
                [
                    {"Item1": "AccountKey", "Item2": social_account.Key}
                ]
            )
            self.rc.set(cache_key, json.dumps(item, encoding='utf-8'))
            old_item = self.commit_item(cache_key)

            return not (old_item and 'Updated' in old_item and str(old_item['Updated']) == str(updated))

        except Exception as ex:
            self.logger.info('Update collision {0}, {1}'.format(social_account.Key, ex.message))

        return False

    def get_activities(self, gid):
        try:
            cached = self.cache_item(
                S2.cache_key(self.poll_table_name, gid),
                self.poll_table_name,
                [
                    {"Item1": "AccountKey", "Item2": gid}
                ]
            )

            return cached['cacheGoogle'] if 'cacheGoogle' in cached else None
        except Exception as ex:
            self.logger.info('Get item failed {0}:{1}'.format(gid, ex.message))

        return None

    def consensus(self, now, threshold):

        # 1/2 second threshold for consensus
        water = now - threshold

        # consensus algorithm implementation
        # 1. Remove items below waterline
        self.rc.zremrangebyscore(S2.Generals(), 0, water)

        # 2. zsize > 0 ?
        if self.rc.zcard(S2.Generals()) > 0:
            return False

        guid = uuid.uuid4().hex
        self.rc.zadd(S2.Generals(), guid, now)

        # 3.  Self on top?
        if self.rc.zrevrank(S2.Generals(), guid) > 0:
            return False

        return True

    def poll(self):
        # pop next item
        gid_tuple = self.rc.blpop(S2.poll_list(), 1)
        if gid_tuple:
            return gid_tuple[1]
        else:
            now = time.time()
            threshold = 0.5
            if self.consensus(now, threshold):
                # now we are quite safe to assume there are no other requests for
                # consensus threshold duration
                # 4. request items
                self.logger.info("Querying Dynoris for next poll items...")
                r1 = self.dynoris_client.api.ExpiringStamp.Next.post(
                    request_body={
                        "Table": self.poll_table_name,
                        "Index": self.poll_table_index_name,
                        "StoreKey": [{"Item1": "Active", "Item2": "Y"}],
                        "StampKey": {"Item1": "Expires", "Item2": "{0}".format(now)}
                    }
                )
                # the response is a list of jsons
                items = json.loads(r1.body)
                self.logger.info("...{0} items to poll".format(len(items)))
                for item_str in items:
                    self.rc.rpush(S2.poll_list(), item_str)
            else:
                self.logger.warn("Consensus collision")

        # will pick items next time around
        return None

    def cache_item(self, cache_key, table, store_key):
        self.dynoris_client.api.Dynoris.CacheItem.post(
            request_body={
                "Table": table,
                "CacheKey": cache_key,
                "StoreKey": store_key
            }
        )
        # load cached item
        item_str = self.rc.get(cache_key)
        return json.loads(item_str, encoding='utf-8')

    def commit_item(self, cache_key):
        r = self.dynoris_client.api.Dynoris.CommitItem.post(
            request_body=cache_key
        )
        return json.loads(r.body) if r and r.body else None

    def get_gid_max_results(self, gid):
        return config.DEFAULT_MAX_RESULTS

    def get_provider(self, provider_name):
        return self.provider[provider_name] if provider_name in self.provider else None

    def activities_doc_from_item(self, item):
        return item['cacheGoogle'] if 'cacheGoogle' in item else None

    def get_sources(self, gid):
        pass

    def get_linked_accounts(self, gid, temp=False):
        pass

    def scan_gid(self, page=None):
        pass
