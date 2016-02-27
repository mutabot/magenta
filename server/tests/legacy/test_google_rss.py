import argparse
import json
import logging
import os
from email import utils
from tornado.template import Template
from providers import facebook
from providers.google_rss import GoogleRSS
from utils.config import version, getLogHandler

parser = argparse.ArgumentParser(prog='G+RSS.Poller')
parser.add_argument('--log_path', required=True)
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
logger = logging.getLogger(__name__)
logger.addHandler(getLogHandler(os.path.join(args.log_path, 'test_google.log')))
logger.level = logging.INFO

f = open('templates/feed.xml')
template = Template(f.read())
f.close()
json_data = open('data/113347540216001053968.json')
data = json.load(json_data)
#print(data)
items = GoogleRSS.gen_items(data, option='photo')
print(template.generate(version=version, gid='UNIT_TEST', pubDate=utils.formatdate(), items=items))
#for item in items:
#    #message = facebook.FacebookPublisher._format_message(item['description'])
#    if item['type'] in ('album', 'photo'):
#        print({'photo_id': item['photo_id'], 'album_id': item['album_id']})
