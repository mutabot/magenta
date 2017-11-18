import json
import time
import uuid

import jsonpickle
from tornado import gen

from core import provider_dynamo
from core.cache_provider import CacheProvider
from core.data_base import DataBase
from core.data_interface import DataInterface
from core.model import SocialAccount
from core.model.model import RootAccount
from core.model.schema2 import S2
from providers.google_rss import GoogleRSS
from utils import config


class DataDynamo(DataBase, DataInterface):

    def add_linked_account(self, pid, gid, root_acc=None):
        pass

    def del_all_provider_sessions(self, gid):
        pass

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
        """

        @rtype: object
        """
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

        self.dynoris = CacheProvider(dynoris_url)

        self.provider = {
            'facebook': provider_dynamo.ProviderDynamo(self.rc, 'facebook'),
            'twitter': provider_dynamo.ProviderDynamo(self.rc, 'twitter'),
            'tumblr': provider_dynamo.ProviderDynamo(self.rc, 'tumblr'),
            'flickr': provider_dynamo.ProviderDynamo(self.rc, 'flickr'),
            '500px': provider_dynamo.ProviderDynamo(self.rc, '500px'),
            'linkedin': provider_dynamo.ProviderDynamo(self.rc, 'linkedin'),
        }

    def get_log(self, root_key):
        return self.get_model_document("logs", root_key)

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

    def cache_provider_doc(self, social_account, activity_doc, activity_map, expires=0.0):
        # type: (SocialAccount, object, object, float) -> bool
        updated = GoogleRSS.get_update_timestamp(activity_doc)

        item = {
            "AccountKey": social_account.Key,
            "Active": "Y",
            "Expires": expires,
            "Updated": updated,
            "ActivityMap": activity_map,
            "ActivityDoc": activity_doc
        }

        try:
            cache_key = self.dynoris.cache_poll_item(social_account.Key)

            item_str = json.dumps(item, encoding='utf-8')
            self.rc.set(cache_key, item_str)
            old_item = self.dynoris.commit_item(cache_key)

            return not (old_item and 'Updated' in old_item and str(old_item['Updated']) == str(updated))

        except Exception as ex:
            self.logger.info('Update collision {0}, {1}'.format(social_account.Key, ex.message))

        return False

    def get_activities(self, gid):
        try:
            cache_key = self.dynoris.cache_poll_item(gid)
            # load cached item
            item_str = self.rc.get(cache_key)
            cached = json.loads(item_str, encoding='utf-8')

            return cached['ActivityDoc'] if 'ActivityDoc' in cached else None
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
                items = self.dynoris.get_next_expired(now)
                self.logger.info("...{0} items to poll".format(len(items)))
                for item_str in items:
                    self.rc.rpush(S2.poll_list(), item_str)
            else:
                self.logger.warn("Consensus collision")

        # will pick items next time around
        return None

    def set_model_document(self, document_name, root_key, items):
        """
        Stores the items as a hash value in redis
        @type items: dict of HashItems
        @param items:
        @param document_name: name of the items document
        @param root_key:
        @return:
        """
        key_name = S2.document_key_name(root_key, document_name)
        self.rc.delete(key_name)
        for item_key, item in items.iteritems():
            js = jsonpickle.dumps(item)
            self.rc.hset(key_name, item_key, js)

    def set_model_document_delta(self, document_name, root_key, items, new_items):
        """
        Stores the items as a hash value in redis, stores only values missing in the reference set
        @type new_items: dict of HashItems
        @param new_items: new items to store at the key
        @type items: dict of HashItems
        @param items: reference items
        @param document_name: name of the items document
        @param root_key:
        @return:
        """
        key_name = S2.document_key_name(root_key, document_name)
        self.rc.delete(key_name)
        keys = [k for k in new_items if k not in items]
        for item_key in keys:
            js = jsonpickle.dumps(new_items[item_key])
            self.rc.hset(key_name, item_key, js)

    @gen.coroutine
    def get_model_document(self, document_name, root_key):
        # cache item first
        yield self.dynoris.cache_object(root_key, document_name)
        key_name = S2.document_key_name(root_key, document_name)
        items = self.rc.hgetall(key_name)
        result = {key: jsonpickle.loads(value) for key, value in items.iteritems()}
        raise gen.Return(result)

    def get_gid_max_results(self, gid):
        return config.DEFAULT_MAX_RESULTS

    def get_provider(self, provider_name):
        return self.provider[provider_name] if provider_name in self.provider else None

    def activities_doc_from_item(self, item):
        return item['cacheGoogle'] if 'cacheGoogle' in item else None

    def get_terms_accept(self, gid):
        account = self.load_account_async(gid)
        child = account.accounts[gid] if account and account.accounts and gid in account.accounts[gid] else {}
        info = child.info['magenta']['info'] if child.info and 'magenta' in child.info else {}
        return info['tnc'] == 'on' if 'tnc' in info else False

    def get_gid_info(self, gid, root_acc=None):
        """

        @type root_acc: RootAccount
        """
        return root_acc.accounts[gid].info

    def get_sources(self, gid):
        pass

    def get_linked_accounts(self, gid, temp=False):
        pass

    def scan_gid(self, page=None):
        pass

    @gen.coroutine
    def load_account_async(self, root_pid):
        """

        @rtype: RootAccount
        """
        result = RootAccount("google", root_pid)
        result.accounts = yield self.get_model_document("Accounts", result.Key)
        result.links = yield self.get_model_document("Links", result.Key)
        result.logs = yield self.get_model_document("Logs", result.Key)

        # format info
        result.account = result.accounts[result.Key]

        raise gen.Return(result)
