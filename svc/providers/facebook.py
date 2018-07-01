import httplib
import json
from logging import Logger
import traceback
import urllib

from datetime import datetime

from providers.publisher_base import PublisherBase
from utils import config
from core import DataDynamo
from core.model import SocialAccount


class FacebookPublisher(PublisherBase):
    API_PREFIX = '/v2.12'

    def __init__(self, log, data, config_path, picasa=None):
        """
        @type data: DataDynamo
        @type log: Logger
        """
        PublisherBase.__init__(self, 'facebook', log, data, config_path, picasa)
        fb_data = config.load_config(config_path, 'facebook_credentials.json')
        self.facebook_api_key = fb_data['facebook_api_key']
        self.facebook_secret = fb_data['facebook_secret']
        self.dummy = fb_data['dummy'] if 'dummy' in fb_data else False
        self.log.info('[{0}] Loaded config key: {1}, secret: {2}, dummy: {3}'.format(self.name,
                                                                                     self.facebook_api_key,
                                                                                     self.facebook_secret,
                                                                                     self.dummy))

    def is_dummy(self):
        return self.dummy

    def get_root_endpoint(self):
        return "graph.facebook.com"

    def get_user_param(self, user, param):
        """

        @type user: SocialAccount
        """
        # albums can not be created for groups
        if param == 'album_links':
            return super(PublisherBase, self).get_user_param(user, param) or super(PublisherBase, self).get_user_param(user, 'is_group')
        return super(PublisherBase, self).get_user_param(user, param)

    def register_destination(self, user):
        """

        @type user: SocialAccount
        """
        key = self.get_token(user)
        req = '/oauth/access_token?'
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.facebook_api_key,
            'client_secret': self.facebook_secret,
            'fb_exchange_token': key}

        result = self.execute_request(req, params, 'GET')
        if 'access_token' not in result:
            self.log.error('Facebook request invalid result [{0}]'.format(result))
            return False

        expires = result['expires'] if 'expires' in result else 'never'
        self.log.info('Received long-lived access token for [{0}], expires [{1}]'.format(user.Key, expires))
        self.data.set_user_token(user, json.dumps(result['access_token']), expires)

        return True

    def refresh_avatar(self, user):
        """

        @type user: SocialAccount
        """
        result = self.execute_request('/{0}/picture', dict(redirect='false', type='square'), method='GET')
        if result:
            pass
        # TODO: finish avatar refresh code

    def publish_link(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        params = {
            'message': message.encode('utf-8', 'ignore'),
            # 'description': 'description',
            # name is prevented by Facebook late 2017 (?)
            # 'name': feed['title'].encode('utf-8', 'ignore'),
            # 'source': feed['link'],
            'link': feed['link'].encode('utf-8', 'ignore'),
            # 'caption': feed['link'].encode('utf-8', 'ignore'),
            'access_token': token
        }

        # picture is prevented by Facebook late 2017 (?)
        # add thumbnail if supplied
        # if 'fullImage' in feed and feed['fullImage']:
        #    params['picture'] = feed['fullImage'].encode('utf-8', 'ignore')

        # execute request
        return self.execute_request('/{0}?'.format(message_id) if message_id else '/{0}/feed?'.format(user.pid), params)

    def publish_text(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        params = {
            'caption': feed['title'].encode('utf-8', 'ignore'),
            'message': message.encode('utf-8', 'ignore'),
            'access_token': token
        }
        # execute request
        return self.execute_request('/{0}?'.format(message_id) if message_id else '/{0}/feed?'.format(user.pid), params)

    def _create_album_from_feed(self, pid, album, message, token):

        if not album:
            self.log.warning('[{0}] No album bag...'.format(self.name))
            return None, None

        # take Facebook's standard for day-to-day photos
        album_name = 'Timeline Photos' if album['buzz'] else album['title']

        if album_name:
            album_result = self._create_album(pid, album_name, message, token)
            if album_result and 'id' in album_result:
                return album_result['id'], album_result

        self.log.warning('[{0}] Failed to create album...'.format(self.name))
        return None, None

    def publish_photo(self, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        # always to timeline photos
        album_id = self.get_user_param(user, 'timeline.album')
        if not album_id:
            album_result = self._create_album(user.pid, 'Timeline Photos', message, token)
            if album_result and 'id' in album_result:
                album_id = album_result['id']
                self.data.set_user_param(user, 'timeline.album', album_id)
                self.log.info('[{0}] Cached Timeline Photos Album for [{1}], ID: [{2}]'.format(self.name, user.Key, album_id))

        # get the location tag if provided
        place_tag = self._get_place_tag(feed['location'], token) if 'location' in feed else None

        # get date
        backdated = feed['pubDate'] if 'pubDate' in feed else None

        return self._publish_photo(album_id or user.pid, feed['fullImage'], message, backdated, place_tag, token)

    def _publish_photo(self, album_id, url, description, backdated, place_tag, token):
        # post the image to the album
        params = {
            'url': url,
            'message': description.encode('utf-8', 'ignore'),
            'access_token': token
        }

        # add place tag if supplied
        if place_tag:
            params['place'] = place_tag

        # add date
        if backdated:
            try:
                params['backdated_time'] = datetime.strptime(backdated, '%a, %d %b %Y %H:%M:%S -0000').strftime('%Y-%m-%dT%H:%M:%S%z')
            except:
                pass

        # execute request
        result = self.execute_request('/{0}/photos?'.format(album_id), params)
        if result and 'error' in result and result['error']:
            self.log.warning('[{0}] Photo publish request failed, returning None'.format(self.name))
            result = None

        return result

    def _get_place_tag(self, location, token):

        if not location:
            return None

        if 'position' not in location:
            return None

        position = location['position']
        if not ('latitude' in position and 'longitude' in position):
            return None

        center = '{0},{1}'.format(position['latitude'], position['longitude'])
        params = {
            'type': 'place',
            'q': location['displayName'].encode('utf-8', 'ignore') if 'displayName' in location else None,
            'center': center,
            'distance': 100,
            'access_token': token
        }
        # execute request
        result = self.execute_request('/search?', params, 'GET')
        if result and 'error' in result and result['error']:
            self.log.warning('[{0}] Location not found'.format(self.name))
            return None

        return result['data'][0]['id'] if 'data' in result and len(result['data']) else None

    def publish_album(self, user, album, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        # get the location tag if provided
        place_tag = self._get_place_tag(feed['location'], token) if 'location' in feed else None

        # get date
        backdated = feed['pubDate'] if 'pubDate' in feed else None

        album_id, album_result = self._create_album_from_feed(user.pid, album, message, token)
        if not album_id:
            return None

        for image in album['images']:
            result = self._publish_photo(album_id or user.pid, image['url'], image['description'], backdated, place_tag, token)
            # fallback to link if publish have failed
            if not (result and 'id' in result):
                self.log.warning('Publish to album failed, retrying with smaller image...')
                # retry with smaller image
                self._publish_photo(album_id or user.pid, image['alt_url'], image['description'], backdated, place_tag, token)

        return album_result

    def _create_album(self, pid, album_name, description, token):
        # check if album exists
        try:
            req = '/{0}/albums?'.format(pid)
            params = {'fields': 'name', 'access_token': token}
            result = self.execute_request(req, params, method='GET')
            if 'data' in result.keys() and len(result['data']):
                for album in result['data']:
                    if album['name'] == album_name:
                        return album
        except:
            pass

        # existing album not found, create an album
        req = '/{0}/albums?'.format(pid)
        params = {
            'name': album_name.encode('utf-8', 'ignore'),
            'description': description.encode('utf-8', 'ignore'),
            'access_token': token
        }

        result = self.execute_request(req, params)
        if not 'id' in result.keys():
            self.log.error('Facebook create album request invalid result [{0}]'.format(result))
            return None

        return result

    def delete_message(self, user, message_id, token):
        """

        @type user: SocialAccount
        """
        self.log.warning('Deleting message [{0}], user [{1}]'.format(message_id, user.Key))
        params = {'access_token': token}
        response = self.execute_request('/{0}?'.format(message_id), params, 'DELETE')
        return bool(response and 'error' not in response)

    def is_delete_message(self, user, feed):
        """

        @type user: SocialAccount
        """
        return feed['type'] in ('photo', 'album') or 'is_page' in user.options

    def execute_request(self, req, params, method='POST'):
        req = ''.join([FacebookPublisher.API_PREFIX, req])
        body = urllib.urlencode(params)
        self.log.info('{0}: {1}, {2}'.format(method, req, body))
        if self.is_dummy():
            self.log.warning('Dry-run mode: not sending to [{0}]!'.format(self.name))
            return {}

        conn = httplib.HTTPSConnection(self.get_root_endpoint())
        conn.connect()
        if 'POST' == method:
            conn.request(method, req, body)
        else:
            conn.request(method, req + body)

        resp = conn.getresponse()
        if resp.status != 200:
            self.log.error('Publisher request failed: {0}:{1}'.format(resp.reason, resp.msg))
            if resp.msg and resp.msg.has_key('content-length'):
                try:
                    return json.loads(resp.read())
                except:
                    pass
            # all have failed fallback to this
            return {'reason': resp.reason, 'error': {'message': resp.msg['www-authenticate'] if resp.msg.haskey('www-authenticate') else str(resp.msg)}}

        result = resp.read()
        self.log.info('...result: {0}'.format(result))
        conn.close()
        return self._parse_response(result)

    def process_result(self, message_id, result, user, log_func):
        try:
            if not result:
                return None
            elif message_id and 'error' not in result:
                return message_id
            elif 'id' in result:
                return result['id']
            elif 'error' in result:
                log_func('Warning: Facebook:{0}, message: "{1}"'.format(user.Key, result['error']['message']))
        except Exception as e:
            self.log.error('Exception in fb.process_result: {0}\r\n{1}'.format(e, traceback.format_exc()))

        return None

    @staticmethod
    def _parse_response(body):
        result = {}
        try:
            r = json.loads(body)
            return {'result': r} if type(r) is bool else r
        except:
            # some weird facebook response for token request
            for tt in body.split('&'):
                keyvalue = tt.split('=')
                if len(keyvalue) < 2:
                    break
                result[keyvalue[0]] = keyvalue[1]

        return result

