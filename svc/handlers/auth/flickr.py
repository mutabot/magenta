import json
import traceback
import tornado
from tornado import gen, web
from extensions import FlickrMixin
from handlers.base import BaseHandler


class AuthLoginHandler(BaseHandler, FlickrMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            self.require_setting("flickr_consumer_secret", "Flickr OAuth")
            user = yield self.get_gl_user()
            if not user:
                self.render('misc/auth.html', error='User must be logged in with Google')
                return
            gid = user['id']

            redirect_uri = self.get_redirect_url()

            if self.get_argument('oauth_token', None):
                auth_user = yield self.get_authenticated_user()
                self.logger.debug('AuthLoginHandler, _on_auth: auth_user = [{0}]'.format(auth_user))
                if not (auth_user and 'user' in auth_user):
                    self.render('misc/auth.html', error='Flickr authentication failed.')
                    return

                # purge all temp accounts, we now have fresh user data
                self.data.purge_temp_accounts(gid)

                # store provider session data
                self.data.add_temp_account(gid,
                                           'flickr',
                                           auth_user['user']['id'].encode(encoding='utf-8', errors='ignore'),
                                           json.dumps(auth_user))

                self.selector_redirect('flickr')
                return

            else:
                yield self.authorize_redirect(callback_uri=redirect_uri)

        # always close the popup on errors
        except:
            self.logger.error('Exception: in flickr.AuthLoginHandler(): {0}'.format(traceback.format_exc()))
            self.render('misc/auth.html', error='System error while authenticating with Flickr.')
            return


class AuthLogoutHandler(BaseHandler, FlickrMixin):
    def get(self):
        self.redirect('/')
