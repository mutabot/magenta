import atexit
import signal
from core.pubsub import Pubsub
from core.schema import S1
from core import DataDynamo


class ServiceBase(Pubsub):
    def __init__(self, logger, name, data, provider_names, config_path, dummy=False):
        """
        @type logger: Logger
        @type data: DataDynamo
        """
        super(ServiceBase, self).__init__(logger, data.rc)
        # register for kill signals
        atexit.register(self.on_terminate)
        signal.signal(signal.SIGTERM, self.on_terminate)
        signal.signal(signal.SIGABRT, self.on_terminate)
        signal.signal(signal.SIGINT, self.on_terminate)

        self.name = name
        self.logger = logger
        self.data = data
        self.dummy = dummy
        self.provider_names = provider_names
        self.config_path = config_path
        self.workers = dict()
        # number of worker processes
        self.workers_min = 1
        # max number of worker process
        self.workers_max = 1

    def run(self, *args, **kwargs):
        pass

    def on_terminate(self, *args, **kwargs):
        """
        WARNING: This can be called multiple times during process termination!
        """
        pass

    def get_worker(self, sub_name):
        pass

    def start_worker(self):
        if len(self.workers) >= self.workers_max:
            self.logger.warning('Max workers reached [{0}]'.format(len(self.workers)))
            return False

        sub_name = '{0}.{1:03}P'.format(self.name, len(self.workers))
        self.logger.info('Starting worker: {0}'.format(sub_name))
        p = self.get_worker(sub_name)
        self.workers[sub_name] = p
        p.daemon = True
        p.start()
        return True

    def _stop_worker(self, p):
        self.logger.info('Stopping worker: {0}...'.format(p[0]))
        self.send_exit(S1.poller_channel_name(p[0]))
        p[1].join()

    def stop_worker(self):
        if not self.workers:
            self.logger.warning('No workers to stop!')
            return False

        p = self.workers.popitem()
        self._stop_worker(p)
        return True
