import json
from core.model import RootAccount, Link

from core.filter import FilterData
from utils import config


class FilterDataDynamo(FilterData):
    keyword_kind = 'keyword'
    keyword_merge = 'keyword_merge'
    likes_kind = 'likes'
    strip_kind = 'strip'
    tagline_kind = 'tagline'

    filter_kinds = {keyword_kind, likes_kind, strip_kind, tagline_kind}

    def __init__(self, rc):
        FilterData.__init__(self, rc)

    def get_filter(self, gl_user, link_key, link_key_):
        link = next((l for l in gl_user.links if l.Key == link_key), None)
        if not link:
            # link not found -- do nothing, error reporting can be added later
            return None

        return link.filters

    def set_filter(self, gl_user, link, link_key, filter_data):
        """

        @type link: Link
        @param link: link object
        @param filter_data: filter data
        @param link_key: filter key
        @type gl_user: RootAccount
        """
        if not link:
            # link not found -- do nothing, error reporting can be added later
            return

        if not filter_data:
            # clear the filter
            link.filters = {}
        else:
            link.filters = filter_data

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