from logging import Logger

from redis import Redis

from core.pubsub import Pubsub
from core.schema import S1


class Balancer:
    def __init__(self, logger, redis, pubsub):
        """
        @type pubsub: Pubsub
        @type logger: Logger
        @type redis: Redis
        """
        self.logger = logger
        self.rc = redis
        self.pubsub = pubsub

    def get_next_poll_set(self, up_to_epoch):
        """
        grabs a range up to current time() from 'all' gid set
        @return: batch of gids to process or None if cursor reset is required
        """
        return self.rc.zrangebyscore(S1.gid_set('all'), 0, up_to_epoch, start=0, num=200, withscores=False)

    def set_poller_stats(self, name, hour, day):
        self.rc.hset(S1.poller_key_fmt(name), 'hour', hour)
        self.rc.hset(S1.poller_key_fmt(name), 'day', day)

    def get_poller_stats(self):
        pollers = [{'name': k,
                    'hour': self.rc.hget(S1.poller_key_fmt(k), 'hour'),
                    'day': self.rc.hget(S1.poller_key_fmt(k), 'day')}
                   for k in self.rc.smembers(S1.poller_set())]

        return pollers

    def get_poller_stats_ex(self):

        return dict(
            all_count=self.rc.zcard(S1.gid_set('all')),
            pollers=self.get_poller_stats(),
            poller_names=list(self.rc.smembers(S1.poller_set())),
            register_set_len=self.rc.scard(S1.register_set()),
            poll_list_len=self.rc.llen(S1.poller_channel_name('all'))
        )

    def register_gid(self, gid):
        # add to balance list
        self.rc.sadd(S1.register_set(), gid)
        # notify poller(s)
        self.pubsub.broadcast_command_now(S1.poller_channel_name('all'), S1.msg_register())

    def get_next_registered(self):
        return self.rc.spop(S1.register_set())

    def add_gid_set(self, gid, at_epoch):
        self.rc.zadd(S1.gid_set('all'), gid, at_epoch)