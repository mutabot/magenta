from logging import Logger

import core


class DataCopyDynamo:
    def __init__(self, log, data, data_d=None):
        """
        @type log: Logger
        @type data: core.DataInterface
        @type data_d: core.DataInterface
        """
        self.data = data
        self.data_d = data_d
        self.log = log

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

    def dump_gid(self, gid):
        self.log.info('Dumping user, GID: {0}'.format(gid))

        # get child bindings for this account
        children = set(self.data.get_sources(gid))

        # just to be safe
        children.add(gid)
        for child in children:
            self.dump_source(gid, child)

    def dump_source(self, master_gid, gid):
        self.log.info('Copying source [{0}:{1}]...'.format(master_gid, gid))

        doc = self.data.get_activities(gid)
        if doc is None and master_gid == gid:
            self.log.info('Empty cache and self master, skipped: {0}'.format(gid))
            return

        self.data_d.register_gid(gid)
        if doc:
            self.data_d.cache_activities_doc(gid, doc, -1.0)

        # copy tokens for all linked destinations (will overwrite some data)
        links = self.data.get_linked_accounts(master_gid) or dict()
        for k in links:
            # copy token
            p = k.split(':')
            if not self.data_d.get_provider(p[0]):
                continue
