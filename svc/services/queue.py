import random
import time
import traceback

from core.schema import S1
from services.service_base import ServiceBase
from utils import config


class Queue(ServiceBase):
    def __init__(self, logger, name, data, provider_names, config_path, dummy=False):
        super(Queue, self).__init__(logger, name, data, provider_names, config_path, dummy)

    def _on_update(self, channel, items):
        pass

    def run(self, *args, **kwargs):
        cfg = config.load_config(kwargs['config_path'], 'queue.json')
        period_s = cfg['period_s'] if 'period_s' in cfg else 10

        self.logger.info('Queue v[{0}], poll period=[{1}]s, starting...'.format(config.version, period_s))

        try:
            while True:
                # get the next items from the queue
                # set look ahead value to half of the wait time
                items = self.data.buffer.get_next_queue_items(period_s / 2.0)

                self.logger.info('{0} items...'.format(len(items)))

                # post notifications for each item
                for itm in items:
                    self.logger.info('Notifying: {0}'.format(itm))
                    # item format: "gid:target"
                    item = itm.split(':')
                    self.broadcast_command(S1.publisher_channel_name(item[1]), S1.msg_publish(), item[0])

                # sleep random interval
                s = random.randrange(period_s - (period_s / 10.0), period_s + (period_s / 10.0))
                self.logger.info('Sleeping {0} seconds...'.format(s))
                time.sleep(s)

        except Exception as e:
            self.logger.warning('Queue is terminating (exception): {0}'.format(e))
            self.logger.exception(traceback.format_exc())

    def on_terminate(self, *args, **kwargs):
        self.logger.warning('Queue is terminating')