import os
import socket
import time
from httplib import BadStatusLine
from logging import Logger

import httplib2
from googleapiclient import discovery, errors
from oauth2client.file import Storage
from oauth2client.service_account import ServiceAccountCredentials


class GoogleShorten(object):
    def __init__(self, logger, config_path):
        """

        @type logger: Logger
        """
        self.logger = logger
        self.config_path = config_path
        self.service = None
        self.http = None
        self.auth_time = time.time()

        # Authenticate and construct service.
        # Prepare credentials, and authorize HTTP object with them.
        try:
            os.unlink(os.path.join(config_path, 'shortner.dat'))
        except:
            pass
        storage = Storage(os.path.join(config_path, 'shortner.dat'))
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            os.path.join(config_path, 'shortner_secrets.json'),
            scopes='https://www.googleapis.com/auth/urlshortener')

        self.credentials.set_store(storage)

    def authorize(self):
        if self.service is None or time.time() - self.auth_time > 300:
            self.logger.info('URL Shortener: authorizing credentials')
            self.http = self.credentials.authorize(http=httplib2.Http())
            # Construct a service object via the discovery service.
            self.service = discovery.build('urlshortener', 'v1', http=self.http)
            self.auth_time = time.time()

    def get_short_url(self, long_url):
        try:
            if self.credentials is None or self.credentials.invalid:
                self.logger.error('URL Shortener credentials are invalid')
                return long_url
                # check auth
            self.authorize()

            # query data from google
            body = {'longUrl': long_url.encode('utf-8', 'ignore')}
            request = self.service.url().insert(body=body)
            response = request.execute()
            if response and 'id' in response:
                self.logger.debug('URL Shortener: [{0}] --> [{1}]'.format(long_url, response['id']))
                return response['id']

            self.logger.warning('URL Shortener: Invalid response [{0}] --> [{1}]'.format(long_url, response))
            return long_url

        except errors.HttpError as e:
            self.logger.warning('HttpError: {0}'.format(e.resp))

        except BadStatusLine as e:
            self.logger.warning('BadStatusLine: {0}'.format(e.line))

        except socket.error as e:
            self.logger.warning('Socket error: {0}'.format(e))

        except Exception as e:
            self.logger.warning('URL Shortener exception: {0}:{1}'.format(type(e), e))

        return long_url