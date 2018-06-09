from multiprocessing import Process
import time
import traceback
from logging import Logger

from core.schema import S1
from services import poller_worker
from services.service_base import ServiceBase
from utils import config
from core import Data


class Poller(ServiceBase):

    def __init__(self, logger, name, data, providers, config_path, dummy=False):
        """
            @type logger: Logger
            @type data: Data
            """
        super(Poller, self).__init__(logger, name, data, providers, config_path)

        self.kwargs = None
        # default poller driver period
        self.period_s = 2
        # how many gids are allowed to expire in period_s before new worker is launched
        self.gid_set_threshold = 100
        # number of worker processes
        self.workers_min = 3
        # max number of worker process
        self.workers_max = 4
        # default gid poll period, 10 min
        self.gid_poll_s = 600
        # default no poll period, 30 min
        self.gid_no_poll_s = 1800

        self.started_at = time.time()
        self.stats = {
            'hour': (self.started_at, 0),
            'day': (self.started_at, 0),
        }

        self.channel_handler = {
            S1.poller_channel_name('all-out'): self.on_all_out,
            S1.poller_channel_name(self.name): self.on_my_name
        }

    def get_worker(self, sub_name):
        kwargs = self.kwargs
        kwargs['name'] = sub_name
        return Process(target=poller_worker.run_poller_worker, name=sub_name, kwargs=self.kwargs)

    def on_terminate(self, *args, **kwargs):
        """
        Called by signal handlers from ServiceBase
        WARNING: This can be called multiple times during process termination!
        """
        self.logger.warning('Poller master is terminating...')
        # stop workers
        while self.stop_worker():
            self.logger.warning('One worker stopped')

        # stop self
        self.send_exit(S1.poller_channel_name(self.name), self_target=True)
        self.logger.warning('Poller master terminate sequence complete!')

    def on_exit(self, channel):
        self.logger.warning('Poller master terminating listener...')
        self.terminate()

    def on_raw(self, channel, raw):
        try:
            # channel_handler is one of the two routines below
            self.channel_handler[channel](raw)
        except Exception as e:
            self.logger.error('ERROR: Exception in on_raw: {0}, \r\n{1}'.format(e, traceback.format_exc()))

    def on_all_out(self, gid):
        """
        Reschedules the gid for next poll based on gid activity, other factors may be added later
        @param gid: assuming raw data is gid
        """
        at_time = time.time()
        # default poll period for each gid is 10 * 60 sec
        next_time = at_time + self.gid_poll_s
        try:
            # get num results in this 3-hour period
            if not self.data.cache.get_num_minute_updates(gid, int(at_time), 90):
                # no updates this time of day --> add 45 minutes to next poll epoch
                next_time += self.gid_no_poll_s
        except Exception as e:
            msg = 'Exception while processing stats [{0}], [{1}], {2}'
            self.logger.error(msg.format(gid, e, traceback.format_exc()))

        # store just polled gid in sorted gid set
        self.data.balancer.add_gid_set(gid, next_time)

    def on_my_name(self, raw):
        self.schedule_next_batch(allow_worker_start=False)

    def on_timeout(self):
        self.schedule_next_batch(allow_worker_start=True)

    def schedule_next_batch(self, allow_worker_start=False):
        try:
            self.logger.info('[{0}] wake up!'.format(self.name))
            # get the gid set until all processed
            while True:
                at_time = time.time()
                gid_set = self.data.balancer.get_next_poll_set(at_time + self.period_s / 2.0)
                gid_set_len = len(gid_set)
                if not gid_set_len:
                    self.logger.warning('[{0}] Empty gid_set...'.format(self.name))
                    return
                elif allow_worker_start and gid_set_len > self.gid_set_threshold:
                    self.logger.warning('Gid set count [{0}] above threshold, starting worker...'.format(gid_set_len))
                    self.start_worker()

                self.logger.info('[{0}] Invoking poll for [{1}] items...'.format(self.name, gid_set_len))

                # clean orphaned gids
                update_set = [gid for gid in gid_set if not self.data.check_orphan(gid, at_time)]

                # post each gid to poller
                for gid in update_set:
                    # move next poll time for the gid to avoid duplicate polling
                    self.data.balancer.add_gid_set(gid, at_time + self.gid_poll_s)
                    # post to pollers
                    self.broadcast_command(S1.poller_channel_name('all'), S1.msg_update(), gid)

                # update stats
                self.update_stats(at_time, len(update_set))

        except Exception as e:
            self.logger.warning('Exception in poller driver: {0}'.format(e))
            self.logger.exception(traceback.format_exc())
            self.data.unregister_poller(self.name)

    def update_stats(self, at_time, count):
        s = self.stats['hour']
        self.stats['hour'] = (s[0], s[1] + count)
        s = self.stats['day']
        self.stats['day'] = (s[0], s[1] + count)

        # set in DB
        self.data.balancer.set_poller_stats(self.name, hour=self.stats['hour'][1], day=self.stats['day'][1])

        # clean stats if lapsed
        if at_time - self.stats['hour'][0] > 3600:
            # reset counters
            self.stats['hour'] = (at_time, 0)
            if at_time - self.stats['day'][0] > 86400:
                self.stats['day'] = (at_time, 0)

    def run(self, *args, **kwargs):
        self.kwargs = kwargs
        cfg = config.load_config(kwargs['config_path'], 'poller.json')
        self.gid_poll_s = cfg['gid_poll_s'] if 'gid_poll_s' in cfg else self.gid_poll_s
        self.period_s = cfg['period_s'] if 'period_s' in cfg else self.period_s
        self.workers_min = cfg['workers_min'] if 'workers_min' in cfg else self.workers_min
        self.workers_max = cfg['workers_max'] if 'workers_max' in cfg else self.workers_max

        self.logger.info('Poller v[{0}], name=[{1}], poll delay=[{2}]s, period=[{3}]s starting...'.format(config.version, self.name, self.gid_poll_s, self.period_s))

        # give pub sub some time... not using sync notifications...
        time.sleep(1)

        # register self as poller
        self.data.register_poller(self.name)

        # start worker processes
        for n in range(0, self.workers_min):
            self.start_worker()

        # drop message to self to do immediate poll round
        self.broadcast_data(S1.poller_channel_name(self.name), '#')
        # start listening
        self.listener([S1.poller_channel_name('all-out'), S1.poller_channel_name(self.name)], None, timeout=self.period_s)
        self.logger.warning('Poller master listener exit!')

        # un-register self
        self.data.unregister_poller(self.name)

        # force kill any remaining workers
        while self.workers:
            p = self.workers.popitem()
            self.logger.warning('Terminating remaining poller {0}!'.format(p[0]))
            p[1].terminate()
        self.logger.warning('Poller master process exit!')
