import tornado
from tornado.gen import Return
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from core.schema import S1
from handlers.api.base import BaseApiHandler


class UserApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(UserApiHandler, self).__init__(application, request, **kwargs)
        self.limits = self.settings['limits']

    @tornado.gen.coroutine
    def handle_get(self, gid, gl_user, args, callback=None):

        if 'info' in args:
            result = self.get_options(gid)
        elif 'log' in args:
            result = self.get_log(gid)
        else:
            # by default return account info
            # tnc accept status
            tnc = self.data.get_terms_accept(gid)
            src = self.format_google_source(gl_user)
            l = self.data.get_limits(gid)
            limits = self.limits[l] if l and l in self.limits else self.limits['free']

            result = {
                'gid': gid,
                'tnc': tnc,
                'name': src['name'],
                'url': src['url'],
                'avatar_url': src['picture_url'],
                'limits': limits
            }

        # sync method, so set the result immediately
        raise Return(result)

    def get_options(self, gid):
        """
        User options and log info
        @param gid: master gid
        @return: { admin: true/false, info: {} }
        """
        return {
            'admin': bool(self.data.get_gid_admin(gid)),
            'info': self.data.get_terms_accept(gid),
        }

    def get_log(self, gid):
        """
        Log/Timeline for the user account
        @param gid:
        @return: [log_lines]
        """
        return self.data.get_log(gid)

    @tornado.gen.coroutine
    def handle_post(self, gid, gl_user, args, body, callback=None):
        if 'agree' in args:
            result = self.agree(gid, body)
        elif 'remove' in args:
            result = yield self.drop(gid, body)
        elif 'info' in args:
            result = self.update(gid, body)
        else:
            result = None

        # sync method
        raise Return(result)

    def agree(self, gid, body):
        """
        Agree on T&Cs and/or set email options
        @param gid: master gid
        @param body: { email: True/False }
        @return: False on errors
        """
        info = {
            'tnc': True,
            'email': body['email']
        }
        self.data.set_terms_accept(gid, info)

        # send registration email
        self.data.pubsub.broadcast_command(S1.MAILER_CHANNEL_NAME, 'mail.send', gid, 'account_created')

        return True

    @tornado.gen.coroutine
    def drop(self, gid, body):
        """
        "Drop" the gid. Remove all data for this account
        *** Calls Payments Service ***
        @param gid: master gid
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
                self.logger.info("Requesting: {0}, gid: {1}...".format(request.url, gid))
                r = yield http_client.fetch(request)
                self.logger.info('Subscription cancel result: {0},{1},{2}'.format(r.code, r.reason, r.error))
                if r.code != 200:
                    raise Return({'error': 'Could not cancel billing plan. Please contact support to resolve this issue.'})
            except Exception as sub_e:
                self.logger.error("ERROR: Exception when Deleting user subscriptions, {0}".format(sub_e))
                raise Return(False)

            # delete user settings
            self.logger.info("Deleting user settings...")
            self.data.unregister_gid(gid)
            self.logger.info("User [{0}] deleted...".format(gid))
            raise Return(True)
        except Return as r:
            raise r
        except Exception as e:
            self.logger.error("ERROR: Exception in api.user.drop(), {0}".format(e))

        raise Return(False)

    def update(self, gid, body):
        """
        Update user information
        @param gid: master gid
        @param body: { email: True/False }
        @return: False on errors
        """
        info = {
            'tnc': True,
            'email': body['email']
        }
        self.data.set_terms_accept(gid, info)

        return True