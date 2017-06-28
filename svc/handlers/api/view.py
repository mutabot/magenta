import traceback
import tornado
from tornado.gen import Return
from handlers.api.base import BaseApiHandler
from handlers.provider_wrapper import BaseProviderWrapper


class ViewApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(ViewApiHandler, self).__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def handle_get(self, gid, gl_user, args, callback=None):
        if 'sources' in args:
            # build sources data structure
            sources = {sid: self.data.get_gid_info(sid) for sid in self.data.get_gid_sources(gid)}
            result = [self.format_google_source(src) for src in sources.itervalues()]

        elif 'accounts' in args:
            # get accounts
            accounts = self.get_accounts(gid, BaseProviderWrapper(), linked=self.data.get_linked_accounts(gid) or dict())

            # build sources data structure
            sources = {sid: self.data.get_gid_info(sid) for sid in self.data.get_gid_sources(gid)}

            # format result
            result = self.format_result(accounts, sources)

        elif 'selector' in args:
            # prepare accounts
            accounts_c = self.get_accounts(gid, BaseProviderWrapper(), linked=self.data.get_linked_accounts(gid) or dict())
            accounts_t = self.get_accounts(gid, BaseProviderWrapper(), linked=self.data.get_linked_accounts(gid, True) or dict())

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
            sources = {sid: self.data.get_gid_info(sid) for sid in self.data.get_gid_sources(gid)}

            # format result
            result = {'sel': self.format_result(accounts, {}), 'src': sources}

        else:
            result = None

        # sync
        raise Return(result)

    @staticmethod
    def get_accounts(gid, wrapper, linked):
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
                                'sch': self.data.buffer.get_schedule(gid, '{provider}:{id}'.format(**account))
                            }
                            for gid in opt['sources'] if gid in sources.keys()
                        ]
                    })
            except Exception as ex:
                self.logger.error('Exception: format_result(): {0}, {1}'.format(ex, traceback.format_exc()))

        return result