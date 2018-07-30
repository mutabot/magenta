import re

import tornado
from tornado import gen, web

from core.model import RootAccount, SocialAccount
from extensions.linkedin_auth import LinkedInMixin
from handlers.base import BaseHandler


class AuthLoginHandler(BaseHandler, LinkedInMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            self.require_setting("linkedin_consumer_secret", "LinkedIn OAuth2")
            gl_user = yield self.get_gl_user()  # type: RootAccount
            if not gl_user:
                self.render('misc/auth.html', error='User must be logged in with Google')
                return

            redirect_uri = self.get_redirect_url()

            code = self.get_argument('code', None)
            if code:
                _user = yield self.get_authenticated_user(redirect_uri,
                                                          self.settings['linkedin_consumer_key'],
                                                          self.settings['linkedin_consumer_secret'],
                                                          code)

                self.logger.debug('AuthLoginHandler, _on_auth: tr_user = [{0}]'.format(_user))
                if not _user:
                    self.render('misc/auth.html', error='LinkedIn authentication failed.')
                    return

                # set dirty flag (IKR!)
                gl_user.dirty.add('accounts')

                # purge all temp accounts, we now have fresh user data
                self.data.purge_temp_accounts(gl_user)

                _user['master'] = True
                # self.data.add_temp_account(gid, 'linkedin', _user['id'], json.dumps(_user))
                # store provider session data
                self.add_temp_account(gl_user, _user)

                # get companies for this user
                args = {
                    'is-company-admin': 'true',
                    'start': 0,
                    'count': 32,
                }

                _pages = yield self.linkedin_request(path='/companies', access_token=_user['access_token'], **args)

                if _pages and 'values' in _pages:
                    for company in _pages['values']:
                        # query company logo
                        _avatar = yield self.linkedin_request(path='/companies/{0}:(square-logo-url)'.format(company['id']), access_token=_user['access_token'], secure='true')

                        company['publicProfileUrl'] = 'http://www.linkedin.com/company/{0}'.format(company['id'])
                        # company id is prepended by CMP$
                        company['id'] = 'CMP${0}'.format(company['id'])
                        company['formattedName'] = company['name']
                        company['pictureUrl'] = re.sub(ur'http://m\.c\.lnkd\.', u'https://media.', _avatar['squareLogoUrl']) if 'squareLogoUrl' in _avatar else u''
                        company['access_token'] = _user['access_token']
                        company['master'] = False
                        company['admin'] = _user['id']

                        # save account info in .t store
                        # self.data.add_temp_account(gid, 'linkedin', company['id'], json.dumps(company))
                        self.add_temp_account(gl_user, company)

                # serialise the user data
                yield self.save_google_user(gl_user)

                # redirect to selector
                self.selector_redirect('linkedin')
                return

            else:
                yield self.authorize_redirect(redirect_uri=redirect_uri,
                                              client_id=self.settings['linkedin_consumer_key'],
                                              client_secret=self.settings['linkedin_consumer_secret'],
                                              extra_params={'state': 'DCEEFWF45453sdffef424'})

        # always close the popup on errors
        except Exception as e:
            self.render('misc/auth.html', error='System error while authenticating with LinkedIn. {0}'.format(e))
            return

    def add_temp_account(self, gl_user, account_data):
        # type: (RootAccount, dict) -> SocialAccount

        child_account = SocialAccount(gl_user.account.pid, 'linkedin', str(account_data['id']))
        # existing account ?
        if child_account.Key in gl_user.accounts:
            # will be updating it
            child_account = gl_user.accounts[child_account.Key]
        else:
            gl_user.accounts[child_account.Key] = child_account
            child_account.options['temp'] = True

        child_account.info = account_data

        return child_account


class AuthLogoutHandler(BaseHandler, LinkedInMixin):
    def get(self):
        self.redirect('/')
