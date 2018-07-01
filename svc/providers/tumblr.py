from logging import Logger
import re
import traceback
import pytumblr

from providers.publisher_base import PublisherBase
from utils import config
from core import DataDynamo
from core.model import SocialAccount, RootAccount


# noinspection PyBroadException
class TumblrPublisher(PublisherBase):
    def __init__(self, log, data, config_path):
        """
        @type data: DataDynamo
        @type log: Logger
        """
        PublisherBase.__init__(self, 'tumblr', log, data, config_path)
        # init tumblr keys
        fb_data = config.load_config(config_path, 'tumblr_credentials.json')
        self.tumblr_consumer_key = fb_data['tumblr_consumer_key']
        self.tumblr_consumer_secret = fb_data['tumblr_consumer_secret']
        self.dummy = fb_data['dummy'] if 'dummy' in fb_data else False
        self.log.info('[{0}] Loaded config key: {1}, secret: {2}, dummy: {3}'.format(self.name,
                                                                                     self.tumblr_consumer_key,
                                                                                     self.tumblr_consumer_secret,
                                                                                     self.dummy))

    def is_dummy(self):
        return self.dummy

    def get_root_endpoint(self):
        return None

    def register_destination(self, user):
        """

        @type user: SocialAccount
        """
        token = self.data.get_token(user)
        if not token:
            self.log.error('Tumblr access token is invalid for [{0}]'.format(user.Key))
            return False
        else:
            self.log.info('Success: Found Tumblr access token for [{0}]'.format(user.Key))

        return True

    def _get_client(self, token):
        return pytumblr.TumblrRestClient(
            self.tumblr_consumer_key,
            self.tumblr_consumer_secret,
            token['key'],
            token['secret']
        )

    def format_message(self, message):
        return re.sub(ur'\n', u'<br />', message)

    def publish_album(self, user, album, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        result = None
        client = self._get_client(token)

        params = {
            'caption': message.encode('utf-8', 'ignore'),
            'tags': [tag.encode('utf-8', 'ignore') for tag in album['tags']],
        }

        if message_id:
            return self.edit_post(client, user, message_id, params)

        # do not expand albums larger than 6 images
        if len(album['images']) > 6:
            self.log.info('Album too big to be expanded, publishing as link...')
            return None

        # post images one by one, photoset functionality is not available via api
        # self.log.info('Posting [{0}] images to album [{1}], tags [{2}]'.format(len(album['images']), album['title'], params['tags']))
        for image in album['images']:
            params['source'] = image['url']
            params['caption'] = image['description'].encode('utf-8', 'ignore')
            result = client.create_photo(user.pid, **params)
            self.log.info('Posted photo to album, result: {0}'.format(result))

        return result

    def publish_photo(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        client = self._get_client(token)
        params = {
            'source': feed['fullImage'],
            'caption': message.encode('utf-8', 'ignore'),
            'tags': [tag.encode('utf-8', 'ignore') for tag in feed['tags']],
        }
        if message_id:
            result = self.edit_post(client, user, message_id, params)
        else:
            result = client.create_photo(user.pid, **params)
        self.log.info('Posted photo, result: {0}'.format(result))
        return result

    def publish_text(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        client = self._get_client(token)
        title = u'{0}...'.format(feed['title'][:16]) if len(feed['title']) > 16 else u''
        params = {
            'title': title.encode('utf-8', 'ignore'),
            'body': message.encode('utf-8', 'ignore'),
            'tags': [tag.encode('utf-8', 'ignore') for tag in feed['tags']],
        }
        if message_id:
            result = self.edit_post(client, user, message_id, params)
        else:
            result = client.create_text(user.pid, **params)
        self.log.info('Posted text, result: {0}'.format(result))
        return result

    def publish_video(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        client = self._get_client(token)

        params = {
            'caption': message.encode('utf-8', 'ignore'),
            'embed': feed['embed']
        }
        if message_id:
            result = self.edit_post(client, user, message_id, params)
        else:
            result = client.create_video(user.pid, **params)

        self.log.info('Posted link, result: {0}'.format(result))
        return result

    def publish_link(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        client = self._get_client(token)

        # add thumbnail if supplied
        if 'fullImage' in feed and feed['fullImage']:
            msg = u'{0}<br /><img src="{1}" style="max-width:100%;">'.format(message, feed['fullImage'])
        else:
            msg = message

        params = {
            'title': feed['title'].encode('utf-8', 'ignore'),
            'description': msg.encode('utf-8', 'ignore'),
            'url': feed['link'].encode('utf-8', 'ignore'),
            'tags': [tag.encode('utf-8', 'ignore') for tag in feed['tags']],
        }
        if message_id:
            result = self.edit_post(client, user, message_id, params)
        else:
            result = client.create_link(user.pid, **params)
        self.log.info('Posted link, result: {0}'.format(result))
        return result

    def process_result(self, message_id, result, user, log_func):
        res = None
        if not result:
            return None
        elif message_id and 'error' not in result:
            res = message_id
        elif 'id' in result:
            # str the message id as it is int
            res = str(result['id'])
        else:
            log_message = 'Warning: Publish to Tumblr [{0}], result[{1}]'.format(user.Key, result)
            log_func(log_message)

        return res

    def edit_post(self, client, user, message_id, params):
        """

        @type user: SocialAccount
        """
        try:
            params['id'] = message_id
            # result = client.edit_post(user, **params)
            # bug in pytumblr
            url = "/v2/blog/%s/post/edit" % user.pid
            result = client.send_api_request('post', url, params,
                                             ['id', 'title', 'url', 'description', 'text', 'body', 'caption', 'link',
                                              'source', 'type', 'data'])
            self.log.info('Edited post, result: {0}'.format(result))
            return result
        except:
            self.log.error('Failed to edit post: {0}'.format(traceback.format_exc()))
            return None

    def is_delete_message(self, user, feed):
        return False

    def delete_message(self, user, message_id, token):
        """

        @type user: SocialAccount
        """
        try:
            client = self._get_client(token)
            result = client.delete_post(user.pid, message_id)
            self.log.info('Deleted post, result: {0}'.format(result))
            return True
        except:
            self.log.error('Failed to delete post: {0}'.format(traceback.format_exc()))
            return False
