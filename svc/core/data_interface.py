from abc import abstractmethod, ABCMeta
from core.balancer import Balancer
from core.buffer import Buffer
from core.filter import FilterData
from core.pubsub import Pubsub


class DataInterface(object):
    buffer = None  # type: Buffer
    balancer = None  # type: Balancer
    pubsub = None  # type: Pubsub
    filter = None  # type: FilterData
    __metaclass__ = ABCMeta

    def __init__(self):
        self.buffer = None
        self.pubsub = None
        self.balancer = None
        self.filter = None

    @abstractmethod
    def is_loading(self):
        pass

    @abstractmethod
    def flush(self, root_pid):
        """
        DynamoDb support. Flushes the db_context data into the database
        @return:
        """
        pass

    @abstractmethod
    def register_gid(self, gl_user, source_account=None):
        """
        registers the gid in the system for pollers to start polling
        forces pollers to update cache
        @param source_account:
        @param gl_user:
        """
        pass

    @abstractmethod
    def remove_from_poller(self, gid):
        """
        Removes the gid from polling queue
        @param gid:
        @return:
        """
        pass

    @abstractmethod
    def unregister_gid(self, gl_user):
        """
        un-register user and remove all data associated with it
        @param gl_user: root account
        """
        pass

    @abstractmethod
    def scan_gid(self, page=None):
        """
        """
        pass

    @abstractmethod
    def poll(self):
        """
        polls the gid set table for gids due to be polled
        @return:
        """
        pass

    @abstractmethod
    def get_sources(self, gid):
        """
        returns a list of gids associated with this master gid
        @param gid:
        @return:
        """
        pass

    @abstractmethod
    def cache_activities_doc(self, gid, activities_doc, collision_window=0.0):
        """
        Google only
        @param gid:
        @param activities_doc:
        @param collision_window:
        @return:
        """
        pass

    @abstractmethod
    def cache_provider_doc(self, social_account, activity_doc, activity_map, expires=0.0):
        # type: (object, object, object, float) -> bool
        """
        process source activities doc
        @param activity_map: activity map
        @param social_account: account to cache data for
        @return true if document was updated with new data
        @type expires: float
        @param expires: lookbehind in seconds, will not update if current stamp on the item is within the window
        @param activity_doc: document
        """
        pass

    @abstractmethod
    def get_activities(self, gid):
        """
        returns the most recent activities document for the gid
        @param gid:
        @return: activities document
        """
        pass

    @abstractmethod
    def activities_doc_from_item(self, item):
        """
        extracts the activities document from the item record
        @param item:
        @return: Google Activities record
        """
        pass

    @abstractmethod
    def get_linked_accounts(self, gid, temp=False):
        """
        returns a dict of linked accounts by target type
        @param gid:
        @param temp: include temp accounts being authenticated now
        @return: dict
        """
        pass

    @abstractmethod
    def get_provider(self, provider_name):
        """
        returns a target provider instance or None
        @param provider_name:
        @return:
        """
        pass

    @abstractmethod
    def get_log(self, gid):
        pass

    @abstractmethod
    def add_log(self, gid, message):
        pass

    @abstractmethod
    def set_log(self, root_pid, log):
        """
        @param root_pid: root account id
        @type log: dict
        """
        pass

    @abstractmethod
    def set_model_document(self, document_name, root_key, items):
        pass

    @abstractmethod
    def get_accounts(self, root_key, accounts):
        pass

    @abstractmethod
    def cache_pid_records(self, root_key):
        pass

    @abstractmethod
    def commit_pid_records(self, root_key):
        pass

    @abstractmethod
    def get_gid_info(self, gl_user):
        pass

    @abstractmethod
    def del_all_provider_sessions(self, gid):
        pass

    @abstractmethod
    def get_terms_accept(self, root_acc):
        pass

    @abstractmethod
    def load_account_async(self, root_gid):
        pass

    @abstractmethod
    def save_account_async(self, root_acc, what=None):
        pass

    @abstractmethod
    def add_linked_account(self, pid, gid, root_acc=None):
        pass

    @abstractmethod
    def get_gid_admin(self, gid):
        pass

    @abstractmethod
    def set_terms_accept(self, gl_user, info):
        pass

    @abstractmethod
    def get_limits(self, gl_user):
        pass

    @abstractmethod
    def get_gid_sources(self, gl_user):
        pass

    @abstractmethod
    def populate_provider_bag(self, param, opt, param1):
        pass

    @abstractmethod
    def set_gid_is_shorten_urls(self, src_gid):
        pass

    @abstractmethod
    def get_link(self, gl_user, link_key):
        pass

    @abstractmethod
    def bind_user(self, gid, param, param1, param2):
        pass
