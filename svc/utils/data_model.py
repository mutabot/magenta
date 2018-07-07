import traceback
from logging import Logger

import jsonpickle

import core
from core.model import RootAccount, SocialAccount, Link
from core.model.model import LogItem
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
        gid = root_gid
        self.log.info('Root model for [google:{0}]'.format(gid))

        result = RootAccount('google', gid)
        result.accounts = self.get_accounts(gid)
        result.links = self.get_links(gid)
        result.logs = self.get_log(gid)
        result.account = result.accounts[result.Key]
        result.options = result.account.info['magenta'] if 'magenta' in result.account.info else {}

        return result

    def get_accounts(self, root_gid):
        accounts = {}

        # add google sources to accounts
        children = set(self.data.get_destination_users(root_gid, 'children'))
        children.add(root_gid)
        for gid in children:
            account = SocialAccount(root_gid, "google", gid)

            credentials_str = self.data.get_gid_credentials(gid)
            account.credentials = jsonpickle.json.loads(credentials_str) if credentials_str else {}

            info_dict = self.data.get_gid_info(gid)
            account.info = info_dict if info_dict else {}

            if gid == root_gid:
                magenta_bag = {
                    'admin': bool(self.data.get_gid_admin(gid)),
                    'terms': self.data.get_terms_accept(gid),
                    'limits': self.data.get_limits(gid),
                }
                account.info['magenta'] = magenta_bag

            account.options[S1.cache_shorten_urls()] = self.data.get_destination_param(gid,
                                                                                       'cache',
                                                                                       '',
                                                                                       S1.cache_shorten_urls())
            accounts[account.Key] = account

            # aux options
            # mark account polled
            account.options['polled'] = True

        self.log.info('{0} google accounts'.format(len(accounts)))

        # add target social accounts
        links = self.data.get_linked_accounts(root_gid) or dict()
        for link, info_str in links.iteritems():
            p = link.split(':')
            account = SocialAccount(root_gid, p[0], p[1])
            account.info = jsonpickle.loads(info_str) if info_str else {}

            value = self.data.rc.hgetall(link)

            account.options = value
            account.credentials = {
                "token": value["token"] if "token" in value else None,
                "expiry": value["token.expiry"] if "token.expiry" in value else None
            }
            account.errors = int(value["errors"]) if "errors" in value else 0
            account.message_map = self.data.filter.get_message_id_map(p[0], p[1])
            last_publish = self.data.get_publisher_value(link, 'last_publish')
            account.last_publish = float(last_publish) if last_publish else 0.0

            # load provider specific params
            # this is already done above by hgetall
            # account.options.update(self.data.provider[p[0]].get_user_params(p[1]))

            accounts[account.Key] = account

        self.log.info('{0} total accounts'.format(len(accounts)))
        return accounts

    def get_links(self, root_gid):
        accounts = ViewApiHandler.get_accounts(BaseProviderWrapper(), linked=self.data.get_linked_accounts(root_gid) or dict())
        sources = {sid: self.data.get_gid_info(sid) for sid in self.data.get_gid_sources(root_gid)}
        result = dict()

        for account in accounts:
            try:
                opt = dict()
                self.data.populate_provider_bag(account['provider'], opt, account['id'])
                for gid in opt['sources']:
                    if gid not in sources.keys():
                        print('Suspicious source {0}:{1}'.format(root_gid, gid))
                        continue

                    target = account['link'].split(':')
                    item = Link('google', gid, target[0], target[1])
                    item.options = opt['op']
                    item.filters = opt['filter'][gid] if gid in opt['filter'] else None
                    item.schedule = self.data.buffer.get_schedule(gid, account['provider'], account['id'])
                    item.bound_stamp = int(self.data.get_destination_param(gid, account['provider'], account['id'], S1.bound_key()))
                    item.updated_stamp = int(self.data.get_destination_param(gid, account['provider'], account['id'], S1.updated_key()))
                    item.options['active'] = True
                    item.first_publish = self.data.get_destination_first_use(gid, account['provider'], account['id'])

                    if not (item.filters is not None and 'keyword' in item.filters and item.filters['keyword']):
                        print ('No keywords for: {0}'.format(item.Key))

                    result[item.Key] = item
            except Exception as ex:
                print ('Exception: format_result(): {0}, {1}'.format(ex, traceback.format_exc()))

        self.log.info('{0} links'.format(len(result)))
        return result

    def get_log(self, root_gid):
        tuple_log_dict = self.data.get_log(root_gid)
        result = {
            k: LogItem(k, [[ll for ll in l] for l in tuple_list])
            for k, tuple_list in tuple_log_dict.iteritems()
        }
        self.log.info('{0} log items'.format(len(result)))
        return result
