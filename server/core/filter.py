import json
import redis
from utils import config


class FilterData:
    keyword_kind = 'keyword'
    keyword_merge = 'keyword_merge'
    likes_kind = 'likes'
    strip_kind = 'strip'
    tagline_kind = 'tagline'

    filter_kinds = {keyword_kind, likes_kind, strip_kind, tagline_kind}

    def __init__(self, rc):
        """
        @type rc: redis.Redis
        """
        self.rc = rc

    @staticmethod
    def merge_filter_data(filter_a, filter_b, included=set()):
        merged = dict()
        # stip keywords is always included if keyword is included
        if FilterData.keyword_kind in included:
            included.add(FilterData.strip_kind)
        # copy data
        for k, v in filter_a.iteritems():
            if k not in included:
                continue
            if k == FilterData.keyword_kind and FilterData.keyword_merge in included:
                b_words = filter_b[k] if k in filter_b else None
                merged[k] = ','.join(set(v.split(',') if v else '') | set(b_words.split(',') if b_words else ''))
            else:
                merged[k] = v
        return merged

    def get_filter(self, destination, gid, pid):
        raw = self.rc.hget(self.filter_all_key_fmt(destination, pid), self.root_key(gid))
        f = json.loads(raw) if raw else dict()
        # make sure all filter keys are present in the resulting dict
        return {k: f[k] if k in f else None for k in self.filter_kinds}

    def get_filter_legacy(self, destination, gid, pid):
        return {k: self.rc.hget(self.root_key(gid), self.filter_key_fmt(k, destination, pid)) for k in
                self.filter_kinds}

    def set_filter(self, destination, gid, pid, filter_data):
        if not filter_data:
            self.rc.hdel(self.filter_all_key_fmt(destination, pid), self.root_key(gid))
        else:
            self.rc.hset(self.filter_all_key_fmt(destination, pid), self.root_key(gid),
                         json.dumps({k: v for k, v in filter_data.iteritems() if v}))

    def del_filter(self, destination, gid, pid):
        self.rc.hdel(self.filter_all_key_fmt(destination, pid), self.root_key(gid))

    def set_message_id_map(self, provider, user, mapping):
        """
        @type mapping: dict
        """
        # remove oldest records if map is larger than threshold
        if len(mapping) > config.DEFAULT_MAX_RESULTS_MAP:
            keys = [k[0] for k in
                    sorted(mapping.items(), key=lambda x: x[1]['updated'])[:-config.DEFAULT_MAX_RESULTS_MAP]]

            # delete from the map
            for key in keys:
                del mapping[key]

            # delete from db
            if len(keys):
                self.rc.hdel(self.message_id_key_fmt(provider, user), *keys)

        # flattent values to json
        for key in mapping.keys():
            mapping[key] = json.dumps(mapping[key])

        # write to db
        if len(mapping):
            self.rc.hmset(self.message_id_key_fmt(provider, user), mapping)

    def get_message_id_map(self, provider, user):
        value_all = self.rc.hgetall(self.message_id_key_fmt(provider, user))
        if not value_all:
            return {}
        for key in value_all.keys():
            value_all[key] = json.loads(value_all[key])
        return value_all

    def del_message_id_map(self, provider, user):
        self.rc.delete(self.message_id_key_fmt(provider, user))

    @staticmethod
    def root_key(gid):
        return 'filter:{0}'.format(gid)

    @staticmethod
    def filter_key_fmt(kind, destination, pid):
        return '{0}:{1}:{2}'.format(kind, destination, pid)

    @staticmethod
    def filter_all_key_fmt(destination, pid):
        return '{0}:{1}'.format(destination, pid)

    @staticmethod
    def message_id_key_fmt(provider, user):
        return '{0}:{1}:message'.format(provider, user)
