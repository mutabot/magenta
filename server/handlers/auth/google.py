import os

from oauth2client import client
import tornado
from tornado import web

from handlers.base import BaseHandler
from providers import google_fetch


class BaseGoogleLoginHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super(BaseGoogleLoginHandler, self).__init__(application, request, **kwargs)
        self.redirect_uri = self.get_redirect_url()
        self.logger.info('GoogleAuth, redirect uri: {0}'.format(self.redirect_uri))

        scope = [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/plus.login',
            'https://www.googleapis.com/auth/plus.me',
        ]
        if 'page' in request.arguments:
            scope.append('https://www.googleapis.com/auth/youtube.readonly')
        elif 'clear' in request.arguments:
            # clear user session if this request is not account link request
            self.clear_current_user_session()

        self.flow = client.flow_from_clientsecrets(
            filename=os.path.join(self.settings['config_path'], 'client_secrets.json'),
            scope=scope,
            redirect_uri=self.redirect_uri)


class GoogleLogoutHandler(BaseGoogleLoginHandler):
    def get(self, *args, **kwargs):
        self.clear_current_user_session()
        self.redirect('/')


class GoogleLoginHandler(BaseGoogleLoginHandler):
    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        try:
            code = self.get_argument('code', None)
            if not code:
                r = self.flow.step1_get_authorize_url()
                self.logger.error('GoogleAuth, redirecting to: {0}'.format(r))
                self.redirect(r)
                return

            # http = httplib2.Http(proxy_info=httplib2.ProxyInfo(socks.PROXY_TYPE_HTTP, 'localhost', 8888, True))
            credentials = self.flow.step2_exchange(code)
            user_info = google_fetch.GoogleFetch.get_user_info(credentials)
            gid = user_info['id'].encode()

            # get logged in google user
            current_gid, gl_user = self.get_google_user()

            # safe user info
            self.data.set_gid_credentials(gid, credentials.to_json())
            self.data.set_gid_info(gid, user_info)

            # link accounts if current user
            if gl_user and 'id' in gl_user and gl_user['id'] and gl_user['id'] != gid:
                self.data.add_linked_account(gl_user['id'], gid)
                self.redirect(self.settings['auth_redirects']['main'])
                return

            else:
                # save GID in a cookie, this will switch user
                self.set_current_user_session(gid)

                # close the window on any errors
        except Exception as e:
            self.logger.error('ERROR: Google Auth, {0}'.format(e))
            self.render('misc/auth.html', error='System error while authenticating with Google. {0}'.format(e))
            return

        # redirect to main login
        self.redirect(self.settings['auth_redirects']['main'])
