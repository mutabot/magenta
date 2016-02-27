import imaplib
import json
import logging
import os

import argparse
from bs4 import BeautifulSoup
from providers.imap import IMAPPuller

from utils import config
from core import data
from email import parser, email


def imap_fetch(config_path):
    json_data = open(os.path.join(config_path, 'imap-pull.json'))
    d = json.load(json_data)
    json_data.close()
    imap_server = imaplib.IMAP4_SSL(d['host'], d['port'])
    imap_server.login(d['login'], d['password'])
    imap_server.select('Plus')
    status, email_ids = imap_server.search(None, '(UNSEEN)')
    print email_ids
    for e_id in email_ids[0].split():
        _, response = imap_server.fetch(e_id, '(RFC822)')
        print(response[0][1])


def parse_email(config_path):
    json_data = open(os.path.join('data/', 'imap_sample.txt'))
    msg = json_data.read()
    json_data.close()

    e = email.message_from_string(msg)

    for part in e.walk():
        ct = part.get_params('Content-Type')
        if ct and ('text/html', '') in ct:
            html = part.get_payload(decode=True)
            print(html)
            soup = BeautifulSoup(html)
            aa = soup.find_all('a', class_='proflink')
            for a in aa:
                print(a)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='G+RSS.Test.IMAP')
    parser.add_argument('--redis_port', default=6379, type=int)
    parser.add_argument('--redis_host', default='127.0.0.1')
    parser.add_argument('--redis_db', default=0, type=int)
    parser.add_argument('--log_path', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--config_path', required=True)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.addHandler(config.getLogHandler(os.path.join(args.log_path, args.name + '.log')))
    logger.level = logging.INFO

    db = data.Data(logger, args.redis_host, args.redis_port, args.redis_db)

    im = IMAPPuller(logger, db, args.config_path)
    im.fetch()

    #imap_fetch(args.config_path)
    #parse_email(args.config_path)
