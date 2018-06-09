import json
import os
import socket
import time
from httplib import BadStatusLine
from logging import Logger

import bitly_api


class BitlyShorten(object):
    def __init__(self, logger, config_path):
        """

        @type logger: Logger
        """
        self.logger = logger
        self.config_path = config_path

        self.http = None
        self.auth_time = time.time()

        # Authenticate and construct service.
        # Prepare credentials, and authorize HTTP object with them.
        # use oauth2 endpoints
        try:
            f = open(os.path.join(config_path, 'bitly_secrets.json'))
            self.config = json.load(f)
            self.logger.debug('Bitly module config: {0}'.format(self.config))

            self.service = bitly_api.Connection(access_token=self.config['access_token'])
        except Exception as e:
            self.logger.error('Failed to initialize Bitly module: {0}'.format(e))

        # '345761ace0235557422ae381f3bae52896aa7513')

    def get_short_url(self, long_url):
        try:
            result = self.service.shorten(long_url)

            return result['url'] if result and 'url' in result else long_url

        except BadStatusLine as e:
            self.logger.warning('BadStatusLine: {0}'.format(e.line))

        except socket.error as e:
            self.logger.warning('Socket error: {0}'.format(e))

        except Exception as e:
            self.logger.warning('URL Shortener exception: {0}:{1}'.format(type(e), e))

        return long_url
