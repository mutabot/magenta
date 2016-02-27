import json
from logging import Logger
import core


class DataDump:
    def __init__(self, log, data):
        """
        @type log: Logger
        @type data: core.Data
        """
        self.data = data
        self.log = log

    def print_key(self, key):
        print ('"{0}":'.format(key))
        if self.dump_hash(key):
            pass
        elif self.dump_list(key):
            pass
        elif self.dump_set(key):
            pass
        else:
            return False
        return True

    def dump(self):
        total = 0
        errors = 0
        keys = self.data.rc.keys('*')
        print('{')
        for key in sorted(keys):
            if total:
                print(',')

            total += 1
            if not self.print_key(key):
                errors += 1

        print('}')

        self.log.info('Dumped [{0}] keys, [{1}] errors'.format(total, errors))

    def dump_hash(self, key):
        try:
            a = self.data.rc.hgetall(key)
            print(json.dumps(a))
            return True
        except:
            return False

    def dump_list(self, key):
        try:
            a = self.data.rc.lrange(key, 0, -1)
            print(json.dumps(sorted(a)))
            return True
        except:
            return False

    def dump_set(self, key):
        try:
            a = self.data.rc.smembers(key)
            print(json.dumps(sorted(list(a))))
            return True
        except:
            return False