

class S1(object):
    MAILER_CHANNEL_NAME = 'mail:all'
    QUEUE_CHANNEL_NAME = 'queue:all'
    PROVIDER_PARAMS = ['album_links', 'album_ignore_stamp', 'in_cty', 'time_space_min']
    LIMITS_KEY = 'lmts'
    ACCOUNT_KEY = 'acc'
    TERMS_OK_KEY = 'terms:all'
    TARGET_VALUE_KEY = 'target:value'

    def __init__(self):
        pass

    @staticmethod
    def gid_set(name):
        return 'poller:{0}:gid.set'.format(name)

    @staticmethod
    def gid_key(gid):
        return 'gid:{0}'.format(gid)

    @staticmethod
    def gid_provider_data_key(provider):
        return 'provider:{0}:data'.format(provider)

    # ****************************************************
    # *********     POLLER & BALANCER SCHEMA     *********
    # ****************************************************
    @staticmethod
    def register_set():
        return 'poller:all:register.set'

    @staticmethod
    def poller_set():
        return 'poller:all:poller.set'

    @staticmethod
    def poller_key_fmt(name):
        return 'poller.info:{0}'.format(name)

    @staticmethod
    def orphaned_timeout_key():
        return 'timeout.orphan'

    @staticmethod
    def admin_key():
        return 'admin'

    @staticmethod
    def credentials_key():
        return 'credentials'

    @staticmethod
    def info_key():
        return 'info'

    @staticmethod
    def cache_key(gid):
        return 'cache:plus:{0}'.format(gid)

    @staticmethod
    def cache_url_key():
        return 'cache:url:all'

    @staticmethod
    def cache_items_key():
        return 'items'

    @staticmethod
    def updated_key():
        return 'updated'

    @staticmethod
    def etag_key():
        return 'etag'

    @staticmethod
    def bound_key():
        return 'bound'

    @staticmethod
    def polled_key():
        return 'polled'

    @staticmethod
    def cache_requested_key():
        return 'requested'

    @staticmethod
    def cache_filter_key():
        return 'filter'

    @staticmethod
    def cache_max_results_key():
        return 'max.results'

    @staticmethod
    def cache_shorten_urls():
        return 'shorten.urls'

    @staticmethod
    def destinations_key():
        return 'destinations'

    @staticmethod
    def destination_key_fmt(provider):
        return 'bind:{0}'.format(provider)

    @staticmethod
    def destination_source_key_fmt(provider):
        return 'bind:{0}:source'.format(provider)

    @staticmethod
    def destination_option_key_fmt(provider):
        return 'bind:{0}:option'.format(provider)

    @staticmethod
    def destination_pair_fmt(id1, id2, key=None):
        if key:
            return '{0}:{1}:{2}'.format(id1, id2, key)
        return '{0}:{1}'.format(id1, id2)

    @staticmethod
    def destination_session_fmt(provider):
        return 'session:{0}'.format(provider)

    @staticmethod
    def destination_session_id_fmt(provider, session_id):
        return '{0}:{1}'.format(S1.destination_session_fmt(provider), session_id)

    @staticmethod
    def gid_log_key(gid):
        return 'log:{0}'.format(gid)

    @staticmethod
    def links_key(gid):
        return 'links:{0}'.format(gid)

    @staticmethod
    def links_temp_key(gid):
        return 'links.t:{0}'.format(gid)

    # ****************************************************
    # *********          PUB-SUB SCHEMA          *********
    # ****************************************************
    @staticmethod
    def poller_channel_name(name):
        return 'poller:{0}'.format(name)

    @staticmethod
    def publisher_channel_name(name):
        return 'publisher:{0}'.format(name)

    @staticmethod
    def msg_update():
        return 'update'

    @staticmethod
    def msg_publish():
        return 'publish'

    @staticmethod
    def msg_register():
        return 'register'

    @staticmethod
    def msg_validate():
        return 'validate'

    @staticmethod
    def msg_update_avatar():
        return 'update_avatar'

    @staticmethod
    def query_list_in(query):
        return 'qry.{0}.in'.format(query)

    @staticmethod
    def query_list_out(query):
        return 'qry.{0}.out'.format(query)

    @staticmethod
    def updated_hour_fmt(hour):
        return 'update.hour:{0}'.format(hour)

    @staticmethod
    def updated_minute_fmt(minute):
        return 'update.minute:{0}'.format(minute)

    @staticmethod
    def get_minute_fmt_minute(key):
        """
        @type key: str
        """
        if not key.startswith('update.minute:'):
            return None

        return key[len('update.minute:'):]

    @staticmethod
    def provider_root_key(provider, user):
        return '{0}:{1}'.format(provider, user)

    @staticmethod
    def error_count_key():
        return 'errors'