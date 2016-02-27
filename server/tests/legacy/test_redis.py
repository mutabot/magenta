from core import data

__author__ = 'Supa'
from utils import config
import argparse
import logging
import os


class Main:
    def __init__(self, logger, db):
        self.logger = logger
        self.data = db

    def run(self):
       # removed as outdated
        pass


if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='G+RSS.Poller')
    parser.add_argument('--redis_port', default=6379, type=int)
    parser.add_argument('--redis_host', default='127.0.0.1')
    parser.add_argument('--redis_db', default=0, type=int)
    parser.add_argument('--max_results', default=4, type=int)
    parser.add_argument('--log_path', required=True)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)

    logger.addHandler(config.getLogHandler(os.path.join(args.log_path, 'test_redis.log')))
    logger.level = logging.DEBUG

    data = data.Data(logger=logger, redis_host=args.redis_host, redis_port=args.redis_port, redis_db=args.redis_db)

    main = Main(logger, data)
    main.run()