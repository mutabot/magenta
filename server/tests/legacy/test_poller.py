from email import utils
import json
import logging
import os
import argparse
from providers.google_rss import GoogleRSS
from services.poller import Poller
from utils import config
from core.data import Data


class GooglePollMock:

    def __init__(self, logger, data):
        self.logger = logger
        self.data = data
        self.files = ['data/plus_sample_0.json', 'data/plus_sample_1.json', 'data/plus_sample_2.json']

    def get_next_file(self):
        for file_name in self.files:
            yield file_name

    def get_activities(self):
        json_data = open(self.get_next_file().next())
        activities_doc = json.load(json_data)
        gid = activities_doc['items'][0]['actor']['id']
        return activities_doc, gid

    def poll(self, gid_set):
        self.logger.warning('poll: [{0}]'.format(gid_set))

        # activities_doc, gid = self.get_activities()

        #if activities_doc:
        #    updated =GoogleRSS.get_update_timestamp(activities_doc)
        #    if updated:
        #        self.logger.info('Received data updated [{0}]'.format(utils.formatdate(updated)))
        #    else:
        #        self.logger.info('Received empty data set')

        #    #store the dataset
        #    self.data.chache.cache_activities_doc(gid, activities_doc, updated)
        #    #notify publishers
        #    self.data.flush_updates(gid)

        return []


def main():
    parser = argparse.ArgumentParser(prog='G+RSS.Poller')
    parser.add_argument('--redis_port', default=6379, type=int)
    parser.add_argument('--redis_host', default='127.0.0.1')
    parser.add_argument('--redis_db', default=0, type=int)
    parser.add_argument('--log_path', required=True)
    parser.add_argument('--config_path', required=True)
    parser.add_argument('--max_results', default=4, type=int)
    parser.add_argument('--name', required=True)
    parser.add_argument('--period', default=900, type=int)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.addHandler(config.getLogHandler(os.path.join(args.log_path, 'poller_test.log')))
    logger.level = logging.DEBUG

    data = Data(logger, args.redis_host, args.redis_port, args.redis_db)
    providers = {'google': GooglePollMock(logger, data)}

    pol = Poller(logger=logger,
                 name=args.name,
                 data=data,
                 providers=providers)

    pol.poll(args.period)


if __name__ == '__main__':
    main()