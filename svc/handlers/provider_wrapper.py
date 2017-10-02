import json

from core.data_base import DataBase
from handlers.user import facebook, twitter, tumblr, flickr, px500, linkedin

class BaseProviderWrapper(object):
    # map used to format blob for UI templates
    provider_map = {
        'facebook': facebook,
        'twitter': twitter,
        'tumblr': tumblr,
        'flickr': flickr,
        '500px': px500,
        'linkedin': linkedin,
    }

    @staticmethod
    def get_provider_from_link(link):
        p = link.split(':')[0]
        return p

    def add_link(self, link, raw, strip_token=True):
        """
        adds a linked account with all sub accounts to "accounts" blob used by UI templates
        @param link: link key in format <provider>:<id>
        @param raw: raw provider specific account data
        @return: True or False
        """
        # get provider name
        p = self.get_provider_from_link(link)
        if not (p and p in self.provider_map.keys()):
            return None

        # load raw user data
        user_data = json.loads(raw) if raw else None
        if not user_data:
            return None

        # normalize user data
        account = self.provider_map[p].UserData.populate(user_data)
        if not account:
            return None

        if strip_token:
            account.pop('token', None)

        return account

    def is_token_refresh(self, provider):
        """
        Returns true if token refresh is required for this provider
        @param provider:
        @return: True or False
        """
        return self.provider_map[provider].UserData.is_token_refresh()

class ProviderWrapper(BaseProviderWrapper):

    def __init__(self, data, sources, include_unlinked=False):
        super(ProviderWrapper, self).__init__()

        self.data = data
        # pre populate destination accounts data structure passed to UI templates
        self.accounts = {k[1]: list() for k in DataBase.short_provider_map}
        self.include_unlinked = include_unlinked
        self.sources = sources

    def purge_sources(self, account):
        """
        Removes redundant sources from the accounts
        @param account: provider account, must have ['sources']
        @return:
        """
        return set.intersection(set(account['sources']), self.sources)

    def get_accounts(self):
        return self.accounts

    def add_link(self, link, raw, strip_token=True):
        p = link.split(':')[0]
        h = DataBase.short_provider(p)
        if not h:
            return None

        a = super(ProviderWrapper, self).add_link(link, raw)
        if not a:
            return None

        # fill accounts record with sources and options
        self.data.populate_provider_bag(p, a, a['id'])

        # remove empty sources unless special case
        if not self.include_unlinked:
            a['sources'] = list(self.purge_sources(a))

        # append the accounts list
        self.accounts[h].append(a)

    def populate_linked_accounts(self, gid):
        linked = self.data.get_linked_accounts(gid) or dict()
        for link, raw in linked.iteritems():
            self.add_link(link, raw)
