import json
import traceback

import tornado
from tornado import gen, web, auth

from core.model import RootAccount
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
                self.data.add_temp_account(gl_user, tw_user)

                # redirect to selector
                self.selector_redirect('twitter')
                return

            else:
                yield self.authorize_redirect(callback_uri=redirect_uri)

        except Exception as e:
            self.logger.error('Twitter Auth exception: {0}, \r\n{1}'.format(e, traceback.format_exc()))
            self.render('misc/auth.html', error='System error while authenticating with Twitter.')
            return


class AuthLogoutHandler(BaseHandler, tornado.auth.TwitterMixin):
    def _oauth_get_user(self, access_token, callback):
        pass

    def get(self):
        self.redirect('/')
