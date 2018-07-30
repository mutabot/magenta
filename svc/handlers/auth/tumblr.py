import tornado
from tornado import gen, web

from core.model import RootAccount, SocialAccount
from extensions import TumblrMixin
from handlers.base import BaseHandler


class AuthLoginHandler(BaseHandler, TumblrMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            self.require_setting("tumblr_consumer_secret", "Tumblr OAuth")

            gl_user = yield self.get_gl_user()  # type: RootAccount

            if not gl_user:
                self.render('misc/auth.html', error='User must be logged in with Google')
                return

            redirect_uri = self.get_redirect_url()

            if self.get_argument('oauth_token', None):
                tr_user = yield self.get_authenticated_user()
                self.logger.debug('AuthLoginHandler, _on_auth: tr_user = [{0}]'.format(tr_user))
                if not tr_user:
                    self.render('misc/auth.html', error='Tumblr authentication failed.')
                    return

                # purge all temp accounts, we now have fresh user data
                # set dirty flag (IKR!)
                gl_user.dirty.add('accounts')

                # purge all temp accounts, we now have fresh user data
                self.data.purge_temp_accounts(gl_user)

                for blog in tr_user['blogs']:
                    blog['avatar'] = 'https://api.tumblr.com/v2/blog/{0}.tumblr.com/avatar'.format(blog['name'])
                    blog['access_token'] = tr_user['access_token']
                    blog['master'] = blog['name'] == tr_user['name']

                    # save account info
                    self.add_temp_account(gl_user, blog)

                # serialise the user data
                yield self.save_google_user(gl_user)

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

    def add_temp_account(self, gl_user, account_data):
        # type: (RootAccount, dict) -> SocialAccount

        child_account = SocialAccount(gl_user.account.pid, 'tumblr', account_data['name'])
        # existing account ?
        if child_account.Key in gl_user.accounts:
            # will be updating it
            child_account = gl_user.accounts[child_account.Key]
        else:
            gl_user.accounts[child_account.Key] = child_account
            child_account.options['temp'] = True

        child_account.info = account_data

        return child_account


class AuthLogoutHandler(BaseHandler, TumblrMixin):
    def get(self):
        self.redirect('/')
