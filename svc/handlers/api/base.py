import json
import traceback

import tornado
from tornado.gen import Return
from tornado.web import HTTPError

from core.model import RootAccount
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

        self.logger.info('GET: [{0}], {1}'.format(gl_user.Key, args))

        try:
            r = yield self.handle_get(gl_user, args)
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

        self.logger.info('POST: [{0}], {1}'.format(gl_user.Key, args))
        try:
            r = yield self.handle_post(gl_user, args, body)
            # normal exit
            if r is None:
                raise HTTPError(status_code=501, log_message='No Result')

            # write gl user back
            if len(gl_user.dirty):
                yield self.save_google_user(gl_user)

            self.write(json.dumps(r))
            self.finish()
            return

        except HTTPError as http_ex:
            raise http_ex

        # abnormal exit
        except Exception as e:
            self.logger.error('Exception: in API POST: {0}, {1}'.format(e, traceback.format_exc()))
            raise HTTPError(status_code=501)

    def check_tnc(self, gl_user):
        terms = self.data.get_terms_accept(gl_user)
        if not (terms and 'tnc' in terms and terms['tnc']):
            raise HTTPError(status_code=401, log_message='Not Authorized')

    @tornado.gen.coroutine
    def handle_get(self, gl_user, args, callback=None):
        """
        Must yield number of seconds to poll or throw Return exception
        @type gl_user: RootAccount
        @param gl_user:
        @param args:
        @param callback:
        @return:
        """

    @tornado.gen.coroutine
    def handle_post(self, gl_user, args, body, callback=None):
        """
        Must yield number of seconds to poll or throw Return exception
        @type gl_user: RootAccount
        @param args:
        @param callback:
        @return:
        """

    def format_google_source(self, info):
        try:
            return {
                'id': info['id'],
                'name': info['name'] if 'name' in info else info['displayName'] if 'displayName' in info else '',
                'url': info['link'] if 'link' in info else info['url'] if 'url' in info else 'https://plus.google.com/{0}'.format(info['id']),
                'picture_url': info['picture'] if 'picture' in info else info['image']['url'] if 'image' in info and 'url' in info['image'] else ''
            }
        except Exception as e:
            self.logger.error('Exception: Failed to format source {0}'.format(info))
