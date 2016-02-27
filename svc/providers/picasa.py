import json
import os
import socket
import time
import traceback
from httplib import BadStatusLine
from logging import Logger

import httplib2
from apiclient import errors
from oauth2client.file import Storage
from oauth2client.service_account import ServiceAccountCredentials

from providers.google_fetch import GoogleFetchRetry
from providers.google_rss import GoogleRSS


class Picasa(object):
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
        storage = Storage(os.path.join(config_path, 'picasa.dat'))
        self.credentials = storage.get()

        if self.credentials is None or self.credentials.invalid:
            self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
                os.path.join(config_path, 'picasa_secrets.json'),
                scopes='https://picasaweb.google.com/data/')

        self.credentials.set_store(storage)

    def authorize(self):
        if self.service is None or time.time() - self.auth_time > 300:
            self.logger.info('Authorizing credentials')
            self.http = self.credentials.authorize(http=httplib2.Http())
            # Construct a service object via the discovery service.
            self.service = None
            self.auth_time = time.time()

    @staticmethod
    def get_item_media_type(src_entry):
        """
        @rtype: set()
        """
        try:
            media = src_entry['media$group']['media$content']
            return {m['medium'] for m in media}
        except:
            pass
        return {}

    def deduce_media_url(self, src_entry):
        try:
            max_media = None
            media = src_entry['media$group']['media$content']
            for m in media:
                if not max_media:
                    max_media = m
                elif max_media['width'] < m['width'] and m['type'] == max_media['type']:
                    max_media = m
                elif m['type'] == 'video/mpeg4':
                    max_media = m

            # check if it is redirector
            if 'redirector.googlevideo.com' in max_media['url']:
                self.logger.info('Expanding google redirector link')
                http = httplib2.Http()
                try:
                    http.follow_redirects = False
                    response, content = http.request(max_media['url'])
                    self.logger.debug('Response: {0}'.format(response))
                    if response['status'] == '302':
                        max_media['url'] = response['location']
                        # self.logger.debug('Content: {0}'.format(content))
                except Exception as e:
                    self.logger.info('Response from google redirector link: {0}:{1}'.format(e, traceback.format_exc()))

            url = GoogleRSS.parse_full_image_url(max_media['url']) if max_media['medium'] == 'image' else max_media[
                'url']
        except:
            url = GoogleRSS.parse_full_image_url(src_entry['content']['src'])
        return url

    def format_album(self, album_bag):

        album = {
            'title': album_bag['feed']['title']['$t'] if album_bag else u'',
            'buzz': 'gphoto$albumType' in album_bag['feed'] and album_bag['feed']['gphoto$albumType']['$t'] == 'Buzz',
            'images': [],
            'media_types': set()
        }

        for src_entry in album_bag['feed']['entry']:
            # collect image media types
            media_types = Picasa.get_item_media_type(src_entry)
            album['media_types'] |= media_types
            # create image record
            img = {
                # using 'published' instead of 'updated' as updated timestamp can be greater than G+ post updated timestamp
                'updated': GoogleRSS.get_timestamp(src_entry['published']['$t']),
                'url': GoogleRSS.parse_full_image_url(src_entry['content']['src']),
                'alt_url': src_entry['content']['src'],
                'description': src_entry['summary']['$t'],
                'media_types': media_types
            }
            self.logger.debug('Appending: {0}'.format(img))
            album['images'].append(img)

        return album

    def get_album(self, user_id, album_id):
        try:
            # if self.credentials is None or self.credentials.invalid:
            #    raise tornado.web.HTTPError(403, 'Invalid Credentials')
            # self.authorize()
            # authorisation is not working, trying bare
            http = httplib2.Http()

            # query data from picasa
            query = 'https://picasaweb.google.com/data/feed/api/user/{user_id}/albumid/{album_id}?alt=json'
            query = query.format(user_id=user_id, album_id=album_id)
            self.logger.debug('Requesting...: {0}'.format(query))
            response, content = http.request(query)
            self.logger.debug('Response: {0}'.format(response))
            # self.logger.debug('Content: {0}'.format(content))
            if not (content and len(content)):
                return None

            album_bag = json.loads(content)

            # validate the album
            if not (album_bag and 'feed' in album_bag and 'entry' in album_bag['feed'] and len(album_bag['feed']['entry'])):
                return None
            if not album_bag or not ('feed' in album_bag and 'title' in album_bag['feed']):
                return None

            # format album to internal format
            return self.format_album(album_bag)

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
            self.logger.warning('picasa::get_album for [{0}]: exception: {1}:{2}'.format(user_id, type(e), e))
            return None
