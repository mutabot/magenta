import json
import traceback

import tornado
from tornado.gen import Return
from tornado.web import HTTPError

from handlers.base import BaseHandler


class BaseApiHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super(BaseApiHandler, self).__init__(application, request, **kwargs)

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        gl_user = yield self.get_gl_user()
        if not gl_user:
            raise HTTPError(status_code=401, log_message='Not Authorized')

        gid = gl_user['id']

        self.logger.info('GET: [{0}], {1}'.format(gid, args))

        try:
            r = yield self.handle_get(gid, gl_user, args)
            # normal exit
            if r is None:
                raise HTTPError(status_code=501, log_message='No Result')

            self.write(json.dumps(r))
            self.finish()
            return

        except HTTPError as http_ex:
            raise http_ex
        # abnormal exit
        except Exception as e:
            self.logger.error('Exception: in API GET: {0}, {1}'.format(e, traceback.format_exc()))
            raise HTTPError(status_code=501)

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        gl_user = yield self.get_gl_user()
        if not gl_user:
            raise HTTPError(status_code=401, log_message='Not Authorized')

        body_raw = self.request.body
        if not body_raw:
            raise HTTPError(status_code=400, log_message='Bad Request')

        body = json.loads(body_raw)

        gid = gl_user['id']

        self.logger.info('POST: [{0}], {1}'.format(gid, args))
        try:
            r = yield self.handle_post(gid, gl_user, args, body)
            # normal exit
            if r is None:
                raise HTTPError(status_code=501, log_message='No Result')

            self.write(json.dumps(r))
            self.finish()
            return

        except HTTPError as http_ex:
            raise http_ex

        # abnormal exit
        except Exception as e:
            self.logger.error('Exception: in API POST: {0}, {1}'.format(e, traceback.format_exc()))
            raise HTTPError(status_code=501)

    def check_tnc(self, gid):
        info = self.data.get_terms_accept(gid)
        if not (info and 'tnc' in info and info['tnc']):
            raise HTTPError(status_code=401, log_message='Not Authorized')

    @tornado.gen.coroutine
    def handle_get(self, gid, gl_user, args, callback=None):
        """
        Must yield number of seconds to poll or throw Return exception
        @param gid:
        @param gl_user:
        @param args:
        @param callback:
        @return:
        """

    @tornado.gen.coroutine
    def handle_post(self, gid, gl_user, args, body, callback=None):
        """
        Must yield number of seconds to poll or throw Return exception
        @param gid:
        @param gl_user:
        @param args:
        @param callback:
        @return:
        """

    def format_google_source(self, gl_user):
        try:
            return {
                'id': gl_user['id'],
                'name': gl_user['name'] if 'name' in gl_user else gl_user['displayName'] if 'displayName' in gl_user else '',
                'url': gl_user['link'] if 'link' in gl_user else gl_user['url'] if 'url' in gl_user else 'https://plus.google.com/{0}'.format(gl_user['id']),
                'picture_url': gl_user['picture'] if 'picture' in gl_user else gl_user['image']['url'] if 'image' in gl_user and 'url' in gl_user['image'] else ''
            }
        except Exception as e:
            self.logger.error('Exception: Failed to format source {0}'.format(gl_user))
