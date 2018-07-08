from core.data_base import DataBase


class HashItem(object):
    Key = None  # type: str
    deleted = None  # type: bool

    def __init__(self, key):
        self.Key = key
        self.deleted = False

    @staticmethod
    def make_key(*args):
        return "~".join(args)

    @staticmethod
    def split_key(key):
        return key.split("~")


class SocialAccountBase(HashItem):
    @staticmethod
    def make_key(provider, pid):
        return HashItem.make_key(DataBase.short_provider(provider), pid)

    def __init__(self, provider, pid):
        super(SocialAccountBase, self).__init__(HashItem.make_key(DataBase.short_provider(provider), pid))


class SocialAccount(SocialAccountBase):
    def long_key(self):
        return "{0}:{1}".format(self.provider, self.pid)

    def __init__(self, owner, provider, pid):
        super(SocialAccount, self).__init__(provider, pid)
        # TODO: Owner is assumed to be a google account, update for generic owner
        self.owner = owner              # gid od the owning google account
        self.provider = provider
        self.pid = pid
        self.info = {}
        self.credentials = {}
        self.options = {}
        self.errors = 0
        # self.posted_set = []
        self.message_map = []
        self.last_publish = 0


class RootAccount(SocialAccountBase):
    account = None      # type: SocialAccount
    options = {}        # terms: t/f, admin: t/f
    dirty = set()       # dirty record types

    def __init__(self, provider, pid):
        super(RootAccount, self).__init__(provider, pid)
        self.dirty = set()
        self.account = None
        self.accounts = {}
        self.links = {}
        self.logs = {}


class Link(HashItem):
    bound_stamp = None  # type: int
    updated_stamp = None  # type: int

    @staticmethod
    def make_key(source_provider, source_pid, target_provider, target_pid):
        src_key = SocialAccountBase.make_key(source_provider, source_pid)
        dst_key = SocialAccountBase.make_key(target_provider, target_pid)
        return HashItem.make_key(src_key, dst_key)

    def __init__(self, source_provider, source_pid, target_provider, target_pid):
        """

        @type target_provider: str
        @type source_provider: str
        """
        super(Link, self).__init__(Link.make_key(source_provider, source_pid, target_provider, target_pid))

        self.source = SocialAccount.make_key(source_provider, source_pid)
        self.target = SocialAccount.make_key(target_provider, target_pid)
        self.filters = {}
        self.options = {}
        self.schedule = None
        self.bound_stamp = None
        self.updated_stamp = None
        self.first_publish = 0


class LogItem(HashItem):
    def __init__(self, key, messages):
        """

        @type messages: list
        """
        super(LogItem, self).__init__(key)
        self.messages = messages


class Schedule(object):
    def __init__(self):
        self.enabled = False
        self.days = {}
