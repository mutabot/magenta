import json
import tornado
from tornado import gen, web
from extensions import TumblrMixin
from handlers.base import BaseHandler


class AuthLoginHandler(BaseHandler, TumblrMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            self.require_setting("tumblr_consumer_secret", "Tumblr OAuth")
            user = yield self.get_gl_user()
            if not user:
                self.render('misc/auth.html', error='User must be logged in with Google')
                return

            gid = user['id']

            redirect_uri = self.get_redirect_url()

            if self.get_argument('oauth_token', None):
                tr_user = yield self.get_authenticated_user()
                self.logger.debug('AuthLoginHandler, _on_auth: tr_user = [{0}]'.format(tr_user))
                if not tr_user:
                    self.render('misc/auth.html', error='Tumblr authentication failed.')
                    return

                # purge all temp accounts, we now have fresh user data
                self.data.purge_temp_accounts(gid)

                for blog in tr_user['blogs']:
                    blog['avatar'] = 'https://api.tumblr.com/v2/blog/{0}.tumblr.com/avatar'.format(blog['name'])
                    blog['access_token'] = tr_user['access_token']
                    blog['master'] = blog['name'] == tr_user['name']

                    # save account info in .t store
                    self.data.add_temp_account(gid, 'tumblr', blog['name'], json.dumps(blog))

                # redirect to selector
                self.selector_redirect('tumblr')
                return

            else:
                yield self.authorize_redirect(callback_uri=redirect_uri)

        # always close the popup on errors
        except Exception as e:
            self.logger.error('ERROR: Failed to authenticate with Tumblr, {0}'.format(e))
            self.render('misc/auth.html', error='System error while authenticating with Tumblr.')
            return


class AuthLogoutHandler(BaseHandler, TumblrMixin):
    def get(self):
        self.redirect('/')
