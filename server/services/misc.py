import json
from multiprocessing import Process
import time
import traceback
from logging import Logger

from core.schema import S1
from providers.mail import MailPublisher
from services.service_base import ServiceBase
from utils import config
from core import Data


def run_misc_worker(*args, **kwargs):
    logger = config.get_logger(kwargs['log_path'], kwargs['name'])
    try:
        db = Data(logger, kwargs['redis_host'], kwargs['redis_port'], kwargs['redis_db'])
        p = MiscWorker(logger, kwargs['name'], db, None, kwargs['config_path'])
        logger.info('Starting poller worker: {0}'.format(kwargs['name']))
        p.run(args, kwargs)
    except Exception as e:
        logger.error('ERROR: Exception in run_misc_worker: {0}\r\n{1}'.format(e, traceback.format_exc()))


class MiscWorker(ServiceBase):
    def __init__(self, logger, name, data, provider_names, config_path):
        super(MiscWorker, self).__init__(logger, name, data, provider_names, config_path)
        self.mail = MailPublisher(self.logger, self.data, config_path)
        self.mail_template_map = dict(
            account_created=dict(
                subject='Welcome to Magenta River',
                template_name='account_created',
                params=dict(),
                check_accept=False
            ),
            account_unlinked=dict(
                template_name='account_unlinked',
                params=dict()
            ),
            publisher_error=dict(
                template_name='publisher_error',
                params=dict()
            )
        )

    def on_terminate(self, *args, **kwargs):
        self.logger.warning('[{0}] Misc worker is force-terminating...'.format(self.name))
        self.terminate()

    def on_exit(self, channel):
        self.logger.warning('[{0}] Misc worker is terminating nicely...'.format(self.name))
        self.terminate()

    def run(self, *args, **kwargs):
        """
        Goes into infinite blocking listener() loop
        """
        self.logger.info('MiscWorker starting...')
        callback = {
            'mail.send': self._on_email,
        }
        self.listener([S1.MAILER_CHANNEL_NAME], callback)

    def _on_email(self, channel, gid, template, args_json=None):
        try:
            args = json.loads(args_json) if args_json else dict()
            self.logger.info('Email: {0}:{1}'.format(gid, template))
            a = self.mail_template_map[template]
            a.update(args)
            self.mail.send(gid, **a)
        except Exception as e:
            self.logger.error('Error: e-mail to [{0}], {1}'.format(gid, e))


class MiscService(ServiceBase):
    MISC_SERVICE_CHANNEL = 'misc.svc'
    def __init__(self, logger, name, data, providers, config_path, dummy=False):
        """
            @type logger: Logger
            @type data: Data
            """
        super(MiscService, self).__init__(logger, name, data, providers, config_path)

        self.kwargs = None

        self.channel_handler = {
            MiscService.MISC_SERVICE_CHANNEL: self.on_my_name
        }

    def get_worker(self, sub_name):
        kwargs = self.kwargs
        kwargs['name'] = sub_name
        return Process(target=run_misc_worker, name=sub_name, kwargs=self.kwargs)

    def on_terminate(self, *args, **kwargs):
        """
        Called by signal handlers from ServiceBase
        WARNING: This can be called multiple times during process termination!
        """
        self.logger.warning('Misc Service is terminating...')
        # stop workers
        while self.stop_worker():
            self.logger.warning('One worker stopped')

        # stop self
        self.send_exit(MiscService.MISC_SERVICE_CHANNEL, self_target=True)
        self.logger.warning('Misc Service terminate sequence complete!')

    def on_exit(self, channel):
        self.logger.warning('Misc Service terminating listener...')
        self.terminate()

    def on_raw(self, channel, raw):
        pass

    def on_my_name(self, raw):
        pass

    def on_timeout(self):
        pass

    def run(self, *args, **kwargs):
        self.kwargs = kwargs
        cfg = config.load_config(kwargs['config_path'], 'misc.json')
        self.workers_min = cfg['workers_min'] if 'workers_min' in cfg else self.workers_min
        self.workers_max = cfg['workers_max'] if 'workers_max' in cfg else self.workers_max

        self.logger.info('Misc Service v[{0}], name=[{1}], starting...'.format(config.version, self.name))

        # give pub sub some time... not using syncho notifications...
        time.sleep(1)

        # start worker processes
        for n in range(0, self.workers_min):
            self.start_worker()

        # start listening
        self.listener([MiscService.MISC_SERVICE_CHANNEL], None)
        self.logger.warning('Misc Service listener exit!')

        # force kill any remaining workers
        while self.workers:
            p = self.workers.popitem()
            self.logger.warning('Terminating remaining worker {0}!'.format(p[0]))
            p[1].terminate()
        self.logger.warning('Misc Service process exit!')