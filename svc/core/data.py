import json
import time

import redis

from core import balancer, cache, provider_data
from core.buffer import Buffer
from core.data_api import DataApi
from core.data_base import DataBase
from core.data_interface import DataInterface
from core.filter import FilterData
from providers.google_rss import GoogleRSS
import pubsub
from schema import S1


# noinspection PyBroadException
class Data(DataBase, DataInterface):

    def __init__(self, logger, redis_host, redis_port, redis_db):
        DataBase.__init__(self, logger, redis_host, redis_port, redis_db)

        self.pubsub = pubsub.Pubsub(logger, redis.Redis(host=redis_host, port=redis_port, db=redis_db))
        self.balancer = balancer.Balancer(logger, self.rc, self.pubsub)
        self.cache = cache.Cache(logger, self.rc)
        self.provider = {
            'facebook': provider_data.ProviderData(self.rc, 'facebook'),
            'twitter': provider_data.ProviderData(self.rc, 'twitter'),
            'tumblr': provider_data.ProviderData(self.rc, 'tumblr'),
            'flickr': provider_data.ProviderData(self.rc, 'flickr'),
            '500px': provider_data.ProviderData(self.rc, '500px'),
            'linkedin': provider_data.ProviderData(self.rc, 'linkedin'),
        }
        self.facebook = self.provider['facebook']
        self.twitter = self.provider['twitter']
        self.tumblr = self.provider['tumblr']
        self.flickr = self.provider['flickr']
        self.px500 = self.provider['500px']
        self.linkedin = self.provider['linkedin']
        self.filter = FilterData(self.rc)
        self.buffer = Buffer(logger, self.rc, self.pubsub)

    def begin_validate_gid(self, gid):
        self.begin_service_query(gid, S1.msg_validate())

    def get_validate_gid(self, gid):
        r = self.end_service_query(gid, S1.msg_validate())
        # first result only
        return r[0] if r else None

    def begin_service_query(self, gid, query):
        self.list_push(S1.query_list_in(query), gid)
        self.pubsub.broadcast_command(S1.poller_channel_name('all'), query, S1.query_list_in(query), S1.query_list_out(query))

    def end_service_query(self, gid, query):
        # get all in list
        results = self.rc.lrange(S1.query_list_out(query), 0, -1)
        if not results:
            return None

        received = []
        # check all results for the specified gid
        mask = '{0}:'.format(gid)
        for result in results:
            if result.startswith(mask):
                self.rc.lrem(S1.query_list_out(query), result)

                # filter out empty results
                received.append(result[len(mask):])

        return [r for r in received if r] if len(received) else None

    def is_valid_gid(self, gid):
        return self.rc.zscore(S1.gid_set('all'), gid) or self.rc.exists(S1.gid_key(gid))

    def register_gid(self, gid):
        """
        registers the gid in the system for pollers to start polling
        forces pollers to update cache
        @param gid: google user id
        """
        self.logger.info('Registering GID: {0}'.format(gid))
        # add to gid set with zero score
        self.balancer.add_gid_set(gid, 0.0)
        # reset cache
        self.cache.reset_cache(gid)
        # poke the pollers
        self.balancer.register_gid(gid)

    def remove_from_poller(self, gid):
        # remove from master set
        self.rc.zrem(S1.gid_set('all'), gid)

        # clear cache
        self.rc.delete(S1.cache_key(gid))
        self.del_destination_param(gid, 'cache', gid, S1.updated_key())
        self.del_destination_param(gid, 'cache', gid, S1.etag_key())
        self.purge_temp_accounts(gid)

    def forget_source(self, master_gid, gid):
        """
        Removes source gid, unlinks all bindings associated with the source
        @param master_gid: master gid
        @param gid: source gid
        @return:
        """
        self.logger.info('Removing source [{0}:{1}]...'.format(master_gid, gid))
        destinations = self.get_destinations(gid)
        for destination in destinations:
            users = self.get_destination_users(gid, destination)
            for user in users:
                # source gid can be bound to destination that does not belong to this master gid
                # forget_destination will only remove bindings that belong to this master gid
                DataApi.forget_destination(self, self.logger, gid, destination, user)

        # remove the gid from the list of child accounts
        self.remove_linked_account(master_gid, gid)

        # clear gid data if no destinations left
        destinations = self.get_destinations(gid)
        if not destinations:
            self.logger.info('Source [{0}:{1}] is orphaned, cleaning...'.format(master_gid, gid))
            # remove user keys
            self.rc.delete(S1.gid_key(gid))
            self.rc.delete(S1.gid_log_key(gid))
            self.rc.delete(S1.links_key(gid))
            self.rc.delete(S1.cache_key(gid))
            self.del_destination_param(gid, 'cache', '', S1.cache_shorten_urls())
            # clear chache and remove gid from poller list
            self.remove_from_poller(gid)

    def unregister_gid(self, gid):
        """
        unregister user and remove all data associated with it
        @param gid: google user id
        """
        self.logger.warning('Deleting user, GID: {0}'.format(gid))

        # clear child bindings for this account
        children = set(self.get_destination_users(gid, 'children'))
        # just to be safe
        children.add(gid)
        for child in children:
            self.forget_source(gid, child)

    def cache_activities_doc(self, gid, activities_doc, collision_window=0.0):
        self.cache.cache_activities_doc(gid, activities_doc)

    def get_gid_admin(self, gid):
        return self.rc.hget(S1.gid_key(gid), S1.admin_key())

    def set_gid_admin(self, gid, admin=None):
        self.rc.hset(S1.gid_key(gid), S1.admin_key(), admin if admin else 1)

    def set_gid_credentials(self, gid, json_str):
        self.rc.hset(S1.gid_key(gid), S1.credentials_key(), json_str)

    def get_gid_credentials(self, gid):
        return self.rc.hget(S1.gid_key(gid), S1.credentials_key())

    def del_gid_credentials(self, gid):
        self.rc.hdel(S1.gid_key(gid), S1.credentials_key())

    def set_gid_info(self, gid, info):
        self.rc.hset(S1.gid_key(gid), S1.info_key(), json.dumps(info) if info else '')

    def get_gid_info(self, gid):
        value = self.rc.hget(S1.gid_key(gid), S1.info_key())
        return json.loads(value) if value else None

    def get_terms_accept(self, gid):
        info = self.rc.hget(S1.TERMS_OK_KEY, gid)
        return json.loads(info) if info else None

    def set_terms_accept(self, gid, info):
        self.rc.hset(S1.TERMS_OK_KEY, gid, json.dumps(info) if info else '')

    def del_gid_info(self, gid):
        self.rc.hdel(S1.gid_key(gid), S1.info_key())

    def check_orphan(self, gid, at_time):
        """
        Check gid inactivity, will update timeouts for this gid or remove it altogether
        @param gid:
        @return:
        """
        if at_time and not self.cache.check_orphan(gid, at_time):
            return False

        # check if gid is bound to any destinations
        destinations = self.get_destinations(gid)
        if destinations and len(destinations):
            return False

        # gid is orphaned, remove it from pollers
        self.logger.warning('Orphaned GID: [{0}], removed from pollers...'.format(gid))
        self.remove_from_poller(gid)

        return True

    def flush_updates(self, gid):
        """ flushes any updates stuck in the update queue """
        destinations = self.get_destinations(gid)
        self.logger.info('Notifying destinations: {0}'.format(destinations))
        for destination in destinations:
            self.pubsub.broadcast_command(S1.publisher_channel_name(destination), S1.msg_publish(), gid)

    def register_poller(self, name):
        self.rc.sadd(S1.poller_set(), name)
        return name

    def unregister_poller(self, name):
        self.rc.srem(S1.poller_set(), name)

    def get_pollers(self):
        return self.rc.smembers(S1.poller_set())

    def add_linked_account(self, parent_gid, gid, bag=None):
        parent_key = S1.provider_root_key('parents', bag) if bag else 'parents'
        child_key = S1.provider_root_key('children', bag) if bag else 'children'

        self._append_hfield(S1.destination_key_fmt(parent_key), gid, parent_gid)
        self._append_hfield(S1.destination_key_fmt(child_key), parent_gid, gid)

    def remove_linked_account(self, parent_gid, gid, bag=None):
        parent_key = S1.provider_root_key('parents', bag) if bag else 'parents'
        child_key = S1.provider_root_key('children', bag) if bag else 'children'

        self._delete_hfield_item(S1.destination_key_fmt(parent_key), gid, parent_gid)
        self._delete_hfield_item(S1.destination_key_fmt(child_key), parent_gid, gid)

    def get_linked_parents(self, gid, bag=None):
        parent_key = S1.provider_root_key('parents', bag) if bag else 'parents'
        return self._get_hfield_list(S1.destination_key_fmt(parent_key), gid)

    def get_linked_children(self, gid, bag=None):
        child_key = S1.provider_root_key('children', bag) if bag else 'children'
        return self._get_hfield_list(S1.destination_key_fmt(child_key), gid)

    def get_linked_users(self, gid, destination, user):
        """
        yields a list of user gids who own gid->destination:user binding
        @param gid: gid of the source, not user gid
        @param destination: name of the destination i.e. "facebook"
        @param user: destination user id
        @return: yeilds gids of users who own gid->destination:user binding
        """
        parents = self.get_linked_parents(gid)
        for parent in parents:
            children = self.get_linked_children(parent, bag='dst')
            if S1.provider_root_key(destination, user) in children:
                yield parent

    def _purge_gid_gid(self, parent, gid):
        """
        union all bindings for all linked children for the parent
        and remove links where gid to parent are not related
        @param parent:
        @param gid:
        @return:
        """
        children = self.get_linked_children(parent, bag='dst')
        child_gids = set()
        # extend with binding for all parent's children
        for child in children:
            try:
                d = child.split(':')
                child_gids.update(self.get_bindings(d[0], d[1]))
            except:
                pass

        # check if gid is still feeding any of the child links
        if gid not in child_gids:
            self.logger.info('Removing account linking: [{0}] --> [{1}]'.format(parent, gid))
            self.remove_linked_account(parent, gid)
        else:
            self.logger.info('Keeping account linking: [{0}] --> [{1}]'.format(parent, gid))

    def purge_gid_links(self, destination, user):
        """
        cleans abandoned account links
        """
        # find all parents' [p]->destination:user
        # find all gids that feed the [p]->[destination:user] <- [gid]
        # if the gid is not in gids -- break the link parent -> gid
        # iterate over list of owners/parents of this destination:user account
        parents = self.get_linked_parents(S1.provider_root_key(destination, user), bag='dst')
        for parent in parents:
            # purge gid 2 gid links
            # this is now a manual process -- users can remove gid-gid links from the UI
            # self._purge_gid_gid(parent, gid)

            # check if destination:user is being fed by any of the parent's children
            # Note: parent will be listed as child of self
            children = self.get_linked_children(parent)
            child_links = set(self.get_bindings(destination, user))
            if not len(child_links.intersection(children)):
                self.logger.info('Removing account linking: [{0}] --> [{1}]'.format(parent, S1.provider_root_key(destination, user)))
                self.remove_linked_account(parent, S1.provider_root_key(destination, user), bag='dst')

    def reset_destination(self, gid, destination, user):
        """
        Reset destination update timestamps
        """
        # set last update timestamp to 0
        t0 = int(time.time())
        self.set_destination_update(gid, destination, user, t0)
        # store first bound timestamp
        self.set_destination_first_use(gid, destination, user, t0)
        # clean destination errors
        self.set_provider_error_count(destination, user, 0)

    def bind_user(self, master_gid, gid, destination, user):
        # bind to destination poller
        self.logger.info('Binding: [{0}] --> [{1}]:[{2}]'.format(gid, destination, user))
        # store gid to gid relation
        self.add_linked_account(master_gid, gid)
        # store gid to destination user relation
        self.add_linked_account(master_gid, S1.provider_root_key(destination, user), bag='dst')

        # reset timestamps and errors
        self.reset_destination(gid, destination, user)
        # bind source and destination
        self.bind_destination(gid, destination, user)

        # carpet-notify GID destinations of updates
        self.flush_updates(gid)

        # append GID log
        self.add_log(master_gid, 'Success: Linked Google+ [{0}] --> [{1}:{2}]'.format(gid, destination, user))
        self.logger.info('Success: Linked Google+ [{0}] --> [{1}:{2}]'.format(gid, destination, user))

    def remove_binding(self, gid, destination, user, clean=False):
        """ clears binding created by bind_user() """
        self.logger.info('Unbinding GID: [{0}] -/-> [{1}:{2}]'.format(gid, destination, user))
        self.add_log(gid, 'Unbinding Google+ [{0}] -/-> [{1}:{2}]'.format(gid, destination, user))

        # remove binding update option
        self.rc.hdel(S1.destination_option_key_fmt(destination),
                     S1.destination_pair_fmt(gid, user, S1.updated_key()))

        # remove destination user id from list of destinations for this gid
        self._delete_hfield_item(S1.destination_key_fmt(destination), gid, user)

        # remove gid from list of sources for this destination user
        self._delete_hfield_item(S1.destination_source_key_fmt(destination), user, gid)

        # clean linked accounts
        # find the owner(s) of the destination:user pair
        self.purge_gid_links(destination, user)

        # the gid->destination:user link is broken
        # clear this relationship
        self.remove_linked_account(gid, S1.provider_root_key(destination, user), bag='dst')

        # remove destination binding if no bindings to this destination left
        bound_users = self.get_destination_users(gid, destination)
        if not (bound_users and len(bound_users)):
            self.logger.info('No links remain for [{0} --> {1}]'.format(gid, destination))
            # remove destination from gid destination list
            self._delete_hfield_item(S1.destination_key_fmt(S1.destinations_key()), gid, destination)

        # keep message map for the destination:user -- user may re-bind later with new token
        # unless forced to clean all
        # keep filters unless forced to clean!
        if clean:
            self.filter.del_filter(destination, gid, user)
            self.filter.del_message_id_map(destination, user)

        # clear bound timestamp
        self.del_destination_param(gid, destination, user, S1.bound_key())

        # check_orphan() will stop polling the gid if nothing is bound to it
        self.check_orphan(gid, 0)

    def bind_destination(self, gid, destination, user):
        # bind source and destination
        self._append_hfield(S1.destination_key_fmt(destination), gid, user)
        # bind destination to source
        self._append_hfield(S1.destination_source_key_fmt(destination), user, gid)
        # append destination list for the source
        self._append_hfield(S1.destination_key_fmt(S1.destinations_key()), gid, destination)

    def get_bindings(self, destination, user):
        return self._get_hfield_list(S1.destination_source_key_fmt(destination), user)

    def get_destinations(self, gid):
        """ returns list of destinations associated with this source gid """
        return self._get_hfield_list(S1.destination_key_fmt(S1.destinations_key()), gid)

    def get_destination_users(self, gid, destination):
        """ returns a list of destination-specific users bound to this gid """
        return self._get_hfield_list(S1.destination_key_fmt(destination), gid)

    def set_destination_param(self, gid, destination, user, param, value):
        """ sets parameter in gid:destination:user record """
        self.rc.hset(S1.destination_option_key_fmt(destination), S1.destination_pair_fmt(gid, user, param), value)

    def del_destination_param(self, gid, destination, user, param):
        """ clears parameter in gid:destination:user record """
        self.rc.hdel(S1.destination_option_key_fmt(destination), S1.destination_pair_fmt(gid, user, param))

    def get_destination_param(self, gid, destination, user, param):
        """ returns parameter in gid:destination:user record """
        return self.rc.hget(S1.destination_option_key_fmt(destination), S1.destination_pair_fmt(gid, user, param))

    def set_destination_update(self, gid, destination, user, timestamp):
        """ sets last update timestamp for destination """
        self.set_destination_param(gid, destination, user, S1.updated_key(), timestamp)

    def get_destination_update(self, gid, destination, user):
        """ returns last update timestamp for destination """
        result = self.get_destination_param(gid, destination, user, S1.updated_key())
        if not result:
            return 0
        return float(result)

    def set_destination_first_use(self, gid, destination, user, timestamp):
        """ sets first use timestamp for destination """
        self.set_destination_param(gid, destination, user, S1.bound_key(), timestamp)

    def get_destination_first_use(self, gid, destination, user):
        """ returns first use timestamp for destination """
        result = self.get_destination_param(gid, destination, user, S1.bound_key())
        if not result:
            return 0
        return float(result)

    def purge_linked_provider_accounts(self, gid, provider):
        keys = self.rc.smembers(S1.links_key(gid))
        to_purge = [k for k in keys if k.split(':')[0] == provider]
        if to_purge:
            self.rc.srem(S1.links_key(gid), *to_purge)

    def unlink_provider_account(self, gid, provider, user):
        self.rc.srem(S1.links_key(gid), S1.provider_root_key(provider, user))

    def link_provider_account(self, gid, provider, user, data=None):
        self.rc.sadd(S1.links_key(gid), S1.provider_root_key(provider, user))
        if data:
            self.rc.hset(S1.provider_root_key(provider, user), S1.ACCOUNT_KEY, data)

    def get_linked_account(self, gid, provider, user):
        return self.rc.hget(S1.provider_root_key(provider, user), S1.ACCOUNT_KEY)

    def get_linked_accounts(self, gid, temp=False):
        links = self.rc.smembers(S1.links_key(gid) if not temp else S1.links_temp_key(gid))
        result = { link:self.rc.hget(link, S1.ACCOUNT_KEY) for link in links }
        return result

    def add_temp_account(self, gid, provider, user, data):
        self.rc.sadd(S1.links_temp_key(gid), S1.provider_root_key(provider, user))
        self.rc.hset(S1.provider_root_key(provider, user), S1.ACCOUNT_KEY, data)

    def purge_temp_accounts(self, gid):
        # remove all accounts
        links_t = self.rc.smembers(S1.links_temp_key(gid))
        links = links_t.difference(self.rc.smembers(S1.links_key(gid)))
        for link in links:
            # second check for usage in another account
            if self.rc.hexists(S1.destination_key_fmt('parents:dst'), link):
                continue
            self.rc.hdel(link, S1.ACCOUNT_KEY)
        self.rc.delete(S1.links_temp_key(gid))

    def is_linked_account(self, gid, provider, user):
        return self.rc.sismember(S1.links_key(gid), S1.provider_root_key(provider, user))

    def set_provider_session(self, gid, session_id, provider, data):
        """
        Use to store arbitrary session data specific to a provider. All session for all providers is cleared when user logs off
        """
        self.rc.hset(S1.gid_key(gid), S1.destination_session_id_fmt(provider, session_id), json.dumps(data))

    def get_provider_session(self, gid, session_id, provider):
        value = self.rc.hget(S1.gid_key(gid), S1.destination_session_id_fmt(provider, session_id))
        return json.loads(value) if value else None

    def del_all_provider_sessions(self, gid):
        for p in self.provider.keys():
            self.del_provider_session(gid, p)

    def del_provider_session(self, gid, provider):
        keys = self.rc.hkeys(S1.gid_key(gid))
        to_clear = [key for key in keys if key.startswith(S1.destination_session_fmt(provider))]
        if len(to_clear):
            self.rc.hdel(S1.gid_key(gid), *to_clear)

    # TODO: Create proper iteration over providers
    def populate_provider_bag(self, provider, account_bag, account_id):
        account_bag['sources'] = []
        account_bag['filter'] = dict()

        # options
        account_bag['op'] = {
            k: self.provider[provider].get_user_param(account_id, k) for k in S1.PROVIDER_PARAMS
        }

        # iterate destination bindings
        source_gid_set = self.get_bindings(provider, account_id)
        for source_gid in source_gid_set:
            # set source display name and id
            account_bag['sources'].append(source_gid)

            # set source filter
            account_bag['filter'][source_gid] = self.filter.get_filter(provider, source_gid, account_id)

    def get_gid_sources(self, gid):
        children = self.get_linked_children(gid)
        # add self to sources if needed
        if gid not in children:
            children.append(gid)

        sources = {child: GoogleRSS.get_user_name(self.get_gid_info(child)) or child for child in children}

        return sources

    def incr_provider_error_count(self, provider, user):
        count_str = self.rc.hincrby(S1.provider_root_key(provider, user), S1.error_count_key())
        return int(count_str) if count_str else 0

    def set_provider_error_count(self, provider, user, count):
        self.rc.hset(S1.provider_root_key(provider, user), S1.error_count_key(), count)

    def get_provider_error_count(self, provider, user):
        count_str = self.rc.hget(S1.provider_root_key(provider, user), S1.error_count_key())
        return int(count_str) if count_str else 0

    def get_log(self, gid):
        # get child account logs too
        children = set(self.get_destination_users(gid, 'children'))
        children.add(gid)
        log = {k: self.rc.zrange(S1.gid_log_key(k), 0, -1, withscores=True) for k in children}

        return log

    def add_log(self, gid, message):
        # log to log file
        self.logger.error('User Log [{0}]: {1}'.format(gid, message))
        # log to gid's log if key does not exist
        if self.rc.zscore(S1.gid_log_key(gid), message):
            return
        # add new record
        self.rc.zadd(S1.gid_log_key(gid), message, time.time())
        # trim log to latest 99 messages
        self.rc.zremrangebyrank(S1.gid_log_key(gid), 0, -100)

    def del_log(self, gid):
        self.rc.delete(S1.gid_log_key(gid))

    def get_limits(self, gid):
        return self.rc.hget(S1.gid_key(gid), S1.LIMITS_KEY)

    def set_limits(self, gid, limit_tag):
        if limit_tag:
            self.rc.hset(S1.gid_key(gid), S1.LIMITS_KEY, limit_tag)
        else:
            self.rc.hdel(S1.gid_key(gid), S1.LIMITS_KEY)

    def set_gid_is_shorten_urls(self, gid):
        # set a flag for poller to shorten urls for this gid
        # check all user's links
        destinations = self.get_destinations(gid)

        # always shorten for twitter
        if 'twitter' in destinations:
            self.set_gid_shorten_urls(gid, '1')
            return

        # check for taglines
        for destination in destinations:
            users = self.get_destination_users(gid, destination)
            for user in users:
                f = self.filter.get_filter(destination, gid, user)
                tagline = f[FilterData.tagline_kind]
                if tagline and any(k_word in tagline for k_word in GoogleRSS.description_keywords()):
                    self.set_gid_shorten_urls(gid, '1')
                    return

        # clear the flag if no taglines require shortening
        self.set_gid_shorten_urls(gid, '')

    def set_gid_shorten_urls(self, gid, shorten):
        if shorten:
            self.set_destination_param(gid, 'cache', '', S1.cache_shorten_urls(), shorten)
        else:
            self.del_destination_param(gid, 'cache', '', S1.cache_shorten_urls())

    def get_gid_shorten_urls(self, gid):
        return self.get_destination_param(gid, 'cache', '', S1.cache_shorten_urls())

    # noinspection PyUnusedLocal
    def refresh_user_token(self, gid, provider, pid):
        self.pubsub.broadcast_command(S1.publisher_channel_name(provider), S1.msg_register(), pid)

    # noinspection PyUnusedLocal
    def get_user_token(self, gid, provider, pid):
        return self.provider[provider].get_user_token(pid)

    # noinspection PyUnusedLocal
    def set_user_token(self, gid, provider, pid, token, expires=0):
        return self.provider[provider].set_user_token(pid, token, expires)

    def set_publisher_value(self, target, key, value):
        """
        Stores a generic value associated with the target
        @param target: target account id i.e. facebook:nnnnn
        @param key: value key
        @param value: value
        @return:
        """
        self.rc.hset(':'.join((S1.TARGET_VALUE_KEY, key)), target, value)

    def get_publisher_value(self, target, key):
        """
        Reads a generic value associated with the given target account
        @param target: target account id i.e. facebook:nnnnn
        @param key: value key
        @return: value
        """
        return self.rc.hget(':'.join((S1.TARGET_VALUE_KEY, key)), target)
