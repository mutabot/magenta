from email import utils
import json
import logging
import os
import argparse
from providers.google_rss import GoogleRSS
from providers.picasa import Picasa
from services.poller import Poller
from utils import config
from core.data import Data


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

    picasa = Picasa(logger, args.config_path)

    album = picasa.get_album('113347540216001053968', '5963913461943227665')

    print(album)


if __name__ == '__main__':
    main()