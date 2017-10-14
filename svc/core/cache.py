import json
import time
from core.schema import S1
from utils import config
from redis import Redis
from logging import Logger


class Cache(object):
    def __init__(self, logger, redis):
        """
        @type logger: Logger
        @type redis: Redis
        """
        self.logger = logger
        self.rc = redis

    def reset_cache(self, gid):
        self.set_poll_stamp(gid, 0)
        self.rc.hset(S1.cache_key(gid), S1.cache_requested_key(), time.time())

    def get_gid_max_results(self, gid):
        return self.get_hfield(S1.cache_key(gid), S1.cache_max_results_key(), config.DEFAULT_MAX_RESULTS)

    def set_gid_max_results(self, gid, max_results):
        return self.rc.hset(S1.cache_key(gid), S1.cache_max_results_key(), max_results)

    def cache_short_url(self, url, short_url):
        return self.rc.hset(S1.cache_url_key(), url, short_url)

    def get_short_url(self, url):
        return self.rc.hget(S1.cache_url_key(), url)

    def cache_activities_doc(self, gid, activities_doc):
        """ stores activities document (google's) into local database (redis)
        @type gid: str
        @param gid: source user id
        @param activities_doc: source data dict
        """
        self.rc.hset(S1.cache_key(gid), S1.cache_items_key(), json.dumps(activities_doc, encoding='utf-8'))

    def hget_int(self, key, sub_key):
        try:
            return int(self.rc.hget(key, sub_key))
        except:
            return 0

    def get_num_minute_updates(self, gid, stamp, spread_minutes):
        keys = self.rc.hkeys(S1.cache_key(gid))
        return sum([self.hget_int(S1.cache_key(gid), k) for k in keys if self._is_key_in_stamp(k, stamp, spread_minutes)])

    def get_activity_update_map(self, gid):
        map = {m: self.rc.hget(S1.cache_key(gid), S1.updated_minute_fmt(m)) for m in range(0, 1439)}
        return {k: v for k,v in map.iteritems() if v > 0}

    def incr_num_minute_updates(self, gid, stamp):
        # get the minute of the day
        minute = (stamp / 60) % 1440
        self.rc.hincrby(S1.cache_key(gid), S1.updated_minute_fmt(minute))

    def get_activities(self, gid):
        str_value = self.rc.hget(S1.cache_key(gid), S1.cache_items_key())
        return json.loads(str_value) if str_value else None

    def is_cache(self, gid, option):
        #check last requested timestamp
        #get last request timestamp and filter
        requested_str = self.rc.hget(S1.cache_key(gid), S1.cache_requested_key())
        last_filter = self.rc.hget(S1.cache_key(gid), S1.cache_filter_key())
        #save last request time and filter
        self.rc.hset(S1.cache_key(gid), S1.cache_requested_key(), time.time())
        self.rc.hset(S1.cache_key(gid), S1.cache_filter_key(), option)

        if requested_str:
            if (not last_filter or option == last_filter) and time.time() - float(requested_str) < config.DEFAULT_FORCE_MISS_TIMEOUT:
                self.logger.warning('Force-request detected [{0}]'.format(gid))
            else:
                # cache hit
                return True
        else:
            self.logger.warning('New user detected [{0}]'.format(gid))

        # cache miss
        return False

    def is_poll_after(self, gid, stamp):
        polled_str = self.rc.hget(S1.cache_key(gid), S1.polled_key())
        if polled_str:
            polled = float(polled_str)
            if polled >= stamp:
                return True
        return False

    def get_poll_stamp(self, gid):
        polled_str = self.rc.hget(S1.cache_key(gid), S1.polled_key())
        if polled_str:
            return float(polled_str)
        return 0

    def set_poll_stamp(self, gid, stamp):
        self.rc.hset(S1.cache_key(gid), S1.polled_key(), stamp)

    def check_orphan(self, gid, at_time):
        """ returns true if gid is orphaned """
        #get last requested timestamp
        requested_str = self.rc.hget(S1.cache_key(gid), S1.cache_requested_key())
        if not requested_str:
            return False

        # compare to orphaned timeout
        if at_time - float(requested_str) < config.DEFAULT_ORPHANED_TIMEOUT:
            return False

        return True

    def get_hfield(self, key, filed, default=None):
        value = self.rc.hget(key, filed)
        if not value:
            return default
        return value

    @staticmethod
    def _is_key_in_stamp(key, stamp, spread_minutes):
        try:
            minute = int(S1.get_minute_fmt_minute(key))
            stamp_minute = stamp / 60 % 1440
            return (stamp_minute - spread_minutes) <= minute <= (stamp_minute + spread_minutes)
        except:
            return False
