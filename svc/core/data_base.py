import time
import redis


class DataBase(object):
    # map used to format blob for UI templates
    short_provider_map = [
        ('facebook', 'fb'),
        ('twitter', 'tw'),
        ('tumblr', 'tr'),
        ('flickr', 'fr'),
        ('500px', '5p'),
        ('linkedin', 'in'),
        ('google', 'gl')
    ]

    # noinspection PyBroadException
    @staticmethod
    def long_provider(short_name):
        try:
            return next(it for it in DataBase.short_provider_map if it[1] == short_name)[0]
        except:
            return None

    # noinspection PyBroadException
    @staticmethod
    def short_provider(long_name):
        try:
            return next(it for it in DataBase.short_provider_map if it[0] == long_name)[1]
        except:
            return None

    def __init__(self, logger, redis_host, redis_port, redis_db):
        """
        @type logger: Logger
        """
        self.logger = logger
        self.logger.info('Connecting to Redis at {0}:{1}:{2}'.format(redis_host, redis_port, redis_db))
        self.rc = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

    def is_loading(self):
        try:
            info = self.rc.info(section='persistence')
            return bool(info['loading'])
        except:
            pass

        return True

    def _get_hfield_as_str_time(self, key, field):
        req_f = 0
        req_str = self.rc.hget(key, field)
        if req_str:
            req_f = float(req_str)
        return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(req_f))

    def _append_hfield(self, key, field, value):
        list_str = self.rc.hget(key, field)
        if not list_str:
            self.rc.hset(key, field, value)
        elif list_str.count(value) == 0:
            list_str += ',{0}'.format(value)
            self.rc.hset(key, field, list_str)

    def _delete_hfield_item(self, key, field, value):
        list_str = self.rc.hget(key, field)
        if not list_str or list_str.count(value) == 0:
            return
        items = [v for v in list_str.split(',') if v and v != value]
        if len(items):
            update = ''.join([item + ',' for item in items])
            self.rc.hset(key, field, update[:-1])
        else:
            self.rc.hdel(key, field)

    def _get_hfield_list(self, key, field):
        list_str = self.rc.hget(key, field)
        if not list_str:
            return []
        return list_str.split(',')

    def get_next_in_list(self, list_name):
        value = self.rc.lpop(list_name)
        if value:
            yield value

    def list_push(self, list_name, value):
        self.rc.lpush(list_name, value)
