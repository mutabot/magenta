import time

import tornado
from tornado.web import RequestHandler

from utils import config


class RenderException(Exception):
    def __init__(self, code, message, update_user=True, template=None, template_args=None):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
        self.update_user = update_user
        self.template = template
        self.template_args = template_args


class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        self.providers = dict()
        self.logger = application.logger
        self.data = application.data

        super(BaseHandler, self).__init__(application, request, **kwargs)

    def get_google_user(self):
        # user id
        gid = self.get_secure_cookie(config.USER_ID_COOKIE_NAME)
        # session id
        session_id = self.get_secure_cookie(config.USER_SESSION_COOKIE_NAME)
        # both cookies must be set or can not continue
        if not gid or not session_id:
            return None, None

        # google user info
        gl_user = self.data.get_gid_info(gid)

        return gid, gl_user

    def get_gl_user(self):
        # get logged in google user
        gid, gl_user = self.get_google_user()

        if not (gl_user and 'id' in gl_user and gl_user['id'] and gl_user['id'] == gid):
            # clear cookies and let user to re-sign in
            self.clear_current_user_session()
            return None

        return gl_user

    def set_current_user_session(self, gid):
        self.set_secure_cookie(config.USER_ID_COOKIE_NAME, gid, expires_days=1)
        self.set_secure_cookie(config.USER_SESSION_COOKIE_NAME, str(int(time.time())))

    def clear_current_user_session(self):
        gid = self.get_secure_cookie(config.USER_ID_COOKIE_NAME)
        self.data.del_all_provider_sessions(gid)
        self.clear_cookie(config.USER_ID_COOKIE_NAME)
        self.clear_cookie(config.USER_SESSION_COOKIE_NAME)

    def error_redirect(self, code=0, message=''):
        pass

    def data_received(self, chunk):
        pass

    def selector_redirect(self, provider):
        selector_url = self.settings['auth_redirects']['selector']
        self.redirect(selector_url + '?p=' + provider)

    def get_redirect_url(self):
        # ALWAYS HTTPS
        redirect_url = 'https://{1}{2}{3}'.format(self.request.protocol, self.request.host, self.settings['api_path'], self.request.path)
        self.logger.info('AuthLoginHandler: redirect_uri = [{0}]'.format(redirect_url))
        return redirect_url