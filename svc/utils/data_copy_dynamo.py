from logging import Logger

import core
from utils.data_model import DataCopyModel


class DataCopyDynamo(object):
    def __init__(self, log, data, data_d=None):
        """
        @type log: Logger
        @type data: core.Data
        @type data_d: core.DataInterface
        """
        self.data = data
        self.data_d = data_d
        self.log = log
        self.model = DataCopyModel(log, data)

    def run(self, gid=None):
        if gid:
            return self.dump_gid(gid)
        else:
            return self.dump_gids()

    def dump_gids(self):
        total = 0
        c = self.data.scan_gid()
        while len(c) > 1 and c[1]:
            total += len(c[1])
            for gid in c[1]:
                self.dump_gid(gid)

            # check if the next cursor is zero
            if c[0] == '0' or c[0] == 0:
                break

            # grab next set
            c = self.data.scan_gid(c[0])
            if total > 20:
                break

        self.log.info('End of gid_set, total [{0}] GIDs.'.format(total))

    def dump_gid(self, root_gid):
        self.log.info('Dumping user, GID: {0}'.format(root_gid))
        self.migrate_records(root_gid)
        self.migrate_cache(root_gid)

    def migrate_cache(self, root_gid):
        # get child bindings for this account
        children = set(self.data.get_sources(root_gid))

        # just to be safe
        children.add(root_gid)
        for child in children:
            self.log.info('Copying cache [{0}:{1}]...'.format(root_gid, child))

            doc = self.data.get_activities(child)
            if doc is None and root_gid == child:
                self.log.info('Empty cache and self master, skipped: {0}'.format(child))
                return

            self.data_d.register_gid(child)
            if doc:
                self.data_d.cache_activities_doc(child, doc, -1.0)

    def migrate_records(self, root_gid):
        root = self.model.get_root_account_model(root_gid)
        self.data_d.set_log(root.pid, root.log)
        # compare = self.data_d.get_log(root.pid)

        self.data_d.set_accounts(root.pid, root.accounts)
        self.data_d.set_links(root.pid, root.links)
