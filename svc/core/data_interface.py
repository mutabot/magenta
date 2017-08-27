from abc import abstractmethod, ABCMeta


class DataInterface(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

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
    def register_gid(self, gid):
        """
        registers the gid in the system for pollers to start polling
        forces pollers to update cache
        @param gid: google user id
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
    def unregister_gid(self, gid):
        """
        unregister user and remove all data associated with it
        @param gid: google user id
        """
        pass

    @abstractmethod
    def scan_gid(self, page=None):
        """
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
        # type: (str, object, float) -> bool
        """
        process Google Plus source activities doc
        @return true if document was updated with new data
        @type collision_window: float
        @param collision_window: lookbehind in seconds, will not update if current stamp on the item is within the window
        @param activities_doc: document (Google Plus only for now)
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
        @type log: dict
        """
        pass

    @abstractmethod
    def set_accounts(self, root_pid, accounts):
        pass

    @abstractmethod
    def get_accounts(self, root_pid, accounts):
        pass

    @abstractmethod
    def set_links(self, root_pid, links):
        pass

    @abstractmethod
    def set_links(self, root_pid, links):
        pass

    @abstractmethod
    def cache_pid_records(self, root_pid):
        pass

    @abstractmethod
    def commit_pid_records(self, root_pid):
        pass
