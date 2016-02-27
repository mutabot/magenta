import os
import logging

import argparse

import core
from utils import config
from utils.data_dump import DataDump


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='G+RSS.Data.Migration')
    parser.add_argument('--redis_port', default=6379, type=int)
    parser.add_argument('--redis_host', default='127.0.0.1')
    parser.add_argument('--redis_db', required=True, type=int)
    parser.add_argument('--log_path', required=True)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger('migrateLogger')
    logger.addHandler(config.getLogHandler(os.path.join(args.log_path, 'migrate.log')))
    logger.level = logging.DEBUG
    logger.propagate = 0

    data = core.Data(logger, args.redis_host, args.redis_port, args.redis_db)

    dump = DataDump(logger, data)
    dump.dump()