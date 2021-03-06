import json
from logging import Logger
from tornado import httpclient
from tornado.httpclient import HTTPRequest
import urllib
from providers.publisher_base import PublisherBase
from utils import config
from core import Data


# noinspection PyBroadException
class LinkedInPublisher(PublisherBase):
    PERSONAL_URL = "https://api.linkedin.com/v1/people/~/shares"
    COMPANY_URL = "https://api.linkedin.com/v1/companies/{0}/shares"

    def __init__(self, log, data, config_path):
        """
        @type data: Data
        @type log: Logger
        """
        PublisherBase.__init__(self, 'linkedin', log, data, config_path)
        # init linkedin keys
        cfg = config.load_config(config_path, 'linkedin_credentials.json')
        self.consumer_key = cfg['consumer_key'].encode(encoding='utf-8', errors='ignore')
        self.consumer_secret = cfg['consumer_secret'].encode(encoding='utf-8', errors='ignore')
        self.dummy = cfg['dummy'] if 'dummy' in cfg else False
        self.log.info('[{0}] Loaded config key: {1}, secret: {2}, dummy: {3}'.format(self.name,
                                                                                     self.consumer_key,
                                                                                     self.consumer_secret,
                                                                                     self.dummy))

    def is_dummy(self):
        return self.dummy

    def get_root_endpoint(self):
        return None

    def get_token(self, user):
        token_str = self.data.linkedin.get_user_token(user)
        if not token_str:
            return None
        token = json.loads(token_str)
        return token

    def _get_share_url(self, user):
        if user.startswith('CMP$'):
            return self.COMPANY_URL.format(user[4:])

        return self.PERSONAL_URL

    def get_user_param(self, user, param):
        # albums to be posted as links
        if param in ['album_links']:
            return True
        return self.data.linkedin.get_user_param(user, param)

    def register_destination(self, user):
        token = self.data.linkedin.get_user_token(user)
        if not token:
            self.log.error('linkedin access token is invalid for [{0}]'.format(user))
            return False
        else:
            self.log.info('Success: Found linkedin access token for [{0}]: {1}'.format(user, token))

        return True

    def publish_album(self, user, album, feed, message, message_id, token):
        self.log.error('ERROR: linkedin.publish_album(), albums are not supported')
        return None

    def publish_photo(self, user, feed, message, message_id, token):
        return self.publish_link(user, feed, message, message_id, token)

    def publish_text(self, user, feed, message, message_id, token):

        share_object = {
            "comment": message.encode('utf-8', 'ignore')[:700],
            "visibility": {
                "code": "anyone"
            }
        }
        json_content = json.dumps(share_object)
        headers = {"Content-Type": "application/json"}
        response = self.make_request(self._get_share_url(user), headers, json_content, token)

        return response

    def publish_link(self, user, feed, message, message_id, token):

        content = {
            "title": feed['title'].encode('utf-8', 'ignore')[:200],
            "submitted-url": feed['link'].encode('utf-8', 'ignore'),
        }

        # add thumbnail if supplied
        if 'fullImage' in feed and feed['fullImage']:
            content['submitted-image-url'] = feed['fullImage'].encode('utf-8', 'ignore')

        share_object = {
            "comment": message.encode('utf-8', 'ignore')[:700],
            "content": content,
            "visibility": {
                "code": "anyone"
            }
        }
        json_content = json.dumps(share_object)
        headers = {"Content-Type": "application/json"}
        response = self.make_request(self._get_share_url(user), headers, json_content, token)

        return response

    def process_result(self, gid, message_id, result, user):
        if not result:
            return None

        if result == 'unsupported':
            # skipped as not supported
            return result

        try:
            r = json.loads(result)
            if not (r and 'updateKey' in r):
                log_message = 'Warning: Publish to LinkedIn [{0}] for Google Plus user [{1}], result[{2}]'.format(user, gid, result)
                self.data.add_log(gid, log_message)
                self.log.info(log_message)
                return None

            # str the message id as it is int
            return str(r['updateKey'])
        except Exception as e:
            self.log.error('ERROR: linkedin.process_result(), Failed to parse {0}'.format(e))

        return None

    def is_delete_message(self, user, feed):
        return False

    def make_request(self, url, headers, body, token):
        try:
            client = httpclient.HTTPClient()

            url += "?" + urllib.urlencode({
                "secure-urls": "true",
                "format": "json",
                'oauth2_access_token': token
            })
            request = HTTPRequest(url, method='POST', headers=headers, body=body)
            self.log.info('POST: {0}, {1}'.format(url, body))
            result = client.fetch(request)
            if result.error:
                self.log.error('ERROR: linkedin.make_request(), failed to publish {0}'.format(result.body))
                return None

            return result.body

        except Exception as e:
            self.log.error('ERROR: Exception in linkedin.make_request(), {0}'.format(e))

        return None
