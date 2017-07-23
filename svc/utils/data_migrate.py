from logging import Logger
import traceback

import core


class DataMigrate:
    def __init__(self, log, data_old, data_new):
        """
        @type log: Logger
        @type data_new: core.Data
        @type data_old: legacy_1.data.Data
        """
        self.data_old = data_old
        self.data_new = data_new
        self.log = log

    def migrate(self):

        """
        total = 0
        errors = 0

        c = self.data_new.rc.sscan(S1.gid_set('all'))
        while c and c[0] and c[1]:
            gid_set = c[1]
            self.log.info('Migrating [{0}] gids...'.format(len(gid_set)))
            total += len(gid_set)
            for gid in gid_set:
                errors += self.migrate_gid(gid)

            if c[0] == '0':
                break

            c = self.data_new.rc.sscan(S1.gid_set('all'), c[0])


        self.log.info('Migrated [{0}] gids, [{1}] errors'.format(total, errors))
        self.log.info('Deleting "all" gid set...')
        self.data_new.rc.delete(S1.gid_set('all'))
        self.log.info('Renaming "all.new" --> "all"...')
        self.data_new.rc.rename(S1.gid_set('all.new'), S1.gid_set('all'))
        self.log.info('Deleting "poller:cursor.lock" ...')
        self.data_new.rc.delete('poller:cursor.lock')
        self.log.info('Deleting "poller:cursor" ...')
        self.data_new.rc.delete('poller:cursor')
        """
        self.log.info('All done!')

    def migrate_gid(self, gid):
        self.log.info('Migrating [{0}]...'.format(gid))
        try:
            pass
            #last_poll = self.data_new.cache.get_poll_stamp(gid)
            #self.data_new.rc.zadd(S1.gid_set('all.new'), gid, last_poll)
        except Exception as e:
            self.log.error('Error migrating [{0}], {1}'.format(gid, traceback.format_exc()))

        return 0