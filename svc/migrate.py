import argparse
import logging
import os

from tornado.ioloop import IOLoop

import core
from utils import config
from utils.data_copy_dynamo import DataCopyDynamo

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='G+RSS.Data.Migration')
    parser.add_argument('--src_port', default=6379, type=int)
    parser.add_argument('--src_host', default='127.0.0.1')
    parser.add_argument('--src_db', required=True, type=int)
    parser.add_argument('--dst_port', default=6379, type=int)
    parser.add_argument('--dst_host', default='127.0.0.1')
    parser.add_argument('--dst_db', required=True, type=int)
    parser.add_argument('--log_path', required=True)
    parser.add_argument('--gid', required=False)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger('migrateLogger')
    logger.addHandler(config.getLogHandler(os.path.join(args.log_path, 'migrate.log')))
    logger.level = logging.DEBUG

    src_data = core.Data(logger, args.src_host, args.src_port, args.src_db)
    dst_data = core.DataDynamo(
        logger,
        dynamo_connection={
            'profile_name': 'test',
            'region_name': 'us-east-1',
            'endpoint_url': "http://localhost:9000",
            'table_prefix': 'DEV__'
        },
        redis_connection={
            'host': args.dst_host,
            'port': args.dst_port,
            'db': args.dst_db
        }
    )

    cp = DataCopyDynamo(logger, src_data, dst_data, args.gid or None)

    result = IOLoop.current().run_sync(cp.run)
    # cp.run(args.gid)

    # migrate = DataMigrate(logger, src_data, dst_data)
    # migrate.migrate()
    # grep = DataGrep(logger, dst_data)
    # grep.multiple_parents()
