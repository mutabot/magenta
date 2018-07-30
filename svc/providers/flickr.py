import json
from logging import Logger
import os
import urlparse

from providers.publisher_base import PublisherBase
from utils import config
from core import DataDynamo
from core.model import SocialAccount
from lib import flickr_api
from lib.flickr_api import auth


# noinspection PyBroadException
class FlickrPublisher(PublisherBase):
    def __init__(self, log, data, config_path, picasa=None):
        """
        @type data: DataDynamo
        @type log: Logger
        """
        PublisherBase.__init__(self, 'flickr', log, data, config_path, picasa=picasa)
        # init flickr keys
        fb_data = config.load_config(config_path, 'flickr_credentials.json')
        self.flickr_consumer_key = fb_data['flickr_consumer_key'].encode(encoding='utf-8', errors='ignore')
        self.flickr_consumer_secret = fb_data['flickr_consumer_secret'].encode(encoding='utf-8', errors='ignore')
        self.dummy = fb_data['dummy'] if 'dummy' in fb_data else False
        self.log.info('[{0}] Loaded config key: {1}, secret: {2}, dummy: {3}'.format(self.name,
                                                                                     self.flickr_consumer_key,
                                                                                     self.flickr_consumer_secret,
                                                                                     self.dummy))

    def is_dummy(self):
        return self.dummy

    def get_root_endpoint(self):
        return None

    def register_destination(self, context):
        """

        @type context: PublisherContext
        """
        token = self.get_token(context.target)

        if not token:
            self.log.error('Flickr access token is invalid for [{0}]'.format(context.target.Key))
            return False
        else:
            self.log.info('Success: Found Flickr access token for [{0}]'.format(context.target.Key))

        return True

    def _get_auth_ahndler(self, token):
        return auth.AuthHandler(key=self.flickr_consumer_key,
                                secret=self.flickr_consumer_secret,
                                access_token_key=token['key'].encode(encoding='utf-8', errors='ignore'),
                                access_token_secret=token['secret'].encode(encoding='utf-8', errors='ignore'))

    def publish_album(self, user, album, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        uploaded = []

        title = album['title'].encode(encoding='utf-8', errors='ignore')
        description = message.encode(encoding='utf-8', errors='ignore')

        self.log.info('Posting [{0}] images to album [{1}]'.format(len(album['images']), title))

        # set up auth
        a = self._get_auth_ahndler(token)
        flickr_api.set_auth_handler(a)

        for image in album['images']:
            # album images contain image title in image['description']
            r = self.upload_photo(image['url'], title=image['description'].encode(encoding='utf-8', errors='ignore'))
            if r:
                uploaded.append(r)

        if not (uploaded or message_id):
            self.log.warning('WARNING: No images were uploaded, returning None')
            return None

        self.log.info('Uploaded {0} images, adding to set...'.format(len(uploaded)))

        # get the photoset
        photo_set = None

        # edit description if edited photoset
        if message_id:
            try:
                photo_set = flickr_api.Photoset(id=message_id)
                photo_set.editMeta(title=title, description=description)
            except Exception as e:
                self.log.warning('[flickr] Warning: Failed to edit a photoset {0}, {1}'.format(message_id, e))
                photo_set = None

        # no message id or failed to get photoset from id
        # locate by name
        if not photo_set:
            try:
                p = flickr_api.Person(id=user.pid)
                photosets = p.getPhotosets()
                photo_set = next((s for s in photosets if s.title.encode(encoding='utf-8', errors='ignore') == title), None)
                if photo_set:
                    photo_set.editMeta(title=title, description=description)
            except Exception as e:
                self.log.warning('[flickr] Warning: Failed to get photoset from list {0}'.format(e))
                photo_set = None

        # create new photoset if edit failed or new photoset
        if not photo_set and uploaded:
            try:
                photo_set = flickr_api.Photoset.create(title=title, description=description, primary_photo=uploaded.pop(0))
            except Exception as e:
                self.log.warning('[flickr] Error: Failed to create a photoset: {0}'.format(e))
                return None

        # assign photos to photoset
        for photo in uploaded:
            try:
                photo_set.addPhoto(photo=photo)
                self.log.info('Added photo {0} to a photoset {1}'.format(photo, photo_set))
            except Exception as e:
                self.log.warning('[flickr] Warning: Failed to add photo [{0}] to a photoset [{1}], {2}'.format(photo, photo_set, e))

        return photo_set

    def publish_photo(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        a = self._get_auth_ahndler(token)
        flickr_api.set_auth_handler(a)

        if len(message) > 20:
            description = message.encode(encoding='utf-8', errors='ignore')
            title = '{0}...'.format(description[:20])
        else:
            description = ''
            title = message.encode(encoding='utf-8', errors='ignore')

        if message_id:
            # edit existing photo
            try:
                result = flickr_api.Photo(id=message_id)
                result.setMeta(title=title, description=description)
                self.log.info('Edited photo, result: {0}'.format(result))
                return result
            except Exception as e:
                self.log.warning('[flickr] Warning: Failed to edit photo {0}, {1}'.format(message_id, e))

        # no message_id or failed to edit -- upload new
        result = self.upload_photo(feed['fullImage'], title=title, description=description)

        self.log.info('Posted photo, result: {0}'.format(result))
        return result

    def upload_photo(self, url, title, description=''):

        u, size = self._download_image(url)
        if not u:
            return None

        path = urlparse.urlparse(url).path
        name = os.path.split(path)[1]
        try:
            self.log.info('Uploading [{0}]...'.format(url))
            result = flickr_api.upload(photo_file=(name, u, size), title=title, description=description)

        except Exception as e:
            self.log.error('Exception in flickr.upload_photo(): {0}'.format(e))
            result = None

        u.close()

        # remove temp file
        return result

    def publish_text(self, user, feed, message, message_id, token):
        # text is not supported
        return 'unsupported'

    def publish_link(self, user, feed, message, message_id, token):
        # links are not supported
        return 'unsupported'

    def process_result(self, message_id, result, user, log_func, context):
        if not result:
            return None

        if result == 'unsupported':
            # skipped as not supported
            return result

        try:
            # str the message id as it is int
            return str(result.id)
        except:
            log_message = 'Warning: Publish to Flickr [{0}], result[{1}]'.format(user.Key, result)
            log_func(context, log_message)

        return None

    def is_delete_message(self, user, feed):
        return False
