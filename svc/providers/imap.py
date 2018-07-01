import email
import imaplib
import json
import os
from bs4 import BeautifulSoup
from core import DataDynamo


class IMAPPuller(object):
    def __init__(self, logger, db, config_path):
        """
        @type db: DataDynamo
        @type logger: Logger
        """
        self.logger = logger
        self.db = db
        try:
            f = open(os.path.join(config_path, 'imap-pull.json'))
            self.config = json.load(f)
            self.logger.debug('IMAP module config: {0}'.format(self.config))
        except Exception as e:
            self.logger.error('Failed to initialize IMAP module: {0}'.format(e))

    def is_dummy(self):
        try:
            return bool(self.config['dummy'])
        except:
            pass

        return True

    def fetch(self):
        """
        Pulls and parses emails to extract Google ID of original sharer and first mentioned person ID
        @return: list of tuples (gid, page_id)
        """
        # dummy accounts must not proceed
        if self.config['dummy']:
            return

        imap_server = imaplib.IMAP4_SSL(self.config['host'], self.config['port'])
        imap_server.login(self.config['login'], self.config['password'])
        imap_server.select('Plus')

        status, email_ids = imap_server.uid('search', None, '(UNSEEN)')

        pages = []
        for e_id in email_ids[0].split():
            _, response = imap_server.uid('fetch', e_id, '(RFC822)')
            # parse method will append pages if parse is successful
            if not response or not response[0] or not response[0][1]:
                self.logger.info('IMAP WARN: Invalid response for message {0}'.format(e_id))
                continue

            self.parse(response[0][1], pages)

        imap_server.close()

        return pages

    def parse(self, msg, pages):
        """
        @param msg: email message
        @return: a tuple (gid, page_id) where gid is a Google User ID mentioned in the
        email and page_id is a Google Plus ID of a sender of the message
        """
        e = email.message_from_string(msg)

        self.logger.info('IMAP parsing message: {0}, From {1}'.format(e.get('Subject'), e.get('From')))

        page_id = e.get('X-Sender-ID')

        if not page_id:
            self.logger.warning('Google ID not found in message {0}'.format(e.as_string()))
            return None

        for part in e.walk():
            ct = part.get_params('Content-Type')
            if ct and ('text/html', '') in ct:
                html = part.get_payload(decode=True)
                if html:
                    soup = BeautifulSoup(html)
                    a = soup.find('a', class_='proflink')
                    if a:
                        gid = a.get('oid')
                        self.logger.info('IMAP message parse success: gid:{0}, page:{1}'.format(gid, page_id))
                        pages.append((gid, page_id))
                        return

        self.logger.info('WARN: IMAP message parse found no page:user links')