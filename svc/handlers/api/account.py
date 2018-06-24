import json
import time
import tornado

from tornado.gen import Return
from tornado.ioloop import IOLoop

from core import data_api, DataDynamo
from core.data_api import DataApi
from core.model import RootAccount, SocialAccountBase, HashItem, Link, SocialAccount
from core.schema import S1
from handlers.api.base import BaseApiHandler
from handlers.provider_wrapper import BaseProviderWrapper


class AccountApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(AccountApiHandler, self).__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def handle_post(self, gl_user, args, body, callback=None):
        # check tnc status before handling post
        self.check_tnc(gl_user)

        what = set()

        if 'add' in args:
            # add is async coroutine that polls for token refresh
            r = yield self.add(gl_user, body)
            raise Return(r)
        elif 'remove' in args:
            self.remove(gl_user, body)
        elif 'link' in args and self.link(gl_user, body):
            what.add('links')
        elif 'unlink' in args:
            self.unlink(gl_user, body)
        elif 'save' in args and self.save(gl_user, body):
            what.add('links')

        elif 'sync' in args:
            self.sync(gl_user, body)

        if len(what):
            yield self.data.save_account_async(gl_user, what)

        raise Return(True)

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
        count = 0

        for tgt_acc in tgt_list:
            # promote account from temp to primary
            raw = self.data.get_linked_account(gid, tgt_acc['p'], tgt_acc['id'])
            if not raw:
                self.data.add_log(gid, 'Warning: no account info for: {0}'.format(tgt_acc))
                continue

            # refresh token
            wrap = BaseProviderWrapper()
            account = wrap.add_link(tgt_acc['p'] + ':' + tgt_acc['id'], raw, strip_token=False)
            if not account:
                self.data.add_log(gid, 'Error: No account info for: [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                continue

            if not ('token' in account and account['token']):
                self.data.add_log(gid, 'Error: No access token for: [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                continue

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
                    continue
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

            # increment sources list
            count += 1

        # purge all "temp" accounts
        self.data.purge_temp_accounts(gid)
        self.data.add_log(gid, 'Linked {0} accounts out of {1}'.format(count, len(tgt_list)))
        raise Return(count == len(tgt_list))

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

    def link(self, gl_user, body):
        """
        Links existing account to existing source
        @param gid: master gid
        @param body: [{ s: { id : id }, d: { p: provider, id: id} } ]
        @return: False on any error
        """

        for pair in body:
            src_acc = pair['s']
            tgt_acc = pair['d']

            # validate
            source_account = DataDynamo.get_account(gl_user, SocialAccount.make_key('google', src_acc['id']))
            if not source_account:
                self.logger.warning('Warning: api.link(): invalid source gid=[{0}], src=[{1}]'.format(gl_user.Key, src_acc['id']))
                raise Return(False)

            target_account = DataDynamo.get_account(gl_user, SocialAccount.make_key(tgt_acc['p'], tgt_acc['id']))
            if not target_account:
                self.logger.warning('Warning: api.link(): invalid destination gid=[{0}], dst=[{1}]'.format(gl_user.Key, tgt_acc))
                raise Return(False)

            self.link_accounts(gl_user, src_acc, tgt_acc)

        return True

    def link_accounts(self, gl_user, src_acc, dst_acc):
        """

        @type dst_acc: SocialAccount
        @type src_acc: SocialAccount
        @type gl_user: RootAccount
        """
        self.logger.info('Binding: {0}, {1} --> {2}'.format(gl_user.Key, src_acc.Key, dst_acc.Key))
        link = self.data.bind_user(gl_user, src_acc, dst_acc)
        # check url shortener
        self.data.set_gid_is_shorten_urls(link)
        # add source gid to pollers
        self.data.register_gid(src_acc)

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
    def save(self, gl_user, body):
        """
        Saves filter and other settings for the account
        @type gl_user: RootAccount
        @param gl_user: RootAccount
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

        link_key = Link.make_key('google', src_gid, destination, user)
        link = self.data.get_link(gl_user, link_key)

        # set the filter values
        self.data.filter.set_filter(gl_user, link, link_key, body['f'])

        # set schedule
        if 'sch' in body:
            link.schedule = body['sch']

        # check if need to shorten urls flag if required
        self.data.set_gid_is_shorten_urls(link)

        # cater for Redis saving values as text, so None will be 'None'
        # and if 'None' == True ...
        params = {k: v if type(v) is not bool else '1' if v else '' for k, v in body['o'].iteritems() if k in S1.PROVIDER_PARAMS}
        # merge dictionaries
        link.options.update(params)

        return True

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
