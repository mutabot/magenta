from utils import config
import time
import threading
import boto3



class Poller(object):

    def __init__(self, logger, name, data, providers, config_path, dummy=False):
        """
        @param logger:
        @param name:
        @param data:
        @param providers:
        @param config_path:
        @param dummy:
        """
        self.logger = logger
        self.name = name
        self.client = boto3.client('dynamodb')


    def run(self, *args, **kwargs):
        self.kwargs = kwargs
        cfg = config.load_config(kwargs['config_path'], 'poller.json')
        self.gid_poll_s = cfg['gid_poll_s'] if 'gid_poll_s' in cfg else self.gid_poll_s
        self.period_s = cfg['period_s'] if 'period_s' in cfg else self.period_s
        self.workers_min = cfg['workers_min'] if 'workers_min' in cfg else self.workers_min
        self.workers_max = cfg['workers_max'] if 'workers_max' in cfg else self.workers_max

        self.logger.info('Poller(d) v[{0}], name=[{1}], poll delay=[{2}]s, period=[{3}]s starting...'.format(config.version, self.name, self.gid_poll_s, self.period_s))

        exit_flag = threading.Event()
        while not exit_flag.wait(timeout=1):
            self.poll()

    def poll(self):
        self.client.


