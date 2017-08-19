
class SocialAccount(object):
    def __init__(self, provider, pid):
        self.provider = provider
        self.pid = pid
        self.info = {}
        self.credentials = {}
        self.errors = 0
        self.posted_set = []
        self.log = []


class RootAccount(SocialAccount):
    def __init__(self, provider, pid):
        super(RootAccount, self).__init__(provider, pid)
        self.accounts = []
        self.links = []


class Link(object):
    def __init__(self, source, target):
        """

        @type target: str
        @type source: str
        """
        self.source = source
        self.target = target
        self.filters = {}
        self.options = {}
        self.schedule = None
        self.bound_stamp = None
        self.updated_stamp = None


class Schedule(object):
    def __init__(self):
        self.enabled = False
        self.days = {}
