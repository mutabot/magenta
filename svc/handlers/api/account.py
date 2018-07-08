import json
import time

import tornado
from tornado.gen import Return
from tornado.ioloop import IOLoop

from core import DataDynamo
from core.data_api import DataApi
from core.model import RootAccount, Link, SocialAccount
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

        result = False
        if 'add' in args:
            # add is async coroutine that polls for token refresh
            gl_user = yield self.add(gl_user, body)
            result = True
        elif 'remove' in args:
            self.remove(gl_user, body)
            result = True
        elif 'link' in args and self.link(gl_user, body):
            gl_user.dirty.add('links')
            result = True
        elif 'unlink' in args:
            self.unlink(gl_user, body)
            result = True
        elif 'save' in args and self.save(gl_user, body):
            gl_user.dirty.add('links')
            result = True
        elif 'sync' in args:
            self.sync(gl_user, body)
            result = True

        if len(gl_user.dirty):
            yield self.data.save_account_async(gl_user)

        raise Return(result)

    @tornado.gen.coroutine
    def add(self, gl_user, body):
        # type: (RootAccount, object) -> RootAccount
        """
        Adds new provider accounts for this gid
        @type gl_user: RootAccount
        @param body: [{p: provider, id: id}]
        @return:
        """
        # data must be a list of accounts to add
        src_list = body['src']
        tgt_list = body['tgt']

        # structs used for validation
        # sources = set(self.data.get_gid_sources(gid).keys())
        count = 0

        for tgt_acc in tgt_list:
            # promote account from temp to primary
            new_account_key = SocialAccount(gl_user.account.pid, tgt_acc['p'], tgt_acc['id']).Key
            new_account = DataDynamo.get_account(gl_user, new_account_key)  # type: SocialAccount
            # raw = self.data.get_linked_account(gid, tgt_acc['p'], tgt_acc['id'])
            if not new_account:
                self.data.add_log(gl_user, gl_user.account.pid, 'Warning: no account info for: {0}'.format(tgt_acc))
                continue

            # refresh token
            wrap = BaseProviderWrapper()
            account_info = wrap.add_link(tgt_acc['p'] + ':' + tgt_acc['id'], new_account.info, strip_token=False)
            if not account_info:
                self.data.add_log(gl_user, gl_user.account.pid,
                                  'Error: No account info for: [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                continue

            if not ('token' in account_info and account_info['token']):
                self.data.add_log(gl_user, gl_user.account.pid,
                                  'Error: No access token for: [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                continue

            # do not overwrite raw account info
            # new_account.info = account_info

            # operate with string token now
            token = json.dumps(account_info['token'])
            self.data.set_user_token(new_account, token, None)

            # sync data to the db for the token provider to pick it up
            gl_user.dirty.add('accounts')
            yield self.save_google_user(gl_user)

            # initiate token refresh
            self.data.refresh_user_token(gl_user, tgt_acc['p'], tgt_acc['id'])
            self.logger.info('Token refresh for {0}:{1} ...'.format(tgt_acc['p'], tgt_acc['id']))

            # check if need to poll for token refresh for this provider
            if wrap.is_token_refresh(tgt_acc['p']):
                # poll here for registration result
                for n in range(0, 60):
                    # wait for up to 30 seconds
                    yield tornado.gen.Task(IOLoop.instance().add_timeout, time.time() + 0.5)

                    # refresh data
                    # *** MUTATING gl_user reference ***
                    gl_user = yield self.get_google_user()

                    if self.data.get_user_token(gl_user, tgt_acc['p'], tgt_acc['id']) != token:
                        break

                if self.data.get_user_token(gl_user, tgt_acc['p'], tgt_acc['id']) != token:
                    # promote account
                    self.promote_account(gl_user, new_account_key)

                else:
                    self.data.add_log(gl_user, gl_user.account.pid,
                                      'Error: Failed to register account [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                    self.logger.warning('Error: Failed to refresh token [{0}:{1}]'.format(tgt_acc['p'], tgt_acc['id']))
                    continue
            else:
                # not waiting for token refresh
                # promote account
                self.promote_account(gl_user, new_account_key)

            # auto-link to sources
            for src_acc in src_list:
                source_key = SocialAccount('', src_acc['p'], src_acc['id'])
                source_account = DataDynamo.get_account(gl_user, source_key)
                if not source_account:
                    self.logger.warning('Warning: api.add(): invalid source gid=[{0}], src=[{1}]'
                                        .format(gl_user.Key, src_acc['id']))
                    continue
                target_key = SocialAccount('', tgt_acc['p'], tgt_acc['id'])
                target_account = DataDynamo.get_account(gl_user, target_key)
                self.link_accounts(gl_user, source_account, target_account)

            # increment sources list
            count += 1

        # purge all "temp" accounts
        self.data.purge_temp_accounts(gl_user)
        self.data.add_log(gl_user, gl_user.account.pid, 'Linked {0} accounts out of {1}'.format(count, len(tgt_list)))

        raise Return(gl_user)

    def promote_account(self, gl_user, new_account_key):
        new_account = DataDynamo.get_account(gl_user, new_account_key)
        if 'temp' in new_account.options:
            new_account.options.pop('temp')

        # set dirty flag as we have mutated the account
        gl_user.dirty.add('accounts')

    def remove(self, gl_user, body):
        """
        Removes destination account and unlinks all sources from it
        @type gl_user: RootAccount
        @param body: { p: provider, id: id }
        @return: True on success
        """
        try:
            removing = SocialAccount(gl_user.account.pid, body['p'], body['id'])

            # remove from accounts dict
            if removing.Key in gl_user.accounts:
                gl_user.accounts.pop(removing.Key)
                gl_user.dirty.add('accounts')

            # remove all links
            link_keys = [link.Key for link in gl_user.links.itervalues() if link.target == removing.Key]
            if len(link_keys):
                gl_user.dirty.add('links')
            for link_key in link_keys:
                gl_user.links.pop(link_key)

        except Exception as e:
            self.logger.exception("ERROR: in api.account.remove() {0}".format(e))
            return False

        return True

    def link(self, gl_user, body):
        """
        Links existing account to existing source
        @param gid: master gid
        @param body: [{ s: { id : id }, d: { p: provider, id: id} } ]
        @return: False on any error
        """

        for pair in body:
            src_acc_ref = pair['s']
            tgt_acc_fer = pair['d']

            # validate
            source_account = DataDynamo.get_account(gl_user, SocialAccount.make_key('google', src_acc_ref['id']))
            if not source_account:
                self.logger.warning('Warning: api.link(): invalid source gid=[{0}], src=[{1}]'.format(gl_user.Key, src_acc_ref['id']))
                raise Return(False)

            target_account = DataDynamo.get_account(gl_user, SocialAccount.make_key(tgt_acc_fer['p'], tgt_acc_fer['id']))
            if not target_account:
                self.logger.warning('Warning: api.link(): invalid destination gid=[{0}], dst=[{1}]'.format(gl_user.Key, tgt_acc_fer))
                raise Return(False)

            self.link_accounts(gl_user, source_account, target_account)

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
        self.data.register_gid(gl_user, src_acc)

    def unlink(self, gl_user, body):
        # type: (RootAccount, dict) -> bool
        """
        Breaks existing gid --> provider:id link
        @param body: [{ s: { id : id }, d: { p: provider, id: id} } ]
        @return: False on any errors
        """
        # structs used for validation
        for pair in body:
            src_acc = pair['s']
            dst_acc = pair['d']

            # find the link
            # TODO: Google hardcoded
            key = Link('google', src_acc['id'], dst_acc['p'], dst_acc['id']).Key

            if key not in gl_user.links:
                self.logger.warning(
                    'Error: api.unlink(): link not found for gid=[{0}], src=[{1}:{2}], dst=[{3}:{4}]'
                    .format(gl_user.Key, src_acc['p'], src_acc['id'], dst_acc['p'], dst_acc['id']))
                continue

            link = gl_user.links[key]
            self.logger.info('Unbinding: {0} --> {1}'.format(link.source, link.target))

            self.data.remove_binding(gl_user, link)

        return True

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
