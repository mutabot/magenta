import time
from logging import Logger
import traceback
from core.schema import S1

from providers.google_fetch import GoogleFetch, GoogleFetchRetry
from providers.google_rss import GoogleRSS
from core import Data
from providers.google_short import GoogleShorten


class GooglePollAgent(object):
    def __init__(self, logger, data, config_path):
        """
        @type logger: Logger
        @type data: Data
        """
        self.logger = logger
        self.data = data
        self.google_fetch = GoogleFetch(logger, config_path)
        self.shortener = GoogleShorten(logger, config_path)

    def validate_user_name(self, user_name):
        # retry 1 time
        for n in range(0, 1):
            try:
                person_doc = self.google_fetch.get_plus_user_info(user_name)
                if not person_doc or not 'id' in person_doc:
                    self.logger.error('Error: validate_user_name no result for {0}'.format(user_name))
                    return None

                # store account info if no info available
                gid_info = self.data.get_gid_info(person_doc['id'])
                # TODO: Update account info for existing account!
                if not gid_info:
                    self.logger.warning('New account info for {0}:{1}'.format(user_name, person_doc['id']))
                    self.data.set_gid_info(person_doc['id'], person_doc)

                # return GID
                return person_doc['id']

            except GoogleFetchRetry:
                self.logger.warning('RetryError in validate_user_name for {0}'.format(user_name))
                continue

            except Exception as e:
                msg = 'Exception while validate_user_name for {0}, [{1}], {2}'
                self.logger.error(msg.format(user_name, e, traceback.format_exc()))
                return None

    def poll(self, gid):
        """ requests list of activities for the GID
        @rtype : bool
        @return : True on success, False on system error
        """
        try:
            self.logger.info('Poll request for {0}...'.format(gid))

            # fetch data
            activities_doc = self.fetch(gid)
            if activities_doc:
                # process the dataset
                self.process_activities_doc(gid, activities_doc, False)
            else:
                self.logger.warning('Nothing to process for {0}'.format(gid))

            return True

        except GoogleFetchRetry:
            self.logger.warning('RetryError for {0}'.format(gid))

        except Exception as e:
            msg = 'Exception while fetching data for {0}, [{1}], {2}'
            self.logger.error(msg.format(gid, e, traceback.format_exc()))

        return False

    def fetch(self, gid):
        #fetch activities from google
        max_results = self.data.cache.get_gid_max_results(gid)
        activities_doc = self.google_fetch.get_activities(gid, max_results)
        # validate received data
        if not activities_doc:
            self.logger.warning('Nothing received for [{0}]'.format(gid))
            return None

        return activities_doc

    def process_activities_doc(self, gid, activities_doc, force=False):
        # validate received data
        updated = GoogleRSS.get_update_timestamp(activities_doc)
        if not updated:
            self.logger.warning('Received empty data set for [{0}]'.format(gid))
            return

        # set last successful poll timestamp
        # users with no posts in Google Plus feeds will not be able to connect
        # as FE monitors this timestamp before accepting new account link
        self.data.cache.set_poll_stamp(gid, time.time())

        # set cache-specific meta-data
        last_updated = self.data.get_destination_update(gid, 'cache', gid)
        self.logger.info('Received data for [{0}], updated [{1}], last_updated [{2}]'.format(gid, updated, last_updated))
        if updated < last_updated:
            # Incomplete data?
            self.logger.warning('Warning: Updated timestamp jumped to past!')
            return

        # check if new update is in
        last_etag = self.data.get_destination_param(gid, 'cache', gid, S1.etag_key())
        etag = GoogleRSS.get_item_etag(activities_doc)
        if not force and last_etag == etag:
            self.logger.debug('Same data for {0}, last_updated={1}'.format(gid, last_updated))
            return

        # save etag
        self.data.set_destination_param(gid, 'cache', gid, S1.etag_key(), etag)

        # set cache destination updated
        self.data.set_destination_update(gid, 'cache', gid, updated)

        # shorten reshares urls
        items = GoogleRSS.get_updated_since(activities_doc, last_updated)
        shorten = self.data.get_gid_shorten_urls(gid)
        urls = set([item for item in items if shorten or GoogleRSS.get_item_is_share(item) for item in GoogleRSS.get_long_urls(item)])
        for url in urls:
            u = self.data.cache.get_short_url(url)
            if not u:
                u = self.shortener.get_short_url(url)
                self.data.cache.cache_short_url(url, u)

        # store the dataset
        self.data.cache_activities_doc(gid, activities_doc)

        # notify publishers
        self.data.flush_updates(gid)

        # process stats data
        # new user ?
        if not last_updated:
            self.logger.warning('Building new user activity map for {0}'.format(gid))
            self._build_user_activity_map(gid, activities_doc)
            # fake an update now as user is likely online when this code is executed
            self.data.cache.incr_num_minute_updates(gid, time.time())
        elif last_updated < updated:
            # increment update count for this minute
            self.logger.debug('Updating user activity map for {0}, data updated={1}'.format(gid, updated))
            self._build_user_activity_map(gid, activities_doc, last_updated=last_updated)
        else:
            self.logger.debug('No activity map updates for {0}, data updated={1}'.format(gid, updated))

    def _build_user_activity_map(self, gid, activities_doc, last_updated=0):
        """
        Creates user daily activity map from activities doc
        @type activities_doc: dict
        """
        for item in activities_doc.get('items', []):
            updated = GoogleRSS.get_item_updated_stamp(item)
            if updated > last_updated:
                self.data.cache.incr_num_minute_updates(gid, updated)