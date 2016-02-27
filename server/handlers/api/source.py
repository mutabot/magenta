import tornado
from tornado.gen import Return
from core.data_api import DataApi
from handlers.api.base import BaseApiHandler


class SourceApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(SourceApiHandler, self).__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def handle_post(self, gid, gl_user, args, body, callback=None):
        # check tnc status before handling post
        self.check_tnc(gid)

        if 'poke' in args:
            result = self.poke(gid, body)
        elif 'forget' in args:
            result = self.forget(gid, body)
        elif 'clone' in args:
            result = self.clone(gid, body)
        else:
            result = None

        # sync
        raise Return(result)

    def poke(self, gid, body):
        """
        Purges Google cache for the given src_gid
        @param gid: master gid
        @param body: { id: gid}
        @return: True
        """
        self.data.register_gid(body['id'])
        return True

    def forget(self, gid, body):
        """
        Removes source account. All affected links will be unlinked, filter and other settings purged
        @param gid: master gid
        @param body: { id: gid}
        @return: False on error
        """
        self.data.forget_source(gid, body['id'])
        return True

    def clone(self, gid, body):
        """
        Clones source bindings from src source to tgt source
        @param gid: master gid
        @param body: { src_gid: src_gid, tgt_gid: tgt_gid }
        @return: True
        """
        DataApi.clone_targets(self.data, self.logger, gid, body['src_gid'], body['tgt_gid'])
        return True
