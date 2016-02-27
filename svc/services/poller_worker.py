from datetime import time
import random
import traceback

from core import data
from core.schema import S1
from providers.google_poll import GooglePollAgent
from services.service_base import ServiceBase
from utils import config


class PollerWorker(ServiceBase):
    def __init__(self, logger, name, data, provider_names, config_path):
        super(PollerWorker, self).__init__(logger, name, data, provider_names, config_path)
        self.google_poll = GooglePollAgent(logger, data, config_path)

    def on_terminate(self, *args, **kwargs):
        self.logger.warning('[{0}] Poller is force-terminating...'.format(self.name))
        self.terminate()

    def on_exit(self, channel):
        self.logger.warning('[{0}] Poller is terminating nicely...'.format(self.name))
        self.terminate()

    def _on_update(self, channel, items):
        if not items:
            self.logger.warning('[{0}] Empty items skipped...'.format(self.name))
            return

        gid_set = [item.strip(',') for item in items.split(',')]

        if not gid_set:
            self.logger.warning('[{0}] Empty gid_set skipped...'.format(self.name))
            return

        for gid in gid_set:

            if self.dummy:
            # sleep random to imitate web-service call
                self.logger.info('Poller is dummy, not posting [{0}]'.format(gid))
                time.sleep(random.randint(1000, 1500) / 1000.0)
            else:
                #### POLL GOOGLE for data, reschedule for expedited retry if poll fails
                if not self.google_poll.poll(gid):
                    self.logger.warning('Retrying for {0} ...'.format(gid))
                    self.data.pubsub.broadcast_command(S1.poller_channel_name('all'), S1.msg_update(), gid)
                else:
                    # the gid will be picked up by poller master and decorated for the next poll
                    self.data.pubsub.broadcast_data(S1.poller_channel_name('all-out'), gid)

    def _on_validate(self, channel, in_list_name, out_list_name):
        for user_name in self.data.get_next_in_list(in_list_name):
            self.logger.info('Validating Google User ID {0}'.format(user_name))
            valid_name = self.google_poll.validate_user_name(user_name)
            self.data.list_push(out_list_name, '{0}:{1}'.format(user_name, valid_name))

    def _on_register(self, channel):
        gid = self.data.balancer.get_next_registered()
        while gid:
            self.logger.info('Registring GID: {0}'.format(gid))
            self.data.pubsub.broadcast_command(S1.poller_channel_name(self.name), S1.msg_update(), gid)
            gid = self.data.balancer.get_next_registered()

    def run(self, *args, **kwargs):
        """
        Goes into infinite blocking listener() loop
        """
        callback = {
            S1.msg_update(): self._on_update,
            S1.msg_validate(): self._on_validate,
            S1.msg_register(): self._on_register,
        }
        self.listener([S1.poller_channel_name('all'), S1.poller_channel_name(self.name)], callback)


def run_poller_worker(*args, **kwargs):

    logger = config.get_logger(kwargs['log_path'], kwargs['name'])
    try:
        db = data.Data(logger, kwargs['redis_host'], kwargs['redis_port'], kwargs['redis_db'])
        p = PollerWorker(logger, kwargs['name'], db, None, kwargs['config_path'])
        logger.info('Starting poller worker: {0}'.format(kwargs['name']))
        p.run(args, kwargs)
    except Exception as e:
        logger.error('ERROR: Exception in run_poller_worker: {0}\r\n{1}'.format(e, traceback.format_exc()))