import traceback
import tornado
from tornado.gen import Return

from core import DataDynamo
from handlers.api.base import BaseApiHandler
from handlers.provider_wrapper import BaseProviderWrapper
from core.model import RootAccount, SocialAccount
from providers.google_rss import GoogleRSS


class ViewApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(ViewApiHandler, self).__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def handle_get(self, gl_user, args, callback=None):
        if 'sources' in args:
            # build sources data structure
            children = gl_user.accounts
            result = [self.format_google_source(child.info) for child in children.itervalues()]

        elif 'accounts' in args:
            # get accounts
            accounts = self.get_accounts(BaseProviderWrapper(), linked=self.data.get_linked_accounts(gl_user) or dict())

            # build sources data structure
            children = gl_user.accounts
            sources = {child.pid: child.info for child in children.itervalues()}

            # format result
            result = self.format_result_v2(gl_user)

        elif 'selector' in args:
            # prepare accounts
            accounts_c = self.get_accounts(BaseProviderWrapper(), linked=self.data.get_linked_accounts(gl_user) or dict())
            accounts_t = self.get_accounts(BaseProviderWrapper(), linked=self.data.get_linked_accounts(gl_user, True) or dict())

            account_c_set = set(['{0}:{1}'.format(a['provider'], a['id']) for a in accounts_c])
            account_t_set = set(['{0}:{1}'.format(a['provider'], a['id']) for a in accounts_t])

            # filter temp accounts not in the main list
            if not self.get_argument('full', default=None) is None:
                accounts = accounts_c
            elif not self.get_argument('refresh', default=None) is None:
                account_set = account_t_set.intersection(account_c_set)
                accounts = [a for a in accounts_t if '{0}:{1}'.format(a['provider'], a['id']) in account_set]
            else:
                account_set = account_t_set.difference(account_c_set)
                accounts = [a for a in accounts_t if '{0}:{1}'.format(a['provider'], a['id']) in account_set]

            # build sources data structure
            sources = {sid: self.data.get_gid_info(sid) for sid in self.data.get_gid_sources(gl_user)}

            # format result
            result = {'sel': self.format_result(accounts, {}), 'src': sources}

        else:
            result = None

        # sync
        raise Return(result)

    @staticmethod
    def get_accounts(wrapper, linked):
        result = list()

        # populate provider wrapper with account links
        for link, raw in linked.iteritems():
            a = wrapper.add_link(link, raw)
            if not a:
                continue

            p = wrapper.get_provider_from_link(link)
            result.append(
                {
                    'id': a['id'],
                    'provider': p,
                    'account': a,
                    'link': link
                })

        return result

    def format_result_v2(self, gl_user):
        """

        @type gl_user: RootAccount
        """
        result = list()

        for account in gl_user.accounts.itervalues():
            source_links = {link.source: link for link in gl_user.links.itervalues() if DataDynamo.get_account_key_from_ref(link.target) == account.Key}

            # skip over if the account is not linked
            if len(source_links) == 0:
                continue

            first_target = source_links.itervalues().next()
            sources = [
                {
                    'a': DataDynamo.get_account_info(gl_user, link.source),
                    'filter': link.filters,
                    'sch': link.schedule
                }
                for (link_source, link) in source_links.iteritems()
            ]

            result.append(
                {
                    'a': account.info,
                    'p': account.provider,
                    'l': first_target.target,
                    'op': first_target.options,
                    'src': sources
                })

        return result

    def format_result(self, accounts, sources):
        # fill accounts record with sources and options

        result = list()

        for account in accounts:
            try:
                opt = dict()
                self.data.populate_provider_bag(account['provider'], opt, account['id'])
                result.append(
                    {
                        'a': account['account'],
                        'p': account['provider'],
                        'l': account['link'],
                        'op': opt['op'],
                        'src': [
                            {
                                'a': self.format_google_source(sources[gid]),
                                'filter': opt['filter'][gid] if gid in opt['filter'] else None,
                                'sch': self.data.buffer.get_schedule(gid, account['provider'], account['id'])
                            }
                            for gid in opt['sources'] if gid in sources.keys()
                        ]
                    })
            except Exception as ex:
                self.logger.error('Exception: format_result(): {0}, {1}'.format(ex, traceback.format_exc()))

        return result
