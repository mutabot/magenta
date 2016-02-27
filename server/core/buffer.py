from bisect import bisect_right
from datetime import datetime
import json
from random import randrange


class Buffer(object):
    BUFFER_BUFFER = 'buffer.buffer'
    BUFFER_STORE = 'buffer.store'
    # used to convert 'XX' hex hour representation to decimal hour of week
    HOUR_DICT = {'{0:02x}'.format(h): h for h in range(0, 168)}

    def __init__(self, logger, rc, pubsub):
        """
        @type rc: redis.Redis
        @type pubsub: pubsub.Pubsub
        """
        self.logger = logger
        self.rc = rc
        self.pubsub = pubsub

    def buffer(self, gid, target, tid):
        """
        Buffers an update notification for the given triplet if buffering is configured
        @param gid:
        @param target:
        @param tid:
        @return: True if posting must be buffered
        """

        # get the schedule name for this destination link
        schedule_name = ':'.join([target, tid])

        # check the schedule
        schedule = self.get_schedule(gid, schedule_name)
        if not schedule:
            self.logger.error('Schedule not found [{0}]'.format(schedule_name))
            return False

        # check if schedule is disabled or empty
        schedule_s = schedule['s']
        if not (schedule['on'] and schedule_s):
            return False

        # check if now hour is in schedule
        now = datetime.utcnow()
        hour = now.weekday() * 24 + now.hour
        if hour in schedule_s:
            self.logger.info('Not buffering for [{0}]'.format(schedule_name))
            return False

        # get next open window and buffer the crosspost
        hours_to_next_window = self.get_next_window(hour, schedule_s)

        # calculate absolute epoch in seconds
        now_epoch = (now - datetime(1970, 1, 1)).total_seconds()
        # drop minutes -- notify at the beginning of the hour
        now_epoch -= now.minute * 60
        # add random offset approx 15 min to distribute load
        now_epoch += randrange(0, 1000)
        # calculate next window in epoch time
        next_window_epoch = hours_to_next_window * 3600 + now_epoch

        # posting not allowed, add to schedule for buffer to pick it up
        # get_next_queue_items will pick all items from the sorted set
        # not storing the target id (tid) as publisher will check all active
        # target id's and their schedules at the time of notification
        self.rc.zadd(self.BUFFER_BUFFER, ':'.join([gid, target]), next_window_epoch)

        return True

    def buffer_in_s(self, gid, target, delay_s):
        """
        Schedule update for the given target in delay_s seconds
        NOTE: actual delay depends on queue service poll period!
        @param gid:
        @param target:
        @param delay_s:
        @return:
        """
        now_epoch = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()

        self.rc.zadd(self.BUFFER_BUFFER, ':'.join([gid, target]), now_epoch + delay_s)

    def get_next_queue_items(self, look_ahead_s=0):
        """
        @return: list of "gid:target" strings that are past due to notification
        """
        now_epoch = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()
        items = self.rc.zrangebyscore(self.BUFFER_BUFFER, -1.0, now_epoch + look_ahead_s)
        if items:
            # remove all items that will be notified now
            self.rc.zrem(self.BUFFER_BUFFER, *items)
        else:
            # check the next item
            next_item = self.rc.zrange(self.BUFFER_BUFFER, 0, 1, withscores=True)
            if not next_item:
                self.logger.info('Buffer set is empty')
            else:
                self.logger.info('No buffers to notify, next buffer in [{0}] sec.'.format(next_item[0][1] - now_epoch))

        return items

    @staticmethod
    def expand_schedule(schedule_s):
        return sorted([Buffer.HOUR_DICT[schedule_s[n:n + 2]] for n in xrange(0, len(schedule_s), 2)])

    def get_schedule(self, gid, schedule_name):
        key = ':'.join([gid, schedule_name])
        schedule_str = self.rc.hget(self.BUFFER_STORE, key)
        if not schedule_str:
            return None

        schedule = json.loads(schedule_str)
        # expand compacted schedule
        schedule['s'] = self.expand_schedule(schedule['s'])
        return schedule

    @staticmethod
    def compact_schedule(schedule_s):
        return ''.join(['{0:02x}'.format(h) for h in schedule_s])

    def set_schedule(self, gid, schedule_name, schedule):
        key = ':'.join([gid, schedule_name])
        if not schedule:
            self.rc.hdel(self.BUFFER_STORE, key)
        else:
            # compact schedule
            schedule['s'] = self.compact_schedule(schedule['s'])
            self.rc.hset(self.BUFFER_STORE, key, json.dumps(schedule, separators=(',', ':')))

    @staticmethod
    def get_next_window(hour, schedule_s):
        """
        @type schedule_s: dict
        @return: time in hours to sleep until next window of opportunity as defined by the schedule_s
        """
        # find next hour of the week when posting is enabled
        # or rollover to the next week
        idx = bisect_right(schedule_s, hour)
        next_hour = schedule_s[idx] if idx != len(schedule_s) else schedule_s[0]

        return next_hour - hour if next_hour > hour else 168 - hour + next_hour
