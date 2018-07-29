import os

from oauth2client import client
from tornado import gen

from core.model import SocialAccount, RootAccount
from handlers.base import BaseHandler
from providers import google_fetch


class BaseGoogleLoginHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super(BaseGoogleLoginHandler, self).__init__(application, request, **kwargs)
        self.redirect_uri = self.get_redirect_url()
        self.logger.info('GoogleAuth, redirect uri: {0}'.format(self.redirect_uri))
        self.flow = None

    def prepare(self):
        scope = [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/plus.login',
            'https://www.googleapis.com/auth/plus.me',
        ]
        if 'page' in self.request.arguments:
            scope.append('https://www.googleapis.com/auth/youtube.readonly')
        elif 'clear' in self.request.arguments:
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
    @gen.coroutine
    def get(self, *args, **kwargs):
        try:

            code = self.get_argument('code', None)
            if not code:
                r = self.flow.step1_get_authorize_url()
                self.logger.error('GoogleAuth, redirecting to: {0}'.format(r))
                self.redirect(r)
                return

            credentials = self.flow.step2_exchange(code)

            # TODO: The below is synchronous!
            user_info = google_fetch.GoogleFetch.get_user_info(credentials)
            gid = user_info['id'].encode()

            # load user data if any
            current_account = yield self.data.load_account_async(gid)

            # redirect to legacy if legacy user
            if self.legacy_data.get_terms_accept(gid):
                self.logger.info('Legacy gid: {0}'.format(gid))
                self.set_cookie('magenta_version', 'v2', expires_days=2)
            else:
                # link accounts if current user
                if current_account and current_account.account.pid != gid:
                    self.data.add_linked_account(current_account.account.pid, gid)

                # prevent account overwrite
                elif not current_account:
                    # safe user info
                    current_account = RootAccount('google', gid)
                    current_account.account = SocialAccount(gid, 'google', gid)
                    current_account.accounts[current_account.account.Key] = current_account.account

                # refresh credentials and info
                current_account.account.credentials = credentials
                current_account.account.info = user_info

                current_account.dirty.add('accounts')

                # not sure if this is required ...
                yield self.data.save_account_async(current_account)

                # save GID in a cookie, this will switch user
                self.set_current_user_session(gid)

        except Exception as e:
            self.logger.error('ERROR: Google Auth, {0}'.format(e))

        # redirect to main login
        self.redirect(self.settings['auth_redirects']['main'])
