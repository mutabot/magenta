import json
from logging import Logger
import os
import urlparse
import time

from fivehundredpx import FiveHundredPXAPI, auth

from providers.publisher_base import PublisherBase
from utils import config
from core import Data


# noinspection PyBroadException
class Px500Publisher(PublisherBase):
    CATEGORY = {
        'abstract': 10,
        'animals': 11,
        'blackandwhite': 5,
        'bw': 5,
        'monochrome': 5,
        'celebrities': 1,
        'cityandarchitecture': 9,
        'city': 9,
        'architecture': 9,
        'commercial': 15,
        'concert': 16,
        'family': 20,
        'fashion': 14,
        'film': 2,
        'fineart': 24,
        'food': 23,
        'journalism': 3,
        'landscapes': 8,
        'landscape': 8,
        'macro': 12,
        'nature': 18,
        'nude': 4,
        'people': 7,
        'performingarts': 19,
        'sport': 17,
        'sports': 17,
        'stilllife': 6,
        'street': 21,
        'transportation': 26,
        'travel': 13,
        'underwater': 22,
        'urbanexploration': 27,
        'urban': 27,
        'wedding': 25
    }

    def __init__(self, log, data, config_path, picasa=None):
        """
        @type data: Data
        @type log: Logger
        """
        PublisherBase.__init__(self, '500px', log, data, config_path, picasa=picasa)
        # init 500px keys
        cfg = config.load_config(config_path, '500px_credentials.json')
        self.consumer_key = cfg['500px_consumer_key'].encode(encoding='utf-8', errors='ignore')
        self.consumer_secret = cfg['500px_consumer_secret'].encode(encoding='utf-8', errors='ignore')
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
        token_str = self.data.px500.get_user_token(user)
        if not token_str:
            return None
        token = json.loads(token_str)
        return token

    def get_user_param(self, user, param):
        return self.data.px500.get_user_param(user, param)

    def register_destination(self, user):
        token = self.data.px500.get_user_token(user)
        if not token:
            self.log.error('500px access token is invalid for [{0}]'.format(user))
            return False
        else:
            self.log.info('Success: Found 500px access token for [{0}]: {1}'.format(user, token))

        return True

    def _get_auth_ahndler(self, token):
        handler = auth.OAuthHandler(self.consumer_key, self.consumer_secret)
        handler.set_access_token(token['key'].encode(encoding='utf-8', errors='ignore'),
                                 token['secret'].encode(encoding='utf-8', errors='ignore'))
        return handler

    def publish_album(self, user, album, feed, message, message_id, token):
        uploaded = []
        title = album['title'][:50].encode(encoding='utf-8', errors='ignore')
        self.log.info('Posting [{0}] images to album [{1}]'.format(len(album['images']), title))

        # set up auth
        api = FiveHundredPXAPI(auth_handler=self._get_auth_ahndler(token))

        for image in album['images']:
            r = self.upload_photo(api, image['url'], image['description'], tags=image['tags'])
            if r and 'id' in r:
                uploaded.append(str(r['id']))

        if not (uploaded or message_id):
            self.log.warning('WARNING: No images were uploaded, returning None')
            return None

        self.log.info('Uploaded {0} images, adding to set...'.format(len(uploaded)))

        # edit description if edited photoset
        if message_id:
            try:
                result = api.collections_update(id=message_id, title=title, photo_ids=','.join(uploaded))
                return result
            except Exception as e:
                self.log.warning('[500px] Warning: Failed to edit a photoset {0}, {1}'.format(message_id, e))

        # no message id or failed to get photoset from id
        # locate by name
        try:
            photosets = api.collections()
            if photosets and 'collections' in photosets:
                photo_set = next((s for s in photosets['collections'] if s['title'].encode(encoding='utf-8', errors='ignore') == title), None)
                if photo_set:
                    # get photos currently in the set
                    ids = [str(p['id']) for p in photo_set['photos']]
                    # extend the set with uploaded
                    ids.extend(uploaded)
                    # update the collection
                    result = api.collections_update(id=photo_set['id'], title=title, photo_ids=','.join(ids))
                    return result
        except Exception as e:
            self.log.warning('[500px] Warning: Failed to get photoset from list {0}'.format(e))

        # create new photoset if edit failed or new photoset
        try:
            path = str(int(time.time()))
            result = api.collections_post(title=title, path=path, kind=2, photo_ids=','.join(uploaded))
            return result
        except Exception as e:
            self.log.warning('[500px] Error: Failed to create a photoset: {0}'.format(e))
            return None

    def publish_photo(self, user, feed, message, message_id, token):
        # set up auth
        api = FiveHundredPXAPI(auth_handler=self._get_auth_ahndler(token))

        if message_id:
            # edit existing photo
            try:
                result = api.photos_update(id=message_id,
                                           description=message.encode(encoding='utf-8', errors='ignore'),
                                           tags=self._get_tags(feed['tags']),
                                           category=self._get_category(feed['tags']))

                self.log.info('Edited photo, result: {0}'.format(result))
                return result['id']
            except Exception as e:
                self.log.warning('[500px] Warning: Failed to edit photo {0}, {1}'.format(message_id, e))

        # no message_id or failed to edit -- upload new
        result = self.upload_photo(api, feed['fullImage'], message, tags=feed['tags'])

        self.log.info('Posted photo, result: {0}'.format(result))
        return result

    def upload_photo(self, api, url, message, tags=list()):
        u, size = self._download_image(url)
        if not u:
            return 'Failed to download image. File too big or unsupported format.'

        path = urlparse.urlparse(url).path
        name = os.path.split(path)[1]
        try:
            result = api.photos_post(name=name,
                                     description=message.encode(encoding='utf-8', errors='ignore'),
                                     tags=self._get_tags(tags),
                                     category=self._get_category(tags),
                                     privacy=0)

            if not (result and ('upload_key' and 'photo' in result)):
                self.log.warning('[{0}] Failed to get upload key for photo {1}'.format(self.name, result))
                raise Exception(message='Failed to get upload key for photo')
            else:
                self.log.debug('Uploading [{0}], [{1}] bytes...'.format(url, size))
                r2 = api.upload_photo(fp=u, file_type='image/jpeg',
                                      photo_id=result['photo']['id'],
                                      upload_key=result['upload_key'],
                                      consumer_key=self.consumer_key,
                                      access_key=api.auth_handler.access_token.key)
                self.log.debug('Uploaded: {0}'.format(r2))

        except Exception as e:
            self.log.error('Exception in 500px.upload_photo(): {0}'.format(e))
            result = None

        u.close()

        # remove temp file
        return result['photo']

    def publish_text(self, user, feed, message, message_id, token):
        # text is published to blog
        # set up auth
        api = FiveHundredPXAPI(auth_handler=self._get_auth_ahndler(token))

        if message_id:
            result = api.blogs_update(id=message_id,
                                      title=feed['title'].encode(encoding='utf-8', errors='ignore'),
                                      body=message.encode(encoding='utf-8', errors='ignore'))
        else:
            result = api.blogs_post(title=feed['title'].encode(encoding='utf-8', errors='ignore'),
                                    body=message.encode(encoding='utf-8', errors='ignore'))

        return result

    def publish_link(self, user, feed, message, message_id, token):
        return 'unsupported'

    def process_result(self, gid, message_id, result, user):
        if not result:
            return None

        if result == 'unsupported':
            # skipped as not supported
            return result

        if not (result and 'id' in result):
            log_message = 'Warning: Publish to 500px [{0}] for Google Plus user [{1}], result[{2}]'.format(user, gid, result)
            self.data.add_log(gid, log_message)
            self.log.info(log_message)
            return None

        # str the message id as it is int
        return str(result['id'])

    def is_delete_message(self, user, feed):
        return False

    def _get_category(self, tags):
        for tag in tags:
            try:
                t = tag.lower()
                # cater for tags that have 'photo' or 'photography' appended
                c = self.CATEGORY.get(t[:t.find('photo')])
                if c:
                    return c
            except:
                pass

        return 0

    @staticmethod
    def _get_tags(tags):
        return ','.join([tag.encode('utf-8', 'ignore') for tag in tags])
