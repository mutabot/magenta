import traceback
from logging import Logger

import jsonpickle

import core
from core.model import RootAccount, SocialAccount, Link
from core.schema import S1
from handlers.api.view import ViewApiHandler
from handlers.provider_wrapper import BaseProviderWrapper


class DataCopyModel:
    def __init__(self, log, data):
        """
        @type data: core.Data
        @type log: Logger
        """
        self.data = data
        self.log = log

    def get_root_account_model(self, root_gid):
        """

        @rtype: RootAccount
        """
        self.log.info('Root model for [google:{0}]'.format(root_gid))

        result = RootAccount("google", root_gid)
        result.accounts = self.get_accounts(root_gid)
        result.links = self.get_links(root_gid)
        result.log = self.get_log(root_gid)

        return result

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

        self.log.info('{0} google accounts'.format(len(accounts)))

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
            account.message_map = self.data.filter.get_message_id_map(p[0], p[1])
            account.last_publish = self.data.get_publisher_value(link, 'last_publish')

            accounts.append(account)

        self.log.info('{0} total accounts'.format(len(accounts)))
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
                    item.bound_stamp = self.data.get_destination_param(gid, account['provider'], account['id'], S1.bound_key())
                    item.updated_stamp = self.data.get_destination_param(gid, account['provider'], account['id'], S1.updated_key())

                    result.append(item)
            except Exception as ex:
                print ('Exception: format_result(): {0}, {1}'.format(ex, traceback.format_exc()))

        self.log.info('{0} links'.format(len(result)))
        return result

    def get_log(self, root_gid):
        tuple_log_dict = self.data.get_log(root_gid)
        result = {
            k: [[ll for ll in l] for l in tuple_list]
            for k, tuple_list in tuple_log_dict.iteritems()
        }
        self.log.info('{0} log items'.format(len(result)))
        return result
