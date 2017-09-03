import argparse
import time
from core import data_dynamo
from utils import config


def get_service(service, log, name, data_svc, providers, config_path, dummy):
    if service == 'poller':
        from services.poller import Poller
        return Poller(log, name, data_svc, providers, config_path, dummy)
    elif service == 'poller_dynamo':
        from services.poller_dynamo import Poller
        return Poller(log, name, data_svc, providers, config_path, dummy)
    elif service == 'publisher':
        from services.publisher import Publisher
        return Publisher(log, name, data_svc, providers, config_path, dummy)
    elif service == 'queue':
        from services.queue import Queue
        return Queue(log, name, data_svc, providers, config_path, dummy)
    elif service == 'misc':
        from services.misc import MiscService
        return MiscService(log, name, data_svc, providers, config_path, dummy)

    raise NotImplementedError('Unknown service')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='G+RSS Service Wrapper')

    parser.add_argument('--redis_port', default=6379, type=int)
    parser.add_argument('--redis_host', default='127.0.0.1')
    parser.add_argument('--redis_db', default=0, type=int)
    parser.add_argument('--dynoris_url', required=True, type=str)
    parser.add_argument('--log_path', required=True)
    parser.add_argument('--provider', required=False, default='')
    parser.add_argument('--service', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--config_path', required=True)
    parser.add_argument('--dummy', default=False, type=bool)
    args = parser.parse_args()

    logger = config.get_logger(args.log_path, args.name)

    db = data_dynamo.DataDynamo(
        logger=logger,
        dynamo_connection={
            'profile_name': args.aws_profile_name,
            'endpoint_url': args.aws_endpoint_url,
            'region_name': args.aws_region_name
        },
        redis_connection={
            'host': args.redis_host,
            'port': args.redis_port,
            'db': args.redis_db
        }
    )

    # wait for redis
    logger.info('Waiting for redis loading...')
    while db.is_loading():
        time.sleep(0.5)
    logger.info('... Redis loaded')

    logger.info('Starting [{0}] ...'.format(args.service))
    # create job
    job = get_service(args.service, logger, args.name, db, args.provider.split(','), args.config_path, args.dummy)

    # run until interrupted
    kwargs = {a: b for a, b in args._get_kwargs()}
    job.run(**kwargs)
    logger.warning('Process exit!')