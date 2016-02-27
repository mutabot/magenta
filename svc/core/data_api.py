import traceback
from core.filter import FilterData
from core.schema import S1


class DataApi(object):

    @staticmethod
    def forget_destination(data, log, gid, destination, user):
        if destination not in data.provider:
            log.exception('ERROR: Unknown destination [{0}]'.format(destination))
            return False

        # get sources for this master gid
        sources = set(data.get_gid_sources(gid).keys())
        # get sources for this destination account
        source_gid_set = set(data.get_bindings(destination, user))
        # sources to unlink
        sources_unlink = sources.intersection(source_gid_set)
        # unlink each source
        for src_gid in sources_unlink:
            data.remove_binding(src_gid, destination, user, clean=True)

        # remove account for this gid
        log.info('Forgetting provider account: [{0}] <-> [{1}:{2}]'.format(gid, destination, user))
        data.unlink_provider_account(gid, destination, user)
        source_gid_set = set(data.get_bindings(destination, user))
        if not source_gid_set:
            log.warning('No sources remain for [{0}:{1}], cleaning...'.format(destination, user))
            data.provider[destination].delete_user(user)

        return True

    @staticmethod
    def sync_settings(data, log, gid, source_link, target_link_list, include):
        """
        Synchronizes settings from source to all target links
        @param data: MR data object
        @param log: logger
        @param gid: master gid
        @param source_link: source link tuple (src,src_id,tgt,tgt_id)
        @param target_link_list: list of link tuples
        @param include: list, settings to be synchronized
        @return:
        """
        log.info('Syncing settings for [{0}] from {1}'.format(gid, source_link))
        try:
            for target_link in target_link_list:
                log.info("Copying filter: {0} --> {1}".format(source_link, target_link))

                if 'keyword' in include or 'tagline' in include:
                    src_filter_data = data.filter.get_filter(source_link[2], source_link[1], source_link[3])
                    tgt_filter_data = data.filter.get_filter(target_link[2], target_link[1], target_link[3])
                    filter_data = FilterData.merge_filter_data(src_filter_data, tgt_filter_data, set(include))
                    tgt_filter_data.update(filter_data)
                    data.filter.set_filter(target_link[2], target_link[1], target_link[3], tgt_filter_data)
                if 'schedule' in include:
                    schedule = data.buffer.get_schedule(source_link[1], '{0}:{1}'.format(source_link[2], source_link[3]))
                    data.buffer.set_schedule(target_link[1], '{0}:{1}'.format(target_link[2], target_link[3]), schedule)
                if 'options' in include:
                    for p_name in S1.PROVIDER_PARAMS:
                        p_val = data.provider[source_link[2]].get_user_param(source_link[3], p_name)
                        if p_val:
                            data.provider[target_link[2]].set_user_param(target_link[3], p_name, p_val)

            return True
        except Exception as e:
            log.error('Syncing settings [{0}], {1}'.format(e, traceback.format_exc()))

        return False

    @staticmethod
    def clone_targets(data, log, gid, src_gid, tgt_gid):
        log.info('Copying targets [{0}] from [{1}] to [{2}]'.format(gid, src_gid, tgt_gid))
        try:
            destinations = data.get_destinations(src_gid)
            for destination in destinations:
                users = data.get_destination_users(src_gid, destination)
                for user in users:
                    try:
                        log.info("Binding: {0} --> {1}:{2}".format(tgt_gid, destination, user))
                        data.bind_user(gid, tgt_gid, destination, user)
                        log.info("Copying filter: {0} --> {1}:{2}".format(tgt_gid, destination, user))
                        fltr = data.filter.get_filter(destination, src_gid, user)
                        data.filter.set_filter(destination, tgt_gid, user, fltr)
                    except Exception as e:
                        log.error('Error binding [{0}], {1}, {2}'.format(src_gid, e, traceback.format_exc()))

        except Exception as e:
            log.error('Error transforming [{0}], {1}, {2}'.format(src_gid, e, traceback.format_exc()))