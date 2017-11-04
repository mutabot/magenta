import json
import tornado
from tornado import gen, web, auth
from handlers.base import BaseHandler


class AuthLoginHandler(BaseHandler, tornado.auth.FacebookGraphMixin):

    def __init__(self, application, request, **kwargs):
        self.mode = None
        super(AuthLoginHandler, self).__init__(application, request, **kwargs)

    def initialize(self, **kwargs):
        self.mode = kwargs['m'] if kwargs and 'm' in kwargs else None
        self.logger.info('FB mode [{0}]...'.format(self.mode))

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            user = yield self.get_gl_user()
            if not user:
                self.error_redirect(code=10001, message='User must be logged in with Google')
                return
            gid = user['id']

            redirect_uri = self.get_redirect_url()

            if self.get_argument("code", False):
                fb_user = yield self.get_authenticated_user(
                    redirect_uri=redirect_uri,
                    client_id=self.settings["facebook_api_key"],
                    client_secret=self.settings["facebook_secret"],
                    code=self.get_argument("code"))

                self.logger.debug('AuthLoginHandler, _on_auth: fb_user = [{0}]'.format(fb_user))
                if not fb_user:
                    self.data.del_provider_session(gid, 'facebook')
                    self.error_redirect(code=10101, message='Facebook authentication failed')
                    return

                if not 'access_token' in fb_user:
                    self.logger.error('No access code in fb_user for [{0}]'.format(fb_user['id']))
                    self.error_redirect(code=10101, message='Facebook authentication failed, no access token')
                    return

                # purge all temp accounts, we now have fresh user data
                self.data.purge_temp_accounts(gid)

                # save account info in .t store
                fb_user['master'] = True
                self.data.add_temp_account(gid, 'facebook', fb_user['id'], json.dumps(fb_user))

                # save user id kind: page, group, or default-personal
                self.data.facebook.set_user_param(fb_user['id'], 'is_page', '')

                # see if user does have extra accounts (pages)
                self.logger.info('Getting user accounts for [{0}]...'.format(fb_user['id']))

                # get associated accounts
                if self.mode and 'p' in self.mode:
                    accounts = yield self.facebook_request('/{0}/accounts'.format(fb_user['id']),
                                                           access_token=fb_user['access_token'])
                    self.logger.debug('Got user accounts [{0}]'.format(accounts))
                    # if does bundle them to provider data
                    if accounts and 'data' in accounts and len(accounts['data']):
                        self.logger.debug('Got accounts data [{0}]'.format(accounts['data']))
                        for account in accounts['data']:
                            avatar = yield self.facebook_request('/{0}/picture'.format(account['id']), access_token=fb_user['access_token'], redirect='false')
                            if avatar:
                                account['picture'] = avatar
                            account['master'] = False

                            # save user id kind: page or not
                            self.data.facebook.set_user_param(account['id'], 'is_page', 'True')

                            # save account info in .t store
                            self.data.add_temp_account(gid, 'facebook', account['id'], json.dumps(account))

                if self.mode and 'g' in self.mode:
                    # get associated groups
                    try:
                        # manually added groups
                        groups = [{'id': g} for g in self.data.get_provider_session(gid, 'fbg', 'facebook') or []]
                        self.logger.debug('Got manual groups [{0}]'.format(groups))
                        for group in groups:
                            try:
                                self.logger.info('Getting group id {0} info...'.format(group['id']))
                                raw = yield self.facebook_request('/{0}'.format(group['id']), access_token=fb_user['access_token'], fields='icon,name')
                                if not (raw and 'name' in raw):
                                    self.logger.error('Group id {0} not valid'.format(group['id']))
                                    group.clear()
                                    continue

                                # update group data
                                group.update(raw)
                            except Exception as e:
                                self.logger.error('Error getting group id {0} information: {1}'.format(group['id'], e))
                                group.clear()
                                continue

                        # purge manual groups data
                        self.data.del_provider_session(gid, 'facebook')

                        # query FB for user groups (and it may let us!)
                        try:
                            g_query = yield self.facebook_request('/{0}/groups'.format(fb_user['id']), access_token=fb_user['access_token'], fields='icon,name')
                            if g_query and 'data' in g_query and len(g_query['data']):
                                self.logger.debug('Got FB groups data [{0}]'.format(g_query['data']))
                                groups.extend(g_query['data'])

                        except Exception as e:
                            self.logger.error('Error getting groups from FB: {0}'.format(e))

                        # purge invalid groups
                        groups[:] = [g for g in groups if g]
                        for group in groups:
                            if 'icon' in group:
                                group['avatar_url'] = group['icon']
                            group['master'] = False
                            group['access_token'] = fb_user['access_token']

                            # save user id kind: page or not
                            self.data.facebook.set_user_param(group['id'], 'is_group', 'True')

                            # save account info in .t store
                            self.data.add_temp_account(gid, 'facebook', group['id'], json.dumps(group))

                    except Exception as e:
                        self.logger.error('Error getting manual groups: {0}'.format(e))

            elif self.get_argument('error_code', False):
                code = self.get_argument('error_code', False)
                msg = self.get_argument('error_message', False)
                self.error_redirect(code=-11, message='Facebook error [{0}]: {1}'.format(code, msg))
                return
            else:
                # Facebook Groups hack
                if self.get_argument('t', False):
                    try:
                        t_arg = self.get_argument('t', False)
                        # validate and store as session data
                        if len(t_arg) < 1024:
                            self.data.set_provider_session(gid, 'fbg', 'facebook', t_arg.split(','))
                    except:
                        pass
                # normal auth flow redirect
                self.authorize_redirect(redirect_uri=redirect_uri,
                                        client_id=self.settings["facebook_api_key"],
                                        extra_params={"scope": self.settings["facebook_scope"]})
                return
        except Exception as e:
            self.logger.error('General error: {0}'.format(e.message))
            self.error_redirect(code=-13, message='General error: {0}'.format(e.message))
            return

        # redirect to generic account selector renderer
        self.selector_redirect('facebook')


class AuthLogoutHandler(BaseHandler, tornado.auth.FacebookGraphMixin):
    def get(self):
        self.redirect('/')