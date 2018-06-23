import tornado
from tornado.gen import Return
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from core.schema import S1
from handlers.api.base import BaseApiHandler
from core.model import RootAccount


class UserApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(UserApiHandler, self).__init__(application, request, **kwargs)
        self.limits = self.settings['limits']

    @tornado.gen.coroutine
    def handle_get(self, gl_user, args, callback=None):
        """

        @type gl_user: RootAccount
        """
        if 'info' in args:
            result = self.get_options(gl_user)
        elif 'log' in args:
            log_data = yield self.data.get_log(gl_user)
            # format log to redis version
            result = {
                gid: log_item.messages for gid, log_item in log_data.iteritems()
            }

        else:
            # by default return account info
            # tnc accept status
            tnc = self.data.get_terms_accept(gl_user)
            src = self.format_google_source(gl_user.account.info)
            user_limits = self.data.get_limits(gl_user)
            limits = self.limits[user_limits] if user_limits and user_limits in self.limits else self.limits['free']

            result = {
                'gid': gl_user.account.pid,     # TODO: Change to the Key model instead of google pid
                'tnc': tnc,
                'name': src['name'],
                'url': src['url'],
                'avatar_url': src['picture_url'],
                'limits': limits
            }

        # sync method, so set the result immediately
        raise Return(result)

    def get_options(self, gl_user):
        """
        User options and log info
        @param gl_user: RootAccount
        @return: { admin: true/false, info: {} }
        """
        return {
            'admin': self.data.get_gid_admin(gl_user),
            'info': self.data.get_terms_accept(gl_user),
        }

    @tornado.gen.coroutine
    def handle_post(self, gl_user, args, body, callback=None):
        """

        @type gl_user: RootAccount
        """
        if 'agree' in args:
            result = self.agree(gl_user, body)
        elif 'remove' in args:
            result = yield self.drop(gl_user, body)
        elif 'info' in args:
            result = self.update(gl_user, body)
        else:
            result = None

        # sync method
        raise Return(result)

    def agree(self, gl_user, body):
        """
        Agree on T&Cs and/or set email options
        @type gl_user: RootAccount
        @param gl_user: root account
        @param body: { email: True/False }
        @return: False on errors
        """
        info = {
            'tnc': True,
            'email': body['email']
        }
        self.data.set_terms_accept(gl_user, info)
        self.data.save_account_async(gl_user, ['accounts'])

        # send registration email
        self.data.pubsub.broadcast_command(S1.MAILER_CHANNEL_NAME, 'mail.send', gl_user.Key, 'account_created')

        return True

    @tornado.gen.coroutine
    def drop(self, gl_user, body):
        """
        "Drop" the gid. Remove all data for this account
        *** Calls Payments Service ***
        @type gl_user: RootAccount
        @param body: ignored
        @return: True
        """
        try:
            try:
                # delete any user subscriptions
                self.logger.info("Deleting user subscriptions")
                payments_node = self.settings['payments_node']
                http_client = AsyncHTTPClient()
                request = HTTPRequest(url=''.join([payments_node, 'cancel']), method='POST', body='{}', headers=self.request.headers)
                self.logger.info("Requesting: {0}, gid: {1}...".format(request.url, gl_user.Key))
                r = yield http_client.fetch(request)
                self.logger.info('Subscription cancel result: {0},{1},{2}'.format(r.code, r.reason, r.error))
                if r.code != 200:
                    raise Return({'error': 'Could not cancel billing plan. Please contact support to resolve this issue.'})
            except Exception as sub_e:
                self.logger.error("ERROR: Exception when Deleting user subscriptions, {0}".format(sub_e))
                raise Return(False)

            # delete user settings
            self.logger.info("Deleting user settings...")
            self.data.unregister_gid(gl_user)
            self.logger.info("User [{0}] deleted...".format(gl_user.Key))
            raise Return(True)
        except Return as r:
            raise r
        except Exception as e:
            self.logger.error("ERROR: Exception in api.user.drop(), {0}".format(e))

        raise Return(False)

    def update(self, gl_user, body):
        """
        Update user information
        @type gl_user: RootAccount
        @param gl_user:
        @param body: { email: True/False }
        @return: False on errors
        """
        info = {
            'tnc': True,
            'email': body['email']
        }
        self.data.set_terms_accept(gl_user, info)

        return True
