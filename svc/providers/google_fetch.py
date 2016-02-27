import os
import socket
import time
import traceback
from httplib import BadStatusLine

import httplib2
import tornado.web
from apiclient import discovery, errors
from oauth2client.file import Storage
from oauth2client.service_account import ServiceAccountCredentials


class GoogleFetchRetry(Exception):
    pass


class GoogleFetch(object):
    def __init__(self, logger, config_path):
        self.logger = logger
        self.config_path = config_path
        self.service = None
        self.http = None
        self.auth_time = time.time()

        # Authenticate and construct service.
        # Prepare credentials, and authorize HTTP object with them.
        try:
            os.unlink(os.path.join(config_path, 'plus.dat'))
        except:
            pass
        storage = Storage(os.path.join(config_path, 'plus.dat'))

        self.logger.warning('GoogleFetch: Initializing credentials')
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            os.path.join(config_path, 'secrets.json'),
            scopes='https://www.googleapis.com/auth/plus.me')

        self.credentials.set_store(storage)

    def authorize(self):
        if self.service is None or time.time() - self.auth_time > 300:
            self.logger.info('Authorizing credentials')
            self.http = self.credentials.authorize(http=httplib2.Http())
            # Construct a service object via the discovery service.
            self.service = discovery.build('plus', 'v1', http=self.http)
            self.auth_time = time.time()

    def get_plus_user_info(self, user_name):
        try:
            if self.credentials is None or self.credentials.invalid:
                raise tornado.web.HTTPError(403, 'Invalid Credentials')
            self.authorize()

            # query data from google
            request = self.service.people().get(userId=user_name)
            person_doc = request.execute()

        except errors.HttpError as e:
            self.logger.warning('HttpError: {0}'.format(e.resp))
            return None

        except BadStatusLine as e:
            self.logger.warning('BadStatusLine: {0}'.format(e.line))
            raise GoogleFetchRetry()

        except socket.error as e:
            self.logger.warning('Socket error: {0}'.format(e))
            raise GoogleFetchRetry()

        except Exception as e:
            self.logger.warning('get_plus_user_info for [{0}]: exception: {1}, {2}'.format(user_name, e, traceback.format_exc()))
            return None

        return person_doc

    def get_activities(self, user_id, max_results):
        try:
            if self.credentials is None or self.credentials.invalid:
                raise tornado.web.HTTPError(403, 'Invalid Credentials')
            self.authorize()

            # query data from google
            request = self.service.activities().list(userId=user_id, collection='public', maxResults=max_results)
            activities_doc = request.execute()

        except errors.HttpError as e:
            self.logger.warning('HttpError: {0}'.format(e.resp))
            return None

        except BadStatusLine as e:
            self.logger.warning('BadStatusLine: {0}'.format(e.line))
            raise GoogleFetchRetry()

        except socket.error as e:
            self.logger.warning('Socket error: {0}'.format(e))
            raise GoogleFetchRetry()

        except Exception as e:
            self.logger.warning('get_activities for [{0}]: exception: {1}, {2}'.format(user_id, e, traceback.format_exc()))
            return None

        return activities_doc

    @staticmethod
    def get_user_info(credentials):
        """
        Requests basic user information associated with credentials
        @param credentials: Google OAuth2 credentials
        @return: basic user information
        """
        http = credentials.authorize(http=httplib2.Http())
        service = discovery.build('oauth2', 'v2', http=http)
        request = service.userinfo().v2().me().get()
        return request.execute()