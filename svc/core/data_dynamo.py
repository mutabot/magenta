import json
import time
import uuid

import jsonpickle
from tornado import gen

from core import provider_dynamo, pubsub
from core.buffer import Buffer
from core.cache_provider import CacheProvider
from core.data_base import DataBase
from core.data_interface import DataInterface
from core.filter import FilterData
from core.filter_dynamo import FilterDataDynamo
from core.model import SocialAccount, RootAccount, Link, HashItem
from core.model.model import LogItem
from core.model.schema2 import S2
from core.schema import S1
from providers.google_rss import GoogleRSS
from utils import config


class DataDynamo(DataBase, DataInterface):

    def populate_provider_bag(self, param, opt, param1):
        pass

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

    def add_log(self, gl_user, pid, message):
        message_item = [message, time.time()]
        if pid in gl_user.logs:
            gl_user.logs[pid].messages.append(message_item)
        else:
            gl_user.logs[pid] = LogItem(pid, [message_item])

        gl_user.dirty.add('logs')

    def set_links(self, root_pid, links):
        pass

    def flush(self, root_pid):
        pass

    def unregister_gid(self, gl_user):
        """

        @type gl_user: RootAccount
        """
        # TODO: Implement account deletion (soft delete or hard delete?)
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
        self.pubsub = pubsub.Pubsub(logger, self.rc)

        self.buffer = Buffer(logger, self.rc, self.pubsub)

        self.provider = {
            'facebook': provider_dynamo.ProviderDynamo(self.rc, 'facebook'),
            'twitter': provider_dynamo.ProviderDynamo(self.rc, 'twitter'),
            'tumblr': provider_dynamo.ProviderDynamo(self.rc, 'tumblr'),
            'flickr': provider_dynamo.ProviderDynamo(self.rc, 'flickr'),
            '500px': provider_dynamo.ProviderDynamo(self.rc, '500px'),
            'linkedin': provider_dynamo.ProviderDynamo(self.rc, 'linkedin'),
        }

        self.filter = FilterDataDynamo(self.rc)

    def refresh_user_token(self, gl_user, provider, pid):
        """

        @type gl_user: RootAccount
        """
        # TODO Google hardcoded
        self.pubsub.broadcast_command(S1.publisher_channel_name(provider), S1.msg_register(), gl_user.account.pid, pid)

    def set_user_token(self, user, token, expiry):
        """

        @type user: SocialAccount
        """
        user.credentials['token'] = token
        user.credentials['expiry'] = expiry

    def get_user_token(self, gl_user, provider, pid):
        """

        @type gl_user: RootAccount
        """
        key = SocialAccount(gl_user.account.pid, provider, pid).Key
        account = DataDynamo.get_account(gl_user, key)  # type: SocialAccount

        return account.credentials['token'] if 'token' in account.credentials else None

    def set_user_param(self, user, param, value):
        """

        @type user: SocialAccount
        """
        user.options[param] = value

    @gen.coroutine
    def get_log(self, gl_user):
        result = yield self.get_model_document("Logs", gl_user.Key)
        raise gen.Return(result)

    def set_log(self, root_key, log):
        key_name = S2.document_key_name(root_key, "Logs")
        self.rc.delete(key_name)
        for key, value in log.iteritems():
            self.rc.hset(key_name, key, json.dumps({"Items": value}))

    @gen.coroutine
    def register_gid(self, gl_user, source_account=None):
        # simply register for a poll
        yield self.cache_provider_doc(source_account, None, None)

    def cache_activities_doc(self, gid, activities_doc, collision_window=0.0):
        pass

    @gen.coroutine
    def get_activities(self, account_key):

        cache_key = yield self.dynoris.cache_poll_item(account_key)
        # load cached item
        item_str = self.rc.get(cache_key)
        cached = json.loads(item_str, encoding='utf-8')

        raise gen.Return(cached['ActivityDoc'] if 'ActivityDoc' in cached else None)

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

    @gen.coroutine
    def poll(self):
        # pop next item if have in the list
        gid_tuple = self.rc.blpop(S2.poll_list(), 1)
        if gid_tuple:
            raise gen.Return(gid_tuple[1])

        # run consensus algorithm
        now = time.time()
        threshold = 0.5
        if self.consensus(now, threshold):
            # now we are quite safe to assume there are no other requests for
            # consensus threshold duration
            # 4. request items
            self.logger.info("Querying Dynoris for next poll items...")
            items = yield self.dynoris.get_next_expired(now)
            self.logger.info("...{0} items to poll".format(len(items)))
            for item_str in items:
                self.rc.rpush(S2.poll_list(), item_str)

            # pick first item
            # the list is required to sync across multiple instances
            item = self.rc.lpop(S2.poll_list())
            raise gen.Return(item)

        else:
            self.logger.warn("Consensus collision")

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

        # load all records
        records = {key: jsonpickle.loads(value) for key, value in items.iteritems()}

        #  deleted records filter
        result = {key: value for key, value in records.iteritems()
                  if not value.deleted}  # type: HashItem

        raise gen.Return(result)
        # yield gen.Return(result)

    def get_gid_max_results(self, gid):
        return config.DEFAULT_MAX_RESULTS

    def get_provider(self, provider_name):
        return self.provider[provider_name] if provider_name in self.provider else None

    def activities_doc_from_item(self, item):
        return item['cacheGoogle'] if 'cacheGoogle' in item else None

    def get_terms_accept(self, root_acc):
        """

        @type root_acc: RootAccount
        """

        info = root_acc.options['terms'] if 'terms' in root_acc.options else {}
        return info

    def get_gid_info(self, gl_user):
        """

        @type root_acc: RootAccount
        """
        return gl_user.account.info

    def get_gid_sources(self, gl_user):
        """

        @type gl_user: RootAccount
        """
        # prefix = HashItem.make_key(DataBase.short_provider('google'), '')
        # TODO: Google hardcoded
        sources = {child.pid: GoogleRSS.get_user_name(child.info) or child
                   for child in gl_user.accounts.itervalues()
                   if child.provider == 'google'}

        return sources

    def get_sources(self, gid):
        pass

    @staticmethod
    def get_account_info(gl_user, acc_ref):
        """

        @type acc_ref: str
        @type gl_user: RootAccount
        """
        key = acc_ref
        return gl_user.accounts[key].info if key in gl_user.accounts else None

    def get_linked_accounts(self, gl_user, temp=False):
        """

        @type gl_user: RootAccount
        """

        return {link.target: DataDynamo.get_account_info(gl_user, link.target) for link in gl_user.links.itervalues()}

    def scan_gid(self, page=None):
        pass

    def get_gid_admin(self, gl_user):
        return bool(gl_user.options['admin'] if 'admin' in gl_user.options else False)

    def set_terms_accept(self, gl_user, info):
        """

        @type gl_user: RootAccount
        """
        gl_user.options['terms'] = info
        gl_user.dirty.add('accounts')

    def get_limits(self, gl_user):
        """

        @type gl_user: RootAccount
        """
        return gl_user.options['limits'] if 'limits' in gl_user.options else None

    @staticmethod
    def get_account(gl_user, key):
        account = gl_user.accounts[key] if key in gl_user.accounts else None
        return account

    def get_link(self, gl_user, link_key):
        """

        @param link_key: link key i.e. 'gl~1232445~fb~209239090'
        @type gl_user: RootAccount
        @rtype: Link
        """
        # find the link
        link = next((l for l in gl_user.links.itervalues() if l.Key == link_key), None)
        return link

    def get_links_for_source(self, gl_user, source_key):
        """
        Formats a list of active links for the given source
        @type gl_user: RootAccount
        """
        links = [l for l in gl_user.links.itervalues() if l.source == source_key and 'active' in l.options and l.options['active']]
        return links

    def set_gid_is_shorten_urls(self, link):
        """

        @type link: Link
        """
        # set a flag for poller to shorten urls for this gid

        # always shorten for twitter
        if link.target.startswith("tw~"):
            link.options[S2.cache_shorten_urls()] = True
        elif link.filters:
            tagline = link.filters[FilterData.tagline_kind]
            if tagline and any(k_word in tagline for k_word in GoogleRSS.description_keywords()):
                link.options[S2.cache_shorten_urls()] = True
        elif S2.cache_shorten_urls() in link.options:
            # clear the flag if no taglines require shortening
            link.options.pop(S2.cache_shorten_urls())

    def bind_user(self, gl_user, source_account, target_account, param2=None):
        """

        @rtype: Link
        @type target_account: SocialAccount
        @type source_account: SocialAccount
        @type gl_user: RootAccount
        """
        link = Link(source_account.provider, source_account.pid, target_account.provider, target_account.pid)
        gl_user.links[link.Key] = link
        gl_user.dirty.add('links')

        return link

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
        if result.Key in result.accounts:
            result.account = result.accounts[result.Key]
            result.options = result.account.info['magenta'] if 'magenta' in result.account.info else {}
        else:
            self.logger.error("Master account missing for: {0}", result.Key)

        raise gen.Return(result)

    @gen.coroutine
    def save_account_async(self, gl_user, what=None):
        """

        @type what: set
        @type gl_user: RootAccount:        
        """

        # union dirty flag sets
        what = what.union(gl_user.dirty) if what else gl_user.dirty

        # check orphaned sources
        # TODO: hardcoded 'google'
        orphans = [a for a in gl_user.accounts.itervalues()
                   if a.provider == 'google' and 'polled' in a.options and not self.get_links_for_source(gl_user, a.Key)]

        # stop polling orphaned sources
        for orphan in orphans:
            self.logger.info('Removing from poller: {0}'.format(orphan.Key))
            orphan.options.pop('polled')
            yield self.dynoris.remove_poll_item(orphan.Key)

        if len(orphans):
            what.add('accounts')

        # write links, logs, and accounts to dynamo
        if what is None or 'logs' in what:
            self.logger.info('Committing logs for: {0}'.format(gl_user.Key))
            yield self.dynoris.cache_object(gl_user.Key, "Logs")
            self.set_model_document("Logs", gl_user.Key, gl_user.logs)
            yield self.dynoris.commit_object(gl_user.Key, "Logs")

        if what is None or 'links' in what:
            self.logger.info('Committing links for: {0}'.format(gl_user.Key))
            yield self.dynoris.cache_object(gl_user.Key, "Links")
            self.set_model_document("Links", gl_user.Key, gl_user.links)
            yield self.dynoris.commit_object(gl_user.Key, "Links")

        if what is None or 'accounts' in what:
            self.logger.info('Committing accounts for: {0}'.format(gl_user.Key))
            # massage options into the master account record
            # master_account = next(a for a in gl_user.accounts.itervalues() if a.pid == gl_user.account.pid)
            # master_account.info['magenta'] = gl_user.options
            yield self.dynoris.cache_object(gl_user.Key, "Accounts")
            self.set_model_document("Accounts", gl_user.Key, gl_user.accounts)
            yield self.dynoris.commit_object(gl_user.Key, "Accounts")

    @gen.coroutine
    def delete_provider_doc(self, social_account):
        # type: (SocialAccount) -> bool
        yield self.dynoris.remove_poll_item(social_account.Key)

    @gen.coroutine
    def cache_provider_doc(self, social_account, activity_doc, activity_map, expires=0.0):
        # type: (SocialAccount, object, object, float) -> bool
        updated = GoogleRSS.get_update_timestamp(activity_doc)

        item = {
            "AccountKey": social_account.Key,
            "OwnerKey": social_account.owner,
            "Active": "Y",
            "Expires": expires,
            "Updated": updated,
            "ActivityMap": activity_map,
            "ActivityDoc": activity_doc
        }

        result = False

        try:
            cache_key = yield self.dynoris.cache_poll_item(social_account.Key)

            item_str = json.dumps(item, encoding='utf-8')
            self.rc.set(cache_key, item_str)
            old_item = yield self.dynoris.commit_item(cache_key, cache_key)

            result = not (old_item and 'Updated' in old_item and str(old_item['Updated']) == str(updated))

        except Exception as ex:
            self.logger.info('Update collision {0}, {1}'.format(social_account.Key, ex.message))
            raise gen.Return(False)

        raise gen.Return(result)

    def get_destination_users(self, gl_user, source, provider):
        """
        Return list of links where this source is a source
        @type gl_user: RootAccount
        @type source: SocialAccount
        @type provider: str
        """
        prefix = HashItem.make_key(DataBase.short_provider(provider), '')
        return [link for link in gl_user.links.itervalues() if link.source == source.Key and link.target.startswith(prefix)]

    def remove_binding(self, gl_user, link):
        """
        Deactivates the link
        @type link: Link
        @type gl_user: RootAccount
        """
        self.logger.info('Unbinding GID: [{0}] -/-> [{1}:{2}]'.format(gl_user.Key, link.source, link.target))
        self.add_log(gl_user, gl_user.account.pid, 'Unbinding Google+ [{0}] -/-> [{1}:{2}]'.format(gl_user.Key, link.source, link.target))

        # check url shortener
        self.set_gid_is_shorten_urls(link)

        # mark link as inactive
        link.options['active'] = False
        gl_user.dirty.add('links')

    def purge_temp_accounts(self, gl_user):
        """
        Temp accounts are used to store accounts user has access but have not yet associated with the system
        @type gl_user: RootAccount
        """
        names = [value.Key for value in gl_user.accounts.itervalues() if 'temp' in value.options]
        self.logger.info('removing temp {0} accounts'.format(len(names)))
        for name in names:
            gl_user.accounts.pop(name)

    def add_temp_account(self, gl_user, account, param1=None, param2=None):
        """

        @type account: SocialAccount
        @type gl_user: RootAccount
        """
        account.options['temp'] = True
        gl_user.accounts[account.Key] = account
        gl_user.dirty.add('accounts')

    def del_provider_session(self, gid, param):
        pass

    def get_short_url(self, url):
        return self.rc.hget(S1.cache_url_key(), url)

    def cache_short_url(self, url, short_url):
        return self.rc.hset(S1.cache_url_key(), url, short_url)
