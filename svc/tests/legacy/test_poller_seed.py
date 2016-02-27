import logging
import os
from random import randint
import argparse
import time
from core.schema import S1
from utils import config
from core import data

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='G+RSS. Poller Seeder')
    parser.add_argument('--redis_port', default=6379, type=int)
    parser.add_argument('--redis_host', default='127.0.0.1')
    parser.add_argument('--redis_db', default=0, type=int)
    parser.add_argument('--log_path', required=True)
    parser.add_argument('--gid_set', required=True)
    parser.add_argument('--period', default=60, type=int)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.addHandler(config.getLogHandler(os.path.join(args.log_path, 'poller_test.log')))
    logger.level = logging.DEBUG

    data = data.Data(logger, args.redis_host, args.redis_port, args.redis_db)

    while True:
        logger.warning('Invoking poll for all, next poll in {0} seconds'.format(args.period))
        with open(args.gid_set) as f_set:
            gid_set = [gid.strip() for gid in f_set.readlines()]

        logger.info('Read [{0}] gids'.format(len(gid_set)))
        for n in range(0, len(gid_set)):
            gid = gid_set[randint(0, len(gid_set) - 1)]
            logger.info('Invoking rebalance for [{0}]'.format(gid))
            data.rc.sadd(S1.register_set(), gid)
            data.register_gid(gid)
            t = randint(5, 20)
            logger.info('Sleeping for [{0}]'.format(t))
            time.sleep(t)
        #get delay and wait
        time.sleep(args.period)
