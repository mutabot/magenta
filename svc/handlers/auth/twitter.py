import json
import traceback

import tornado
from tornado import gen, web, auth
from handlers.base import BaseHandler


class AuthLoginHandler(BaseHandler, tornado.auth.TwitterMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            self.require_setting("twitter_consumer_secret", "Twitter OAuth")
            user = yield self.get_gl_user()
            if not user:
                self.render('misc/auth.html', error='User must be logged in with Google')
                return
            
            gid = user['id']

            redirect_uri = self.get_redirect_url()

            if self.get_argument('oauth_token', None):
                tw_user = yield self.get_authenticated_user()
                self.logger.debug('AuthLoginHandler, _on_auth: tw_user = [{0}]'.format(tw_user))
                if not tw_user:
                    self.render('misc/auth.html', error='Twitter authentication failed.')
                    return

                # purge all temp accounts, we now have fresh user data
                self.data.purge_temp_accounts(gid)

                # store provider session data
                self.data.add_temp_account(gid, 'twitter', tw_user['id_str'], json.dumps(tw_user))

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
    def get(self):
        self.redirect('/')
