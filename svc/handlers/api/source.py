import tornado
from tornado.gen import Return

from core import DataDynamo
from core.data_api import DataApi
from core.model import SocialAccount, RootAccount
from handlers.api.base import BaseApiHandler


class SourceApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(SourceApiHandler, self).__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def handle_post(self, gl_user, args, body, callback=None):
        # check tnc status before handling post
        self.check_tnc(gl_user)

        if 'poke' in args:
            result = yield self.poke(gl_user, body)
        elif 'forget' in args:
            result = self.forget(gl_user, body)
        elif 'clone' in args:
            result = self.clone(gl_user, body)
        else:
            result = None

        raise Return(result)

    @tornado.gen.coroutine
    def poke(self, gl_user, body):
        """
        Purges Google cache for the given src_gid
        @param gl_user: RootAccount
        @param body: { id: gid}
        @return: True
        """
        account = DataDynamo.get_account(gl_user, SocialAccount.make_key('google', body['id']))
        yield self.data.register_gid(gl_user, account)
        raise Return(True)

    def forget(self, gl_user, body):
        """
        Removes source account. All affected links will be unlinked, filter and other settings purged
        @type gl_user: RootAccount
        @param body: { id: gid}
        @return: False on error
        """
        self.data.forget_source(gl_user, body['id'])
        return True

    def clone(self, gl_user, body):
        # type: (RootAccount, dict) -> bool
        """
        Clones source bindings from src source to tgt source
        @param gl_user:
        @param body: { src_gid: src_gid, tgt_gid: tgt_gid }
        @return: True
        """
        DataApi.clone_targets(self.data, self.logger, gl_user, body['src_gid'], body['tgt_gid'])
        return True
