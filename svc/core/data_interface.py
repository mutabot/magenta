from abc import abstractmethod, ABCMeta


class DataInterface(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod
    def is_loading(self):
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
    def activities_doc_from_item(self, item):
        """
        extracts the activities document from the item record
        @param item:
        @return: Google Activities record
        """
        pass
