import traceback
from logging import Logger

import jsonpickle

import core
from core.model import RootAccount, SocialAccount, Link
from core.schema import S1
from handlers.api.view import ViewApiHandler
from handlers.provider_wrapper import BaseProviderWrapper


class DataCopyModel:
    def __init__(self, log, data, data_d=None):
        """
        @type log: Logger
        @type data: core.Data
        @type data_d: core.Data
        """
        self.data = data
        self.data_d = data_d
        self.log = log

    def run(self, gid=None):
        if gid:
            return self.dump_gid(gid)
        else:
            return self.dump_gids()

    def dump_gids(self):
        total = 0
        c = self.data.rc.hscan(S1.destination_key_fmt('children'))
        while len(c) > 1 and c[1]:
            total += len(c[1])
            for gid in c[1]:
                self.dump_gid(gid)

            # check if the next cursor is zero
            if c[0] == '0' or c[0] == 0:
                break

            # grab next set
            c = self.data.rc.hscan(S1.destination_key_fmt('children'), c[0])

        # sleep 10 sec before retry
        self.log.info('End of gid_set, total [{0}] GIDs.'.format(total))
        self.data_d.rc.delete(S1.register_set())
        self.log.info('Cleared register set.')

    def dump_gid(self, gid):
        self.log.info('Dumping user, GID: {0}'.format(gid))

        result = RootAccount("google", gid)
        result.accounts = self.get_accounts(gid)
        result.links = self.get_links(gid)

        json = jsonpickle.encode(result, unpicklable=False)

        print json

    def get_accounts(self, root_gid):
        accounts = []

        # add google sources to accounts
        children = set(self.data.get_destination_users(root_gid, 'children'))
        children.add(root_gid)
        for gid in children:
            account = SocialAccount("google", gid)
            credentials_str = self.data.get_gid_credentials(gid)
            account.credentials = jsonpickle.json.loads(credentials_str) if credentials_str else {}
            account.info = self.data.get_gid_info(gid)
            accounts.append(account)

        # add target social accounts
        links = self.data.get_linked_accounts(root_gid) or dict()
        for link, info_str in links.iteritems():
            p = link.split(':')
            account = SocialAccount(p[0], p[1])
            account.info = info_str
            value = self.data.rc.hgetall(link)

            account.credentials = {
                "token": value["token"] if "token" in value else None,
                "expiry": value["token.expiry"] if "token.expiry" in value else None
            }
            account.errors = value["errors"] if "errors" in value else 0
            accounts.append(account)

        return accounts

    def get_links(self, root_gid):
        accounts = ViewApiHandler.get_accounts(BaseProviderWrapper(), linked=self.data.get_linked_accounts(root_gid) or dict())
        sources = {sid: self.data.get_gid_info(sid) for sid in self.data.get_gid_sources(root_gid)}
        result = list()

        for account in accounts:
            try:
                opt = dict()
                self.data.populate_provider_bag(account['provider'], opt, account['id'])
                for gid in opt['sources']:
                    if gid not in sources.keys():
                        print('Suspicious source {0}:{1}'.format(root_gid, gid))
                        continue

                    item = Link('google:' + gid, account['link'])
                    item.options = opt['op']
                    item.filters = opt['filter'][gid] if gid in opt['filter'] else None
                    item.schedule = self.data.buffer.get_schedule(gid, account['provider'], account['id'])

                    result.append(item)
            except Exception as ex:
                print ('Exception: format_result(): {0}, {1}'.format(ex, traceback.format_exc()))

        return result
