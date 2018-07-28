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

            else:

                credentials = self.flow.step2_exchange(code)

                # TODO: The below is synchronous!
                user_info = google_fetch.GoogleFetch.get_user_info(credentials)
                gid = user_info['id'].encode()

                # get logged in google user
                current_account = yield self.get_google_user()

                self.logger.info('setting cookie and redirect to {0}'.format(self.settings['auth_redirects']['main']))

                self.set_cookie('magenta_version', 'v2')
                # redirect to main login
                self.redirect(self.settings['auth_redirects']['main'])
                return

                # link accounts if current user
                if current_account and current_account.account.pid != gid:
                    self.data.add_linked_account(current_account.account.pid, gid)
                    self.redirect(self.settings['auth_redirects']['main'])
                else:
                    # safe user info
                    root_acc = RootAccount('google', gid)
                    root_acc.account = SocialAccount(gid, 'google', gid)
                    root_acc.account.credentials = credentials
                    root_acc.account.info = user_info

                    root_acc.accounts[root_acc.account.Key] = root_acc.account
                    root_acc.dirty.add('accounts')
                    yield self.data.save_account_async(root_acc)

                    # save GID in a cookie, this will switch user
                    self.set_current_user_session(gid)

                # close the window on any errors
        except Exception as e:
            self.logger.error('ERROR: Google Auth, {0}'.format(e))

        # redirect to main login
        self.redirect(self.settings['auth_redirects']['main'])
