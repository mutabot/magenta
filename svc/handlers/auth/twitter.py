import json
import traceback

import tornado
from tornado import gen, web, auth

from core.model import RootAccount, SocialAccount
from handlers.base import BaseHandler


class AuthLoginHandler(BaseHandler, tornado.auth.TwitterMixin):
    def _oauth_get_user(self, access_token, callback):
        pass

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            self.require_setting("twitter_consumer_secret", "Twitter OAuth")
            gl_user = yield self.get_gl_user()  # type: RootAccount
            if not gl_user:
                self.render('misc/auth.html', error='User must be logged in with Google')
                return

            redirect_uri = self.get_redirect_url()

            if self.get_argument('oauth_token', None):
                tw_user = yield self.get_authenticated_user()
                self.logger.debug('AuthLoginHandler, _on_auth: tw_user = [{0}]'.format(tw_user))
                if not tw_user:
                    self.render('misc/auth.html', error='Twitter authentication failed.')
                    return

                # set dirty flag (IKR!)
                gl_user.dirty.add('accounts')

                # purge all temp accounts, we now have fresh user data
                self.data.purge_temp_accounts(gl_user)

                # store provider session data
                self.add_temp_account(gl_user, tw_user)

                # serialise the user data
                yield self.save_google_user(gl_user)

                # redirect to selector
                self.selector_redirect('twitter')
                return

            else:
                yield self.authorize_redirect(callback_uri=redirect_uri)

        except Exception as e:
            self.logger.error('Twitter Auth exception: {0}, \r\n{1}'.format(e, traceback.format_exc()))
            self.render('misc/auth.html', error='System error while authenticating with Twitter.')
            return

    def add_temp_account(self, gl_user, account_data):
        # type: (RootAccount, dict) -> SocialAccount

        child_account = SocialAccount(gl_user.account.pid, 'twitter', str(account_data['id']))
        # existing account ?
        if child_account.Key in gl_user.accounts:
            # will be updating it
            child_account = gl_user.accounts[child_account.Key]
        else:
            gl_user.accounts[child_account.Key] = child_account
            child_account.options['temp'] = True

        child_account.info = account_data

        return child_account


class AuthLogoutHandler(BaseHandler, tornado.auth.TwitterMixin):
    def _oauth_get_user(self, access_token, callback):
        pass

    def get(self):
        self.redirect('/')
