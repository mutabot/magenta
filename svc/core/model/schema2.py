class S2(object):
    def __init__(self):
        pass

    @staticmethod
    def log_key_name(root_pid):
        return '{0}:log'.format(root_pid)

    @staticmethod
    def accounts_key_name(root_pid):
        return '{0}:accounts'.format(root_pid)
