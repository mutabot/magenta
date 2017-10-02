class S2(object):
    def __init__(self):
        pass

    @staticmethod
    def document_key_name(root_pid, document_name):
        return '{0}:{1}'.format(root_pid, document_name)

    @staticmethod
    def cache_key(table_name, gid):
        return '{0}:{1}'.format(gid, table_name)

    @staticmethod
    def Generals():
        return 'poll:general:set'

    @staticmethod
    def poll_list():
        return 'poll:list'
