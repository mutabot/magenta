import json
import re
import traceback
import urllib2
import time
from logging import Logger

from bs4 import BeautifulSoup
from tornado import gen

from core.model import RootAccount, Link, SocialAccount
from core.filter import FilterData
from core.schema import S1
from providers.google_rss import GoogleRSS
from core import DataDynamo
from providers.publisher_inerface import PublisherInterface
from utils import config
from providers.picasa import Picasa
from providers import PublisherContext

MSG_FAILED_TO_PARSE_ID_ = 'Failed to parse message_id [{0}]-->[{1}], {2}, skipping message...'
MSG_RETRYING_FAILED_ = 'Retrying previously failed message [{0}], retry {1}, message_id [{2}]...'
MSG_FAILED_ALREADY_ = 'Message failed previously [{0}]-/->[{1}], skipping...'
MSG_NEW_TOKEN_ = 'New token, retrying previously failed message [{0}], retry {1}, message_id [{2}]...'
MSG_NOW_IN_TAGS_ = '"now" in tags, schedule check skipped, post {0} to {1}:{2}'
MSG_SUCCESS_ = 'Success: {0} Google+ [{1}] --> [{2}:{3}] --> message ID [{4}]'
MSG_DEACTIVATED_ = 'Magenta River {0} publisher is deactivated'
MSG_UNLINK_ = 'Error count for [{0}]:[{1}] is {2}, unlinking accounts...'
MSG_FAILED_TO_ = 'Magenta River failed to publish to {0}'
MSG_ERR_COUNT_ = '[{0}] Incrementing error count for [{1}], new count={2}'
MSG_LAST_UPDATED_ = 'Warning: Source update timestamp jumped backward (deleted post?), GID[{0}], updated[{1}], last_updated[{2}]'


class PublishFailed(Exception):
    pass


# noinspection PyBroadException
class PublisherBase(PublisherInterface):
    def __init__(self, name, log, data, config_path, picasa=None):
        """
        @type config_path: str
        @type name: str
        @type data: DataDynamo
        @type log: Logger
        """
        self.name = name
        self.log = log
        self.data = data

        # picasa data puller
        self.picasa = picasa or Picasa(log, config_path)
        # used to retrieve full-size image url from picasas data
        self.re_img = re.compile('(/[^/]+\.jpg)$')

    def get_user_param(self, user, param):
        """

        @param param: name of the parameter
        @type user: SocialAccount
        """
        return user.options[param] if param in user.options else None

    def get_token(self, target):
        """

        @type target: SocialAccount
        """
        token_str = target.credentials['token'] if 'token' in target.credentials else None
        if not token_str:
            return None
        token = json.loads(token_str)
        return token

    def send_email_notification(self, gl_user, pid, subject, template_name):
        """

        @param template_name:
        @param subject:
        @param pid: target user id
        @type gl_user: RootAccount
        """
        args = {
            'subject': subject,
            'params': {
                'gid': gl_user.Key,
                'provider': self.name.title(),
                'user': pid
            }
        }
        args_json = json.dumps(args)
        parent = gl_user.account.pid
        self.data.pubsub.broadcast_command_now(S1.MAILER_CHANNEL_NAME, 'mail.send', parent, template_name, args_json)

    def on_publish_error(self, gl_user, link):
        """

        @type link: Link
        @type gl_user: RootAccount
        """
        # increment error count
        source = DataDynamo.get_account(gl_user, link.source)
        target = DataDynamo.get_account(gl_user, link.target)
        if not target:
            self.log.error('Fatal: target account not found for {0}'.format(link.target))
            return False

        target.errors += 1
        if target.errors == 2:
            self.log.warning(MSG_ERR_COUNT_.format(self.name, link.Key, target.errors))

            # get the name and email address of the user
            # only parents will get notified
            self.send_email_notification(gl_user, link, MSG_FAILED_TO_.format(self.name.title()), 'publisher_error')

        elif target.errors >= config.DEFAULT_MAX_ERROR_COUNT:
            msg = MSG_UNLINK_.format(self.name, link.source, target.errors)
            self.data.add_log(gl_user, source.pid, msg)
            self.log.warning(msg)

            # notify user before unbinding, we need that binding to get parents for this gid-->provider:user
            self.send_email_notification(gl_user, source.pid, MSG_DEACTIVATED_.format(self.name.title()),
                                         'account_unlinked')

            # unbind from source
            self.data.remove_binding(gl_user, link)

            # do not attempt to publish for this user
            return False

        # can still re-try
        return True

    @gen.coroutine
    def publish(self, context):
        """

        @type context: PublisherContext
        """

        gl_user = context.root
        source = context.source

        # 1. extract activities from cache
        activities_doc = yield self.data.get_activities(source.Key)
        if not activities_doc:
            self.log.warning('Warning: No activities for Google Plus user [{0}]'.format(source.Key))
            return

        # 2. get gid update timestamp
        updated = GoogleRSS.get_update_timestamp(activities_doc)
        if not updated:
            self.log.warning(
                'Warning: Noting to publish, no updates in feed for Google Plus user [{0}]'.format(source.Key))
            self.log.debug(json.dumps(activities_doc))
            return

        # 3. see if have any new items, that has been updated in last 7200 hours
        review_depth = int(time.time()) - 7200 * 3600
        items = GoogleRSS.get_updated_since(activities_doc, review_depth)

        if not items:
            self.log.warning('Noting to publish, no items in feed for {0}->{1}'.format(source.Key, self.name))
            return
        else:
            self.log.info('{0} new items in feed for {1}'.format(len(items), source.Key))

        # 4. get destination user accounts for this gid
        links = self.data.get_destination_users(gl_user, source, self.name)
        self.log.info('[{0}] Publishing updates [{1}] --> [{2}] users'.format(self.name, source.Key, len(links)))

        # for each link bound to this source
        for link in links:

            try:
                # validate the whole document
                if self.is_skip_document(source, link, updated):
                    self.log.info('Document skipped for gid={0}, user={1}'.format(source.Key, link.target))
                    continue

                # setup up the context
                context.link = link
                context.source = DataDynamo.get_account(gl_user, link.source)
                context.target = DataDynamo.get_account(gl_user, link.target)

                # publish updates for this user
                self.publish_for_user(context, items)

            except:
                self.log.error('[{0}] Exception in provider_publish(): {1}'.format(self.name, traceback.format_exc()))

    def verify_publish_result(self, context, message_id_map, message_id, p_item):
        """

        @param p_item: prepared items adhoc dict
        @param message_id: id of the resulting message
        @param message_id_map: map of message ids
        @type context: PublisherContext
        """
        gl_user = context.root
        user = context.target
        source = context.source

        if message_id:
            # reset error count on success
            user.options[S1.error_count_key()] = 0

            pub_up = 'Publish' if not p_item['message_id'] else 'Update'
            log_message = MSG_SUCCESS_.format(pub_up, source.Key, self.name, user.Key, message_id)
            self.log.warning(log_message.format(source.Key, self.name, user.Key))
            self.data.add_log(gl_user, source.pid, log_message.format(source.Key, self.name, user.Key))
            user.last_publish = time.time()

        else:
            log_message = 'Failed to publish Google+ [{0}] --> [{1}:{2}]'
            self.log.warning(log_message.format(source.Key, self.name, user.Key))
            self.data.add_log(gl_user, source.pid, log_message.format(source.Key, self.name, user.Key))

            # increment error counter
            if not self.on_publish_error(context.root, context.link):
                # return immediately if final re-try
                return False

            # mark message as erroneous to avoid re-publish attempts
            message_id = 'error:{0}:{1}'.format(p_item['error_count'] + 1, str(self.get_token(user)))

        # store new or updated message_id in the map
        message_id_map[p_item['item_id']] = {
            'message': message_id,
            'updated': p_item['item_updated']
        }

        return True

    def publish_prepared(self, context, p_item, message_id_map, token):
        """
        Publishes the prepared item to a destination channel
        @type context: PublisherContext
        @param p_item: prepared item
        @param message_id_map: resulting messages id map
        @param token: destination access token
        """
        gl_user = context.root
        target = context.target
        message_id = None
        try:
            # publish to destination
            msg = 'Publishing --> [{0}:{1}], updated [{2}], type [{3}], id [{4}]'
            self.log.info(
                msg.format(self.name, target.Key, p_item['feed']['pubDate'], p_item['feed']['type'], p_item['item_id']))

            # actual publish
            result = self.provider_publish(target, token, p_item['feed'], message_id=p_item['message_id'],
                                           user_options=p_item['params'])
            self.log.debug('[{0}] Publish result [{1}]'.format(self.name, result))

            # check result
            message_id = self.process_result(p_item['message_id'], result, target, self.user_log, context)

        except:
            msg = '[{0}] Exception while publishing item, gid={1}, user={2}, item_id={3}, trace:{4}'
            self.log.exception(msg.format(self.name, gl_user.Key, target.Key, p_item['item_id'], traceback.format_exc()))

        # set destination update timestamp
        target.last_publish = p_item['item_updated']
        self.log.debug('Set destination update: {0}:{1}:{2}'.format(self.name, target.Key, p_item['item_updated']))

        # message id is an ultimate indication of success
        self.verify_publish_result(context, message_id_map, message_id, p_item)

    def user_log(self, context, message):
        """

        @type message: str
        @type context: PublisherContext
        """
        self.data.add_log(context.root, context.source.pid, message)

    def publish_for_user(self, context, items):
        """
        Publishes items for given destination user
        @type context: PublisherContext
        @param items: items to publish
        """
        gl_user = context.root
        link = context.link
        self.log.info('[{0}] Publishing updates [{1}]-->[{2}]'.format(self.name, link.source, link.target))

        source = context.source
        target = context.target

        if not source:
            self.log.error('No source account for link {0}:{1}:{2}'.format(gl_user.Key, link.source, link.target))
            return
        elif not target:
            self.log.error('No target account for link {0}:{1}:{2}'.format(gl_user.Key, link.source, link.target))
            return

        # retrieve access token for target account
        token = self.get_token(target)
        if not token:
            self.log.error('[{0}] No access token for [{1}], post failed'.format(self.name, target.Key))
            # increment error counter
            self.on_publish_error(gl_user, link)
            return

        # prepare items for publish
        prepared = self.get_next_prepared(context, items, target.message_map)

        # publishing one item at a time
        # rest of the items will be scheduled in 1 minute
        if not prepared:
            self.log.info('All items filtered out, publish complete')
            return

        # check for time-space
        last_publish = target.last_publish

        # minimum time-space is required to stop spamming activity
        time_space_min_ = prepared['params']['time_space_min'] or config.DEFAULT_MIN_TIME_SPACE
        if last_publish and time_space_min_:
            time_space_s = 60.0 * int(time_space_min_)
            wait_s = int(time_space_s - (time.time() - float(last_publish)))
            if wait_s > 0:
                self.log.info('T-space of {0}s for {1}'.format(wait_s, source.Key))
                self.data.add_log(gl_user, source.pid,
                                  'Next publish to {0}:{1} in {2:.1f}min.'.format(self.name, target.Key, wait_s / 60.0))
                self.data.buffer.buffer_in_s(source.pid, self.name, wait_s)
                return

        if prepared and 'item_id' in prepared and prepared['item_id'] != items[-1]['id']:
            self.log.info('Buffering remaining items')
            self.data.buffer.buffer_in_s(source.pid, self.name, 60.0)

        self.log.info('Publishing 1 out of {0} items'.format(len(items)))

        # publish prepared item
        self.publish_prepared(context, prepared, target.message_map, token)

        # set dirty flags
        gl_user.dirty.add('accounts')
        gl_user.dirty.add('links')

        self.log.info('Publish complete')

    def get_next_prepared(self, context, items, message_id_map):
        """
        Prepares next content block to be published
        @type context: PublisherContext
        @param message_id_map: previously published content reference (to avoid duplicates)
        @param items: content to be published
        """

        gl_user = context.root
        link = context.link
        source_account = context.source
        target_account = context.target
        for item in items:

            item_id = GoogleRSS.get_item_id(item)
            item_updated_stamp = GoogleRSS.get_item_updated_stamp(item)
            item_url = GoogleRSS.get_long_urls(item)[0]
            item_url = item_url.encode('utf-8', errors='ignore') if item_url else '***'

            # will skip messaged dated pre-enroll
            item_published = GoogleRSS.get_item_published_stamp(item)
            # Set below to False for DEBUG
            if item_published < link.first_publish:
                # skip items older than first use of the service to
                # avoid duplicates of items we or other service may have exported earlier
                self.data.add_log(gl_user, source_account.pid,
                                  'Pre-link post skipped {0}, [{1}]-->[{2}]'
                                  .format(item_url, source_account.Key, target_account.Key))
                continue

            # was the item exported to provider previously?
            msg_error_count = 0
            message_id = message_id_map[item_id]['message'] if item_id in message_id_map.keys() else None
            if message_id:
                if message_id.startswith('error:'):
                    msg_error_count = self.check_message_id(target_account, item_id, message_id)
                    if msg_error_count is None:
                        self.data.add_log(gl_user, source_account.pid,
                                          'Skipped {0}, {1}:{2}'
                                          .format(item_url, self.name, target_account.Key))
                        continue
                    # reset message id to allow downstream code process this as new message
                    message_id = None

                elif not (message_id_map[item_id]['updated'] < item_updated_stamp):
                    self.log.info('Message already processed [{0}]-->[{1}], skipping...'.format(item_id, message_id))
                    continue

                self.log.info(
                    'Message edit detected [{0}]-->[{1}], editing in destination...'.format(item_id, message_id))

            # filter out community posts
            if GoogleRSS.get_item_is_community(item) and 'in_cty' not in target_account.options:
                self.data.add_log(gl_user, source_account.pid, 'Ignored community post {0}'.format(item_url))
                continue

            # prepare description and annotation *before filters!*
            self._format_message(item)

            # get tags, for schedule control or eny other post control
            tags = GoogleRSS.get_tags(item)

            # check if user has schedule
            if 'now' in tags:
                self.data.add_log(gl_user, source_account.pid, MSG_NOW_IN_TAGS_.format(item_url, self.name, target_account.Key))
            elif self.data.buffer.check_schedule(gl_user, self.name, target_account.pid, link.schedule):
                self.data.add_log(gl_user, source_account.pid, 'Post buffered {0}, {1}:{2}'.format(item_url, self.name, target_account.Key))
                continue

            # apply item filter for new items only, previously exported items will be updated regardless of filter
            f_ltr = link.filters
            if not message_id and self.is_filter_rejected(f_ltr, item):
                self.data.add_log(gl_user, source_account.pid, 'Filter reject {0}, {1}:{2}'.format(item_url, self.name, target_account.Key))
                continue

            # formatting description
            tagline = f_ltr[FilterData.tagline_kind] if FilterData.tagline_kind in f_ltr else None

            # build prepared item bag
            prepared = self.create_prepared_item(source_account, target_account, item, tagline)
            prepared['feed']['tags'] = tags
            prepared['item_id'] = item_id
            prepared['item_updated'] = item_updated_stamp
            prepared['message_id'] = message_id
            prepared['error_count'] = msg_error_count
            self.log.info('One item prepared')
            return prepared

        return None

    def check_message_id(self, target, item_id, message_id):
        """
        extract error count from message_id
        @param target:
        @param item_id:
        @param message_id:
        @return: None on error or message_id does not contain error count. Error count in other cases.
        """
        try:

            err_options = message_id.split(':', 2)
            msg_error_count = int(err_options[1])

            # check for token update
            if len(err_options) > 1 and err_options[2] != str(self.get_token(target)):
                self.log.warning(MSG_NEW_TOKEN_.format(item_id, msg_error_count, message_id))
                return 0
            # check update timestamp for message edit
            elif msg_error_count > 1:
                self.log.warning(MSG_FAILED_ALREADY_.format(item_id, message_id))
                return None

            elif msg_error_count >= 0:
                self.log.warning(MSG_RETRYING_FAILED_.format(item_id, msg_error_count, message_id))
                return msg_error_count

        except:
            self.log.error(MSG_FAILED_TO_PARSE_ID_.format(item_id, message_id, traceback.format_exc()))

        return None

    def create_prepared_item(self, source, target, item, tagline):
        """

        @param tagline: tagline template
        @param item: item data
        @type target: SocialAccount
        @type source: SocialAccount
        """
        # shorten urls for tagline and reshares, urls must be cached locally already, see google_poll.py
        if GoogleRSS.get_item_is_share(item) or S1.cache_shorten_urls() in source.options:
            cache = {url: self.data.cache.get_short_url(url) or url for url in GoogleRSS.get_long_urls(item)}
            GoogleRSS.remap_urls(item, cache)

        # get URLs for photo/album/text/etc
        feed = GoogleRSS.process_item(item)

        # format description, let derived classes to amend format for line breaks, etc
        feed['description'] = self.format_message(GoogleRSS.get_description(item, tagline))

        # get self url (Twitter uses it)
        feed['self_url'] = GoogleRSS.get_self_url(item)

        # additional parameters will go there
        params = {
            'expand_albums': 'expand_albums' in target.options,
            # fallback to link post if album_links flag is set
            'album_links': target.options['album_links'] if 'album_links' in target.options else None,
            'time_space_min': target.options['time_space_min'] if 'time_space_min'in target.options else None,
        }

        # build local item structure
        return {
            'feed': feed,
            'params': params
        }

    def provider_publish(self, target, token, feed, message_id=None, user_options=None):
        """

        @type token: str
        @type target: SocialAccount
        """
        # updated photos must be deleted first
        # page posts can not be edited and must be deleted first
        if message_id and self.is_delete_message(target, feed):
            self.log.info('[{0}] Deleting story for [{1}], message_id [{2}]...'
                          .format(self.name, target.Key, message_id))
            if not self.delete_message(target, message_id, token):
                self.log.warning('Warning: failed to delete story for [{0}], message_id [{1}]'
                                 .format(target.Key, message_id))
                # keep going and try to post new message
            # clear message id
            message_id = None

        message = feed['description']

        self.log.debug('[{0}] Publishing, user_options: [{1}]...'.format(self.name, user_options))

        # try to process full-fledged and fallback to simple link post in case of failure
        result = None
        try:
            # is it text?
            if 'text' == feed['type']:
                result = self.publish_text(target, feed, message, message_id, token)

            # video ?
            elif 'video' == feed['type']:
                result = self.publish_video(target, feed, message, message_id, token)

            # is it image?
            elif feed['type'] in ['album', 'photo']:
                if not ('user_id' and 'album_id' in feed):
                    self.log.warning('[{0}] ERROR: Unable to fetch Picasa album, no album info in feed'
                                     .format(self.name))

                else:
                    album = self.picasa.get_album(feed['user_id'], feed['album_id'])
                    if not album:
                        self.log.warning('[{0}] ERROR: Unable to fetch Picasa album'.format(self.name))

                    elif 'photo' == feed['type']:

                        # twitter does not support buzz expansion -- post as single image
                        if not self.is_expand_buzz() or ('buzz' in album and album['buzz']):
                            # "buzz" photo publish one photo to "timeline"
                            result = self.publish_photo(target, feed, message, message_id, token)
                        else:
                            # not a "buzz" photo -- add to photo album
                            # for posts that are single photos we do not want any other images to be uploaded
                            # the image set is faked
                            album['images'] = [
                                {
                                    # 'Tue Oct 11 22:33:19 2603'
                                    'updated': 19999999999.0,
                                    'url': feed['fullImage'],
                                    'alt_url': feed['link'],
                                    'description': feed['description']
                                }
                            ]
                            # post prepared album
                            result = self._publish_album(album, target, feed, message, message_id, token)

                    # check for album_links settings and use link publishing if not set
                    # only image albums are posted as series of images
                    elif 'album' == feed['type'] and not user_options['album_links'] and album['media_types'] == {'image'}:

                        if 'buzz' in album and album['buzz'] and self.is_expand_buzz():
                            # buzz album -- publish each photo separately, specific providers can refuse to expand buzz
                            result = self._publish_buzz_album(album, target, feed, message, message_id, token)
                        else:
                            # not a buzz album -- replicate album in destination
                            result = self._publish_album(album, target, feed, message, message_id, token)

        except Exception as e:
            self.log.warning('Exception in provider_publish: {0}'.format(e))

        # fallback to link post in case of link post or failure
        if not result:
            # check and format links
            self.check_link(feed)

            # publish
            return self.publish_link(target, feed, message, message_id, token)
        return result

    @staticmethod
    def _strip_html(message):
        # convert <br>s to self-closing <br />
        message = re.sub(ur'<br>', u'<br />', message)
        soup = BeautifulSoup(message, "html.parser")
        for br in soup.find_all(u'br'):
            if br.next and br.next.name == u'br':
                br.replace_with(u'\n ')
            else:
                br.replace_with(u'\n')

        result = soup.get_text()
        # prepare duplicate line breaks
        # return re.sub(ur'\n(?=\n)', u'\n ', result)
        return result

    @staticmethod
    def _format_message(item):
        message = GoogleRSS.get_description_raw(item)
        if message:
            message = PublisherBase._strip_html(message)
            GoogleRSS.set_description_raw(item, message)

        annotation = GoogleRSS.get_annotation_raw(item)
        if annotation:
            annotation = PublisherBase._strip_html(annotation)
            GoogleRSS.set_annotation_raw(item, annotation)

    def is_filter_rejected(self, f_ltr, item):
        """
        Returns True if item did not pass user filters
        empty filter = no filter!
        @param item:
        @param f_ltr:
        @rtype : bool
        """
        keyword_str = f_ltr[FilterData.keyword_kind] if FilterData.keyword_kind in f_ltr else None
        strip = f_ltr[FilterData.strip_kind] if FilterData.strip_kind in f_ltr else None
        if keyword_str and self._is_keyword_rejected(keyword_str, item, strip=bool(strip)):
            return True

        likes_str = f_ltr[FilterData.likes_kind] if FilterData.likes_kind in f_ltr else None
        if likes_str and self._is_likes_rejected(likes_str, GoogleRSS.get_likes(item)):
            return True

        return False

    @staticmethod
    def _is_keyword_rejected(keyword_str, item, strip=False):
        """
        empty filter = no filter
        @type strip: bool
        @type item: object
        @type keyword_str: unicode
        """
        keywords_all = keyword_str.split(u',')
        # separate keywords by type
        keywords = {k[1:] if k.startswith(u'-') else k: k.startswith(u'-') for k in keywords_all}

        regex = u'(' + u'|'.join(re.escape(k) for k in keywords) + u')'

        # filter on annotation only if re-shared content
        annotation = GoogleRSS.get_annotation_raw(item)
        if annotation:
            return PublisherBase._is_apply_kw_filter(annotation, keywords, regex, strip,
                                                     lambda text: GoogleRSS.set_annotation_raw(item, text))

        description = GoogleRSS.get_description_raw(item)
        if description:
            return PublisherBase._is_apply_kw_filter(description, keywords, regex, strip,
                                                     lambda text: GoogleRSS.set_description_raw(item, text))

        return True

    @staticmethod
    def _is_apply_kw_filter(text, keywords, regex, strip, strip_lambda):
        s = re.search(regex, text)
        if s and s.group() in keywords:
            # negative k-word reject?
            if keywords[s.group()]:
                return True
            # now check is strip is enabled
            if strip:
                d, n = re.subn(regex, u'', text)
                strip_lambda(d)
            return False
        return False in keywords.values()

    @staticmethod
    def _is_likes_rejected(likes_str, likes):
        # empty filter = no filter
        try:
            return likes < int(likes_str)
        except:
            return False

    def is_skip_document(self, source, link, updated):
        """

        @param updated: current document update timestamp
        @type link: Link
        @type source: SocialAccount
        """
        # get last publish stamp (property of destination and user)
        last_updated = link.updated_stamp
        if updated < last_updated:
            msg = MSG_LAST_UPDATED_.format(source.Key, updated, last_updated)
            # self.data.add_log(gid, msg)
            self.log.warning(msg)
            # self.log.debug(json.dumps(activities_doc))
            return True

        return False

    def _publish_album(self, album, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        # will skip images older than last update timestamp
        last_updated = user.last_publish

        if self.get_user_param(user, 'album_ignore_stamp'):
            # blindly take the whole album
            self.log.warning('[{0}] Warning: album_ignore_stamp is True!'.format(self.name))
            a = album['images']
        else:
            # clean old images
            a = [i for i in album['images'] if i['updated'] > last_updated]

        self.log.debug('[{0}] Publishing to album, last_updated [{1}]'.format(self.name, last_updated))
        for i in a:
            self.log.debug('[{0}] Ready to publish: [{1}]'.format(self.name, i))

        # reassign cleaned image list
        album['images'] = a

        # copy tags to album
        album['tags'] = feed['tags']

        # assign tags for each image
        for image in album['images']:
            image['tags'] = re.findall(ur'#(\w+)', image['description'], re.UNICODE)

        # return album creation result
        return self.publish_album(user, album, feed, message, message_id, token)

    def _publish_buzz_album(self, album, user, feed, message, message_id, token):
        """

        @type user: SocialAccount
        """
        # will skip images older than last update timestamp
        last_updated = user.last_publish

        # clean old images
        a = [i for i in album['images'] if i['updated'] > last_updated]

        b = sorted(a, key=lambda x: x['updated'], reverse=True)
        if not b and message_id:
            # post edited but no photos updated ?
            # "publish" as image -- this will update image description
            return self.publish_photo(user, feed, message, message_id, token)

        elif b:
            # append last image description with message
            b[-1]['description'] = message + '\r\n\r\n' + b[-1]['description']
            self.log.debug('[{0}] Publishing buzz album, last_updated [{1}]'.format(self.name, last_updated))
            result = None
            # publish as single photos
            for i in b:
                self.log.debug('[{0}] Ready to publish: [{1}]'.format(self.name, i))
                feed['fullImage'] = i['url']
                result = self.publish_photo(user, feed, i['description'], None, token)

            # return last result, it will be associated with this post ID
            return result

        # publish as link if all failed
        self.log.warning('[{0}] Warning: Failed to publish buzz album'.format(self.name))
        return None

    def _download_image(self, url, max_size_mb=20):

        try:
            u = urllib2.urlopen(url)
            # get the file size
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            if file_size > (max_size_mb * 1048576):
                self.log.error('WARNING: [{0}] file too big for {0} {1}'.format(self.name, url))
                return None, None

            return u, file_size

        except Exception as e:
            self.log.error('ERROR: [{name}] exception when downloading {0}, {1}'.format(url, e, name=self.name))

        return None, None

    def publish_video(self, user, feed, message, message_id, token):
        return None

    def format_message(self, message):
        return message

    @staticmethod
    def check_link(feed):
        """
        Checks and corrects the link if required
        @param feed: feed dict. Must contain 'link', and optionally 'embed'
        @return: True if link was corrected
        """
        # see if this is youtube link
        if feed['link'].count('youtube.com') and 'embed' in feed and feed['embed']:
            y = re.findall('youtube\.com/embed/(.+)', feed['embed'])
            if y:
                # format correct youtube link
                feed['link'] = 'http://youtu.be/{0}'.format(y[0])
                return True

        return False
