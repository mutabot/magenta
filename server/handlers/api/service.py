import tornado
from tornado.gen import Return
from tornado.web import HTTPError
from handlers.api.base import BaseApiHandler


class ServiceApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(ServiceApiHandler, self).__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def handle_get(self, gid, gl_user, args, callback=None):
        # check admin status before handling get
        if not self.data.get_gid_admin(gid):
            raise HTTPError(401)
        # always render stats
        stats = self.data.balancer.get_poller_stats_ex()
        # sync
        raise Return(stats)

    @tornado.gen.coroutine
    def handle_post(self, gid, gl_user, args, body, callback=None):
        # check admin status before handling post
        if not self.data.get_gid_admin(gid):
            raise HTTPError(401)

        if 'as_user' in args:
            result = self.login_as(gid, body)
        else:
            result = None

        # sync
        raise Return(result)

    def login_as(self, gid, body):
        """
        Sets a user id cookie to a specified user
        @param gid: master gid
        @param body: { id: gid }
        @return: False on error
        """
        self.set_current_user_session(body['id'])
        return True