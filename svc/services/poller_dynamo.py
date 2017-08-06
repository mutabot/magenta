import random
import threading
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from core import DataDynamo
from providers.google_poll import GooglePollAgent
from utils import config


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
        self.data = DataDynamo(logger, dynamo_connection={
            'region_name': 'us-east-1',
            'endpoint_url': "http://localhost:9000",
            'aws_access_key_id': 'foo',
            'aws_secret_access_key': 'bar'
        })

        self.client = boto3.resource('dynamodb',
                                     region_name='us-east-1',
                                     endpoint_url="http://localhost:9000",
                                     aws_access_key_id='foo',
                                     aws_secret_access_key='bar'
                                     )
        self.table = self.client.Table('GidSet')

        cfg = config.load_config(config_path, 'poller.json')
        self.gid_poll_s = cfg['gid_poll_s'] if 'gid_poll_s' in cfg else self.gid_poll_s
        self.period_s = cfg['period_s'] if 'period_s' in cfg else self.period_s
        self.workers_min = cfg['workers_min'] if 'workers_min' in cfg else self.workers_min
        self.workers_max = cfg['workers_max'] if 'workers_max' in cfg else self.workers_max

        self.google_poll = GooglePollAgent(logger, data, config_path)

    def run(self, *args, **kwargs):
        self.logger.info(
            'Poller(d) v[{0}], name=[{1}], poll delay=[{2}]s, period=[{3}]s starting...'.format(config.version,
                                                                                                self.name,
                                                                                                self.gid_poll_s,
                                                                                                self.period_s))

        random.seed(time.time())

        exit_flag = threading.Event()
        while not exit_flag.wait(timeout=1):
            self.poll()

    def poll(self):
        stamp = Decimal(time.time() - self.gid_poll_s)

        poll_due_set = self.table.query(
            IndexName='PollIndex',
            Limit=1,
            KeyConditionExpression=Key('active').eq('true') & Key('refreshStamp').lt(stamp)
        )

        self.logger.info('Polling {0} items'.format(poll_due_set['Count']))
        if poll_due_set['Count'] == 0:
            sleep_sec = self.period_s + (random.randint(2, 4) * 0.1)
            self.logger.info('No items to poll, waiting {0}s'.format(sleep_sec))
            time.sleep(sleep_sec)
        else:
            for item in poll_due_set['Items']:
                gid = item['gid']
                try:
                    document = self.google_poll.fetch(gid)
                    if self.data.cache_activities_doc(gid, document, self.gid_poll_s / 3.0):
                        # TODO: build user activity map and notify publishers
                        self.logger.info('{0}: notifying publishers (dummy)'.format(gid))
                    else:
                        self.logger.info('{0}: Same document, no-op'.format(gid))
                except Exception as ex:
                    self.logger.info('{0}: Poll failed {1}'.format(gid, ex.message))
