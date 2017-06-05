import json
from logging import Logger
import core
from core.schema import S1


class DataCopy:
    def __init__(self, log, data, data_d=None):
        """
        @type log: Logger
        @type data: core.Data
        @type data_d: core.Data
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
        c = self.data.rc.hscan(S1.destination_key_fmt('children'))
        while len(c) > 1 and c[1]:
            total += len(c[1])
            for gid in c[1]:
                self.dump_gid(gid)

            # check if the next cursor is zero
            if c[0] == '0' or c[0] == 0:
                break

            # grab next set
            c = self.data.rc.hscan(S1.destination_key_fmt('children'), c[0])

        # sleep 10 sec before retry
        print('End of gid_set, total [{0}] GIDs.'.format(total))
        self.data_d.rc.delete(S1.register_set())
        print('Cleared register set.')


    def dump_gid(self, gid):
        print('Dumping user, GID: {0}'.format(gid))

        # get child bindings for this account
        children = set(self.data.get_destination_users(gid, 'children'))
        if not children or (len(children) == 1 and gid in children):
            if not self.data.rc.exists(S1.cache_key(gid)):
                print('****** SELF CHILD + NO CACHE, SKIPPED, GID: {0}'.format(gid))
                return

        # just to be safe
        children.add(gid)
        for child in children:
            self.dump_source(gid, child)

    def copy_hash(self, key):
        print('Copying {0}...'.format(key))
        self.data_d.rc.delete(key)
        d = self.data.rc.hgetall(key)
        for k, v in d.iteritems():
            self.data_d.rc.hset(key, k, v)

    def copy_set(self, key):
        print('Copying {0}...'.format(key))
        self.data_d.rc.delete(key)
        c = self.data.rc.sscan(key)
        while len(c) > 1 and c[1]:
            for record in c[1]:
                self.data_d.rc.sadd(key, record)

            # check if the next cursor is zero
            if c[0] == '0' or c[0] == 0:
                break

            # grab next set
            c = self.data.rc.sscan(key, c[0])

    def copy_zset(self, key):
        print('Copying {0}...'.format(key))
        self.data_d.rc.delete(key)
        c = self.data.rc.zscan(key)
        while len(c) > 1 and c[1]:
            for record in c[1]:
                self.data_d.rc.zadd(key, *record)

            # check if the next cursor is zero
            if c[0] == '0' or c[0] == 0:
                break

            # grab next set
            c = self.data.rc.zscan(key, c[0])

    def dump_source(self, master_gid, gid):
        print('Copying source [{0}:{1}]...'.format(master_gid, gid))

        # add child gid to pollers first
        self.data_d.register_gid(gid)

        # add the gid from the list of child accounts
        print('Linking GID: [{0}]m <-- [{1}]s'.format(master_gid, gid))
        self.data_d.add_linked_account(master_gid, gid)

        destinations = self.data.get_destinations(gid)
        self.log.debug('{"dest": [')
        c = 0
        for destination in destinations:
            users = self.data.get_destination_users(gid, destination)
            for user in users:
                if c != 0:
                    self.log.debug(',')
                # dump destination
                self.dump_destination(master_gid, gid, destination, user)
                c += 1
        self.log.debug('],')

        # dump gid data keys
        self.log.debug('"keys": [')
        self.log.debug('"{0},"'.format(S1.gid_key(gid)))
        self.log.debug('"{0},"'.format(S1.gid_log_key(gid)))
        self.log.debug('"{0},"'.format(S1.links_key(gid)))
        self.log.debug('"{0}"'.format(S1.cache_key(gid)))
        self.log.debug(']}')

        # copy keys
        self.copy_hash(S1.gid_key(gid))
        self.copy_zset(S1.gid_log_key(gid))
        self.copy_hash(S1.cache_key(gid))
        self.copy_set(S1.links_key(gid))

        # copy tokens for all linked destinations (will overwrite some data)
        links = self.data.get_linked_accounts(master_gid) or dict()
        for k in links:
            # copy token
            p = k.split(':')
            if not p[0] in self.data.provider:
                continue

            token = self.data.get_user_token(gid, p[0], p[1])
            self.data_d.set_user_token(gid, p[0], p[1], token)
            # copy user params
            for p_name in S1.PROVIDER_PARAMS:
                p_val = self.data.provider[p[0]].get_user_param(p[1], p_name)
                if p_val:
                    self.data_d.provider[p[0]].set_user_param(p[1], p_name, p_val)

    def dump_destination(self, master_gid, gid, destination, user):
        self.log.debug('{')
        self.log.debug('"dst":"{0}:{1}",'.format(destination, user))
        self.log.debug('"m":"{0}","s":"{1}",'.format(master_gid, gid))
        # get sources for this master gid
        sources = set(self.data.get_gid_sources(gid).keys())
        # get sources for this destination account
        source_gid_set = set(self.data.get_bindings(destination, user))
        # sources to unlink
        sources_unlink = sources.intersection(source_gid_set)

        self.log.debug('"src_all":{0},'.format(json.dumps(list(sources))))
        self.log.debug('"src_dest":{0},'.format(json.dumps(list(source_gid_set))))
        self.log.debug('"src_link":{0}'.format(json.dumps(list(sources_unlink))))

        # unlink each source
        for src_gid in sources_unlink:
            print('Binding: [{0}] --> [{1}:{2}]'.format(gid, destination, user))
            self.data_d.bind_user(master_gid, gid, destination, user)
            # destination update
            #up = self.data.get_destination_update(gid, destination, user)
            #self.data_d.set_destination_first_use(gid, destination, user, up)
            # copy first bound timestamp
            #use = self.data.get_destination_first_use(gid, destination, user)
            #self.data_d.set_destination_first_use(gid, destination, user, use)
            # timestamps
            #bound = self.data.get_destination_param(gid, destination, user, S1.bound_key())
            #self.data_d.set_destination_param(gid, destination, user, S1.bound_key(), bound)
            # filters
            filter_data = self.data.filter.get_filter(destination, gid, user)
            self.data_d.filter.set_filter(destination, gid, user, filter_data)
            # message map
            msg_id_map = self.data.filter.get_message_id_map(destination, user)
            self.data_d.filter.set_message_id_map(destination, user, msg_id_map)

        self.log.debug('}')
        # remove account for this gid

        # get destination accounts data (keys, avatar, etc.) for this link
        acc_dump = self.data.get_linked_account(gid, destination, user)
        if not acc_dump:
            print('WARNING: No data for [{0}] --> [{1}:{2}]'.format(gid, destination, user))
        else:
            print('Copying Data: [{0}] --> [{1}:{2}]'.format(gid, destination, user))
            self.data_d.link_provider_account(gid, destination, user, acc_dump)