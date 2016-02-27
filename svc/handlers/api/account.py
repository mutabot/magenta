import json
import time
import tornado

from tornado.gen import Return
from tornado.ioloop import IOLoop

from core import data_api
from core.data_api import DataApi
from core.schema import S1
from handlers.api.base import BaseApiHandler
from handlers.provider_wrapper import BaseProviderWrapper


class AccountApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(AccountApiHandler, self).__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def handle_post(self, gid, gl_user, args, body, callback=None):
        # check tnc status before handling post
        self.check_tnc(gid)

        if 'add' in args:
            # add is async coroutine that polls for token refresh
            r = yield self.add(gid, body)
            raise Return(r)
        elif 'remove' in args:
            self.remove(gid, body)
        elif 'link' in args:
            self.link(gid, body)
        elif 'unlink' in args:
            self.unlink(gid, body)
        elif 'save' in args:
            self.save(gid, body)
        elif 'sync' in args:
            self.sync(gid, body)

    @tornado.gen.coroutine
    def add(self, gid, body):
        """
        Adds new provider accounts for this gid
        @param gid: master gid
        @param body: [{p: provider, id: id}]
        @return: True
        """
        # data must be a list of accounts to add
        src_list = body['src']
        tgt_list = body['tgt']

        # structs used for validation
        sources = set(self.data.get_gid_sources(gid).keys())

        for tgt_acc in tgt_list:
            # promote account from temp to primary
            raw = self.data.get_linked_account(gid, tgt_acc['p'], tgt_acc['id'])
            if not raw:
                self.logger.warning('Warning: no account info for: {0}'.format(tgt_acc))
                continue

            # refresh token
            wrap = BaseProviderWrapper()
            account = wrap.add_link(tgt_acc['p'] + ':' + tgt_acc['id'], raw, strip_token=False)
            if not account:
                self.logger.warning('Error: No account info for: [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                raise Return(False)

            if not ('token' in account and account['token']):
                self.logger.warning('Error: No access token for: [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                raise Return(False)

            # operate with string token now
            token = json.dumps(account['token'])
            self.data.set_user_token(gid, tgt_acc['p'], tgt_acc['id'], token)
            self.data.refresh_user_token(gid, tgt_acc['p'], tgt_acc['id'])
            self.logger.info('Token refresh for {0}:{1} ...'.format(tgt_acc['p'], tgt_acc['id']))
            # check if need to poll for token refresh for this provider
            if wrap.is_token_refresh(tgt_acc['p']):
                # poll here for registration result
                for n in range(0, 60):
                    # wait for up to 30 seconds
                    yield tornado.gen.Task(IOLoop.instance().add_timeout, time.time() + 0.5)
                    if self.data.get_user_token(gid, tgt_acc['p'], tgt_acc['id']) != token:
                        break

                if self.data.get_user_token(gid, tgt_acc['p'], tgt_acc['id']) != token:
                    # promote account
                    self.data.link_provider_account(gid, tgt_acc['p'], tgt_acc['id'])
                else:
                    self.data.add_log(gid, 'Error: Failed to register account [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                    self.logger.warning('Error: Failed to refresh token [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                    raise Return(False)
            else:
                # not waiting for token refresh
                # promote account
                self.data.link_provider_account(gid, tgt_acc['p'], tgt_acc['id'])

            # auto-link to sources
            for src_acc in src_list:
                if src_acc['id'] not in sources:
                    self.logger.warning('Warning: api.add(): invalid source gid=[{0}], src=[{1}]'.format(gid, src_acc['id']))
                    continue
                self.link_accounts(gid, src_acc, tgt_acc)

        # purge all "temp" accounts
        self.data.purge_temp_accounts(gid)
        self.logger.info('Token refresh complete.')
        raise Return(True)

    def remove(self, gid, body):
        """
        Removes destination account and unlinks all sources from it
        @param gid: master gid
        @param body: { p: provider, id: id }
        @return: True on success
        """
        try:
            result = data_api.DataApi.forget_destination(self.data, self.logger, gid, body['p'], body['id'])
        except Exception as e:
            self.logger.exception("ERROR: in api.account.remove() {0}".format(e))
            raise Return(False)

        raise Return(result)

    def link(self, gid, body):
        """
        Links existing account to existing source
        @param gid: master gid
        @param body: [{ s: { id : id }, d: { p: provider, id: id} } ]
        @return: False on any error
        """
        # structs used for validation
        sources = set(self.data.get_gid_sources(gid).keys())

        for pair in body:
            src_acc = pair['s']
            tgt_acc = pair['d']

            # validate
            if src_acc['id'] not in sources:
                self.logger.warning('Warning: api.link(): invalid source gid=[{0}], src=[{1}]'.format(gid, src_acc['id']))
                raise Return(False)

            if not self.data.is_linked_account(gid, tgt_acc['p'], tgt_acc['id']):
                self.logger.warning('Warning: api.link(): invalid destination gid=[{0}], dst=[{1}]'.format(gid, tgt_acc))
                raise Return(False)

            self.link_accounts(gid, src_acc, tgt_acc)

        raise Return(True)

    def link_accounts(self, gid, src_acc, dst_acc):
        self.logger.info('Binding: {0}:{1} --> {2}:{3}'.format(gid, src_acc['id'], dst_acc['p'], dst_acc['id']))
        self.data.bind_user(gid, src_acc['id'], dst_acc['p'], dst_acc['id'])
        # check url shortener
        self.data.set_gid_is_shorten_urls(src_acc['id'])
        # add source gid to pollers
        self.data.register_gid(src_acc['id'])

    def unlink(self, gid, body):
        """
        Breaks existing gid --> provider:id link
        @param gid: maser gid
        @param body: [{ s: { id : id }, d: { p: provider, id: id} } ]
        @return: False on any errors
        """
        # structs used for validation
        sources = set(self.data.get_gid_sources(gid).keys())
        for pair in body:
            src_acc = pair['s']
            dst_acc = pair['d']

            # validate
            if not src_acc['id'] in sources:
                self.logger.warning('Error: api.unlink(): invalid source gid=[{0}], src=[{1}]'.format(gid, src_acc['id']))
                raise Return(False)

            if not self.data.is_linked_account(gid, dst_acc['p'], dst_acc['id']):
                self.logger.warning('Error: api.unlink(): invalid destination gid=[{0}], dst=[{1}]'.format(gid, dst_acc))
                raise Return(False)

            self.logger.info('Unbinding: {0}:{1} --> {2}:{3}'.format(gid, src_acc['id'], dst_acc['p'], dst_acc['id']))
            self.data.remove_binding(src_acc['id'], dst_acc['p'], dst_acc['id'])

            # check url shortener
            self.data.set_gid_is_shorten_urls(src_acc['id'])

        raise Return(True)

    # noinspection PyUnusedLocal
    def save(self, gid, body):
        """
        Saves filter and other settings for the account
        @param gid: master gid
        @param body: {
                        l: { s: source gid, p: provider, id: destination id},
                        f: filter,
                        s: schedule,
                        op: options
                    }
        @return: False on any error
        """

        src_gid = body['l']['s']
        destination = body['l']['p']
        user = body['l']['id']

        # set the filter values
        self.data.filter.set_filter(destination, src_gid, user, body['f'])

        # set schedule
        if 'sch' in body:
            schedule = body['sch']
            self.data.buffer.set_schedule(src_gid, '{0}:{1}'.format(destination, user), schedule)

        # check if need to shorten urls flag if required
        self.data.set_gid_is_shorten_urls(src_gid)

        # cater for Redis saving values as text, so None will be 'None'
        # and if 'None' == True ...
        params = {k: v if type(v) is not bool else '1' if v else '' for k, v in body['o'].iteritems() if k in S1.PROVIDER_PARAMS}
        for param, value in params.iteritems():
            self.data.provider[destination].set_user_param(user, param, value)

        raise Return(True)

    def sync(self, gid, body):
        """
        Synchronizes filter and other settings for accounts
        @param gid: master gid
        @param body: {
                        ref: { s: source gid, p: provider, id: destination id},
                        tgt: [{ s: source gid, p: provider, id: destination id}],
                        in: ['keyword', 'keyword_merge', 'schedule', 'tagline']
                    }
        """

        source_link = ('gl', body['ref']['s'], body['ref']['p'], body['ref']['id'])
        target_link_list = [('gl', l['s'], l['p'], l['id']) for l in body['tgt']]

        DataApi.sync_settings(self.data, self.logger, gid, source_link, target_link_list, body['in'])
        raise Return(True)
