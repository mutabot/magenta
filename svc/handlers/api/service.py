import tornado
from tornado.gen import Return
from tornado.web import HTTPError
from handlers.api.base import BaseApiHandler


class ServiceApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(ServiceApiHandler, self).__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def handle_get(self, gl_user, args, callback=None):
        """

        @type gl_user: RootAccount
        """
        # check admin status before handling get
        if not self.data.get_gid_admin(gl_user):
            raise HTTPError(401)
        # always render stats
        stats = self.data.balancer.get_poller_stats_ex()
        # sync
        raise Return(stats)

    @tornado.gen.coroutine
    def handle_post(self, gl_user, args, body, callback=None):
        # check admin status before handling post
        if not self.data.get_gid_admin(gl_user):
            raise HTTPError(401)

        if 'as_user' in args:
            self.set_current_user_session(body['id'])
            result = True
        else:
            result = None

        # sync
        raise Return(result)
