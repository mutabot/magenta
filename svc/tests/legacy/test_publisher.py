import json
import logging
import os
import argparse
from providers.facebook import FacebookPublisher
from providers.flickr import FlickrPublisher
from providers.google_rss import GoogleRSS
from providers.linkedin import LinkedInPublisher
from providers.mail import MailPublisher
from providers.picasa import Picasa
from providers.publisher_base import PublisherBase
from providers.px500 import Px500Publisher
from providers.tumblr import TumblrPublisher
from providers.twitter import TwitterPublisher
from services.publisher import Publisher
from utils import config
from core import data


class FacebookMock(PublisherBase):
    def __init__(self, name, log, data, config_path):
        PublisherBase.__init__(self, name, log, data, config_path)

def get_items(sample_file):
    json_data = open(sample_file)
    d = json.load(json_data)
    json_data.close()
    items = d['items']
    items.sort(key=lambda item: GoogleRSS.get_timestamp(item['published']))
    return items


class PicasaMock(Picasa):
    def __init__(self, logger, config_path):
        super(PicasaMock, self).__init__(logger, config_path)

    def get_album(self, user_id, album_id):
        json_data = open('data/album.json')
        return self.format_album(json.load(json_data, encoding='utf-8'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='G+RSS.Publisher')
    parser.add_argument('--redis_port', default=6379, type=int)
    parser.add_argument('--redis_host', default='127.0.0.1')
    parser.add_argument('--redis_db', default=0, type=int)
    parser.add_argument('--log_path', required=True)
    parser.add_argument('--provider', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--config_path', required=True)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.addHandler(config.getLogHandler(os.path.join(args.log_path, args.name + '.log')))
    logger.level = logging.INFO

    db = data.Data(logger, args.redis_host, args.redis_port, args.redis_db)
    publisher = FacebookPublisher(logger, db, args.config_path)
    #publisher.send_email_notification('115788445920947013565', '839482846112313', 'Publish to {0} failed'.format(publisher.name.title()), 'publisher_error')

    #publisher.publish('110631511291382363658')
    publisher.publish_for_user('112219414285466905779', '805906479499445', get_items('../../data/106608083168451074557.json'))
    #publisher = TwitterPublisher(logger, db, args.config_path)
    #publisher.publish_for_user('111780410677417445421', '1621727184723235', get_items('data/115788445920947013565.json'))

    #publisher = FlickrPublisher(logger, db, args.config_path, picasa=PicasaMock(logger, args.config_path))
    #publisher.publish_for_user('115788445920947013565', '95995882@N05', get_items('data/115788445920947013565.json'))
    #publisher = TumblrPublisher (logger, db, args.config_path)
    #publisher.publish_for_user('115788445920947013565', 'mutabox', get_items('data/115788445920947013565.json'))
    #publisher = LinkedInPublisher(logger, db, args.config_path)
    #publisher.publish_for_user('115788445920947013565', 'CMP$3844051', get_items('data/115788445920947013565.json'))
    #publisher = Px500Publisher(logger, db, args.config_path, picasa=PicasaMock(logger, args.config_path))
    #publisher.publish_for_user('115788445920947013565', '248631', get_items('data/115788445920947013565.json'))


    #job = Publisher(logger=logger,
    #                name=args.name,
    #                data=data,
    #                providers={'facebook': FacebookMock(logger, data, args.config_path)})
    #
    #job.run()