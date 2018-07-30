import json
from logging import Logger
from tornado import httpclient
from tornado.httpclient import HTTPRequest
import urllib
from providers.publisher_base import PublisherBase
from utils import config
from core import DataDynamo
from core.model import SocialAccount, RootAccount
from providers import PublisherContext


# noinspection PyBroadException
class LinkedInPublisher(PublisherBase):
    PERSONAL_URL = "https://api.linkedin.com/v1/people/~/shares"
    COMPANY_URL = "https://api.linkedin.com/v1/companies/{0}/shares"

    def __init__(self, log, data, config_path):
        """
        @type data: DataDynamo
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

    def _get_share_url(self, user):
        """

        @type user: SocialAccount
        """
        if user.pid.startswith('CMP$'):
            return self.COMPANY_URL.format(user.pid[4:])

        return self.PERSONAL_URL

    def get_user_param(self, user, param):
        """

        @type user: SocialAccount
        """
        # albums to be posted as links
        if param in ['album_links']:
            return True
        return user.options[param] if param in user.options else None

    def register_destination(self, context):
        """

        @type context: PublisherContext
        """
        token = self.get_token(context.target)
        if not token:
            self.log.error('linkedin access token is invalid for [{0}]'.format(context.target.Key))
            return False
        else:
            self.log.info('Success: Found linkedin access token for [{0}]'.format(context.target.Key))

        return True

    def publish_album(self, user, album, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        self.log.error('ERROR: linkedin.publish_album(), albums are not supported')
        return None

    def publish_photo(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        return self.publish_link(user, feed, message, message_id, token)

    def publish_text(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
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
        """

        @type user: SocialAccount
        """
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

    def process_result(self, message_id, result, user, log_func, context):
        """

        @type user: SocialAccount
        """
        if not result:
            return None

        if result == 'unsupported':
            # skipped as not supported
            return result

        try:
            r = json.loads(result)
            if not (r and 'updateKey' in r):
                log_message = 'Warning: Publish to LinkedIn [{0}], result[{1}]'.format(user, result)
                log_func(context, log_message)
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
