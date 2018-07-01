import json
from logging import Logger
import re
import traceback
import twython

from providers.publisher_base import PublisherBase
from utils import config
from core import DataDynamo
from core.model import SocialAccount, RootAccount


# noinspection PyBroadException
class TwitterPublisher(PublisherBase):
    def __init__(self, log, data, config_path):
        """
        @type data: DataDynamo
        @type log: Logger
        """
        PublisherBase.__init__(self, 'twitter', log, data, config_path)
        # init twitter keys
        fb_data = config.load_config(config_path, 'twitter_credentials.json')
        self.twitter_consumer_key = fb_data['twitter_consumer_key']
        self.twitter_consumer_secret = fb_data['twitter_consumer_secret']

        self.dummy = fb_data['dummy'] if 'dummy' in fb_data else False
        self.log.info('[{0}] Loaded config key: {1}, secret: {2}, dummy: {3}'.format(self.name,
                                                                                     self.twitter_consumer_key,
                                                                                     self.twitter_consumer_secret,
                                                                                     self.dummy))

        self.max_tweet = 140
        self.first_link_len = 30
        self.link_len = 23

    def is_dummy(self):
        return self.dummy

    def get_root_endpoint(self):
        return "api.twitter.com"

    def register_destination(self, user):
        """

        @type user: SocialAccount
        """
        token = self.get_token(user)
        if not token:
            self.log.error('Twitter access token is invalid for [{0}]'.format(user.Key))
            return False
        else:
            self.log.info('Success: Twitter access token for [{0}]'.format(user.Key))

        return True

    def _get_client(self, token):
        return twython.Twython(self.twitter_consumer_key, self.twitter_consumer_secret, token['key'], token['secret'])

    @staticmethod
    def _get_len_strip_links(message, max_len):
        r = re.compile(r"(https?://[^ ]+)")
        links = r.finditer(message)

        for m in links:
            if m.start() < max_len < m.end():
                max_len = m.start()
                break

        return max_len

    def _format_tweet(self, message, self_url, url=None, extra_trim=0, force_trim=False):
        # long tweet
        if len(message) > self.max_tweet:
            max_len = self.max_tweet - self.first_link_len - extra_trim
            # strip links past max_len
            max_len = self._get_len_strip_links(message, max_len)
            message = message[:max_len] + u'... {0}'.format(self_url)

        # short tweet with link
        elif url:
            max_len = self.max_tweet - self.first_link_len - extra_trim
            # strip links past max_len
            max_len = self._get_len_strip_links(message, max_len)
            message = message[:max_len] + u'{0} {1}'.format(u'...' if len(message) > max_len else u'', url or u'')

        # picture poster must trim for picture url
        elif force_trim:
            max_len = self.max_tweet - self.first_link_len
            # strip links past max_len
            max_len = self._get_len_strip_links(message, max_len)
            message = message[:max_len] + u'{0}'.format(u'...' if len(message) > max_len else u'')

        # short tweet no link
        return message.encode('utf-8', 'ignore')

    def publish_album(self, user, album, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        # publish as a link with photo
        try:
            thumb = next((image for image in album['images'] if image['media_types'] == {'image'}), None)
            # fallback to link post if
            if not thumb:
                return self.publish_link(user, feed, message, message_id, token)

            # post image with link
            client = self._get_client(token)
            status = self._format_tweet(feed['description'], feed['self_url'], feed['self_url'],
                                        extra_trim=self.link_len, force_trim=True)
            u, _ = self._download_image(thumb['url'])
            if not u:
                return None

            result = client.post('/statuses/update_with_media', params={'status': status, 'media': u})

            # close the handle
            u.close()
            self.log.info('Posted photo, result: {0}'.format(result))
            return result

        except Exception as e:
            self.log.error('ERROR: Exception while publish_album, {0}'.format(e))

        return None

    def publish_photo(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        result = None
        try:
            client = self._get_client(token)
            # extra offset for second link
            status = self._format_tweet(feed['description'], feed['self_url'], extra_trim=self.link_len, force_trim=True)
            u, _ = self._download_image(feed['fullImage'])
            if not u:
                return result

            result = client.post('/statuses/update_with_media', params={'status': status, 'media': u})

            # close the handle
            u.close()

            self.log.info('Posted photo, result: {0}'.format(result))

        except Exception as e:
            self.log.error('ERROR: Exception while update_with_media, {0}'.format(e))
            return None
            # this will cause publish_link to be called

        return result

    def _update_status(self, token, message, self_url, url=None):
        client = self._get_client(token)
        status = self._format_tweet(message, self_url, url)

        try:
            result = client.update_status(status=status)
        except twython.TwythonError as twe:
            self.log.error('ERROR: Exception while client.update_status, {0}'.format(twe))

            # re-try with shorter trim
            status = self._format_tweet(message, self_url, url, extra_trim=self.first_link_len, force_trim=True)
            result = client.update_status(status=status)

        return result

    def publish_text(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        result = self._update_status(token, feed['description'], feed['self_url'])
        self.log.info('Posted text, result: {0}'.format(result))
        return result

    def publish_link(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        result = self._update_status(token, feed['description'], feed['self_url'], feed['link'])
        self.log.info('Posted link, result: {0}'.format(result))
        return result

    def process_result(self, message_id, result, user, log_func):
        """

        @type user: SocialAccount
        """
        if not result:
            return None
        elif 'id_str' in result:
            return result['id_str']

        log_message = 'Warning: Publish to Twitter, result: {0}'
        log_message = log_message.format(result)
        log_func(log_message)
        return None

    def is_delete_message(self, user, feed):
        # always delete messages for edit
        return True

    def is_expand_buzz(self):
        # never expand "timeline"/"buzz" albums
        return False

    def delete_message(self, user, message_id, token):
        """

        @type user: SocialAccount
        """
        try:
            client = self._get_client(token)
            result = client.destroy_status(id=message_id)
            self.log.info('Deleted post, result: {0}'.format(result))
            return True
        except:
            self.log.error('Failed to delete post: {0}'.format(traceback.format_exc()))
            return False
