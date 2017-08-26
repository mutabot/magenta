import argparse
import logging
import os

import core
from utils import config
from utils.data_model import DataCopyModel

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='G+RSS.Data.Dump')
    parser.add_argument('--src_port', default=6379, type=int)
    parser.add_argument('--src_host', default='127.0.0.1')
    parser.add_argument('--src_db', required=True, type=int)
    parser.add_argument('--log_path', required=True)
    parser.add_argument('--gid', required=False)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger('migrateLogger')
    logger.addHandler(config.getLogHandler(os.path.join(args.log_path, 'migrate.log')))
    logger.level = logging.DEBUG
    #logger.propagate = 0

    data = core.Data(logger, args.src_host, args.src_port, args.src_db)

    dump = DataCopyModel(logger, data)
    if args.gid:
        dump.get_root_account_model(args.gid)
