from core.data_base import DataBase


class HashItem(object):
    def __init__(self, key):
        self.Key = key

    @staticmethod
    def make_key(*args):
        return "~".join(args)

    @staticmethod
    def split_key(key):
        return key.split("~")


class SocialAccountBase(HashItem):
    def __init__(self, provider, pid):
        super(SocialAccountBase, self).__init__(HashItem.make_key(DataBase.short_provider(provider), pid))


class SocialAccount(SocialAccountBase):
    def __init__(self, provider, pid):
        super(SocialAccount, self).__init__(provider, pid)
        self.provider = provider
        self.pid = pid
        self.info = {}
        self.credentials = {}
        self.errors = 0
        self.posted_set = []
        self.message_map = []
        self.last_publish = 0


class RootAccount(SocialAccountBase):
    def __init__(self, provider, pid):
        super(RootAccount, self).__init__(provider, pid)
        self.account = None
        self.accounts = {}
        self.links = {}
        self.logs = {}


class Link(HashItem):
    def __init__(self, source, target):
        """

        @type target: str
        @type source: str
        """
        super(Link, self).__init__(HashItem.make_key(source, target))
        self.source = source
        self.target = target
        self.filters = {}
        self.options = {}
        self.schedule = None
        self.bound_stamp = None
        self.updated_stamp = None


class LogItem(HashItem):
    def __init__(self, key, messages):
        super(LogItem, self).__init__(key)
        self.messages = messages


class Schedule(object):
    def __init__(self):
        self.enabled = False
        self.days = {}
