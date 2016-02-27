import calendar
import logging
import re
import datetime
from types import UnicodeType

from dateutil.parser import parse


class GoogleRSS(object):

    @staticmethod
    def result(item, kind, url, title, full_image=''):
        re_br = re.compile(ur'\r\n|\n|\r')
        return {
            'type': kind,
            # truncate title to 127-1 chars (255 limit in FB divide by 2 for unicode???)
            'title': re_br.sub(u' ', u'{0}...'.format(title[:123]) if len(title) > 126 else title, re.UNICODE),
            'link': url,
            'fullImage': full_image,
            'embed': GoogleRSS.get_item_embed_url(item),
            'guid': item['id'],
            'pubDate': GoogleRSS.format_timestamp_rss(GoogleRSS.get_timestamp(item['updated'])),
            'likes': GoogleRSS.get_likes(item)
        }

    @staticmethod
    def get_item_id(item):
        return item['id']

    @staticmethod
    def get_self_url(item):
        return GoogleRSS.get_unicode_string(item['url'])

    @staticmethod
    def get_object_type(item):
        try:
            if 'attachments' in item['object']:
                if 'objectType' in item['object']['attachments'][0]:
                    # treat single thumbnail albums as images (WTF is this single thumbnail thing???)
                    if 'album' == item['object']['attachments'][0]['objectType']:
                        if 'thumbnails' in item['object']['attachments'][0] and len(item['object']['attachments'][0]['thumbnails']) <= 1:
                            return 'photo'

                    return item['object']['attachments'][0]['objectType']
                else:
                    return 'link'
            elif item['provider']['title'] == 'Events':
                return 'event'
            # there are posts w/out text/description, they can not be treated as text
            elif item['title']:
                return 'text'
        except:
            pass

        # default is 'link' -- a link to the post itself or link in the post
        return 'link'

    @staticmethod
    def get_item_url(item, link):
        if link and 'attachments' in item['object'] and 'url' in item['object']['attachments'][0]:
            url = GoogleRSS.get_unicode_string(item['object']['attachments'][0]['url'])
        elif 'url' in item['object']:
            # another Google bug: duplicate prefix in event urls
            url = re.sub(ur'https://plus.google.com/https://plus.google.com',
                         u'https://plus.google.com',
                         GoogleRSS.get_unicode_string(item['object']['url']),
                         count=1)
        else:
            url = GoogleRSS.get_unicode_string(item['url'])
        return url

    @staticmethod
    def get_item_embed_url(item):
        if 'attachments' in item['object'] and 'embed' in item['object']['attachments'][0]:
            return GoogleRSS.get_unicode_string(item['object']['attachments'][0]['embed']['url'])
        return None

    @staticmethod
    def get_likes(item):
        result = 0
        try:
            result += int(item['object']['replies']['totalItems'])
            result += int(item['object']['plusoners']['totalItems'])
            result += (2 * int(item['object']['resharers']['totalItems']))
        except:
            pass
        finally:
            return result

    @staticmethod
    def set_description_raw(item, description):
        item['object']['content'] = description

    @staticmethod
    def get_description_raw(item):
        # strip invalid chars from description (Google bug?)
        if 'content' in item['object'] and item['object']['content']:
            return re.sub(ur'[\u0000-\u0009\ufeff-\uffff]', u'', item['object']['content'])
        return u''

    @staticmethod
    def set_annotation_raw(item, annotation):
        item['annotation'] = annotation

    @staticmethod
    def get_annotation_raw(item):
        if 'annotation' in item:
            return item['annotation']
        else:
            return u''

    @staticmethod
    def description_keywords():
        return [u'{self_name}', u'{self_url}']

    @staticmethod
    def get_unicode_string(string):
        return unicode(string, 'utf-8', errors='ignore') if type(string) is not UnicodeType else string

    @staticmethod
    def get_description(item, fmt=None):
        """
        @type fmt: unicode
        """
        description = GoogleRSS.get_description_raw(item)

        if item['verb'] == 'share':
            fmt = u'{annotation}\r\n-\r\n{description}\r\n-- \r\n{self_name} ({self_url}) via {share_name} ({share_url})'
            annotation = GoogleRSS.get_annotation_raw(item)
            description = fmt.format(
                annotation=GoogleRSS.get_unicode_string(annotation),
                description=GoogleRSS.get_unicode_string(description),
                self_url=GoogleRSS.get_unicode_string(item['url']),
                self_name=GoogleRSS.get_unicode_string(item['actor']['displayName']),
                share_url=GoogleRSS.get_unicode_string(item['object']['url']),
                share_name=GoogleRSS.get_unicode_string(item['object']['actor']['displayName']))

        elif fmt:
            try:
                # prepend with a line break
                description = u''.join([
                    description,
                    u'\r\n',
                    fmt.format(
                        self_url=GoogleRSS.get_unicode_string(item['url']),
                        self_name=GoogleRSS.get_unicode_string(item['actor']['displayName'])
                    )
                ])
            except:
                # do nothing if formatting failed
                pass

        return description

    @staticmethod
    def get_tags(item):
        description = GoogleRSS.get_description_raw(item)
        annotation = GoogleRSS.get_annotation_raw(item)
        return re.findall(ur'#(\w+)', ' '.join((description, annotation)), re.UNICODE)

    @staticmethod
    def parse_full_image_url(url):
        re_img = re.compile('/((w\d+-h\d+|s0)(-[pd])?/)?([^/]+)$')
        return re_img.sub(r'/s0/\4', url)

    @staticmethod
    def get_full_image_url(item):
        if not 'attachments' in item['object']:
            return None

        url = None
        try:
            if 'fullImage' in item['object']['attachments'][0]:
                url = item['object']['attachments'][0]['fullImage']['url']
            elif 'image' in item['object']['attachments'][0]:
                url = item['object']['attachments'][0]['image']['url']
            elif 'thumbnails' in item['object']['attachments'][0] and item['object']['attachments'][0]['thumbnails']:
                url = item['object']['attachments'][0]['thumbnails'][0]['image']['url']
            else:
                return None

            # cater for Google's issue with not providing full-size image links
            if 'objectType' in item['object']['attachments'][0] and item['object']['attachments'][0]['objectType'] in ['photo', 'album']:
                return GoogleRSS.parse_full_image_url(url)
        except:
            pass

        return url

    @staticmethod
    def populate_image_ids(item, result):
        result['id'] = item['object']['attachments'][0]['id']
        re_album = re.compile('.*/photos/(?P<user_id>\d+)/albums/(?P<album_id>\d+)(/(?P<photo_id>\d+))?')
        m = re_album.match(item['object']['attachments'][0]['url'])
        if m:
            result['album_id'] = m.group('album_id')
            result['photo_id'] = m.group('photo_id')
            result['user_id'] = m.group('user_id')

    @staticmethod
    def process_photo(item):
        title = item['title']
        url = full_image = GoogleRSS.get_full_image_url(item)
        return GoogleRSS.result(item, 'photo', url, title, full_image=full_image)

    @staticmethod
    def process_text(item):
        title = item['title']
        url = GoogleRSS.get_item_url(item, False)
        return GoogleRSS.result(item, 'text', url, title)

    @staticmethod
    def process_link(item, object_type='link'):
        if 'attachments' in item['object'] and 'displayName' in item['object']['attachments'][0]:
            title = item['object']['attachments'][0]['displayName']
        else:
            title = item['title']

        url = GoogleRSS.get_item_url(item, True)
        full_image = GoogleRSS.get_full_image_url(item)
        return GoogleRSS.result(item, object_type, url, title, full_image=full_image)

    @staticmethod
    def process_album(item):
        title = item['title']
        url = GoogleRSS.get_item_url(item, True)
        full_image = GoogleRSS.get_full_image_url(item)
        if not url.startswith('https://plus.google.com'):
            url += 'https://plus.google.com'
        return GoogleRSS.result(item, 'album', url, title, full_image=full_image)

    @staticmethod
    def gen_items(activities_doc, option, cache):
        optionmap = {
            'text': ['text'],
            'photo': ['photo'],
            'links': ['text', 'link', 'album'],
            'links-': ['link', 'album'],
            'text-': ['text']
        }
        for item in activities_doc['items']:
            result = GoogleRSS.process_item(item)
            # shorten urls reshares, urls must be cached locally already, see google_poll.py
            if GoogleRSS.get_item_is_share(item):
                c = {url: cache.get_short_url(url) or url for url in GoogleRSS.get_long_urls(item)}
                GoogleRSS.remap_urls(item, c)

            result['description'] = GoogleRSS.get_description(item)

            if option:
                if option in optionmap.keys() and result['type'] in optionmap[option]:
                    yield result
            else:
                yield result

    @staticmethod
    def process_item(item):
        # format urls and etc.
        object_type = GoogleRSS.get_object_type(item)
        if object_type == 'photo':
            result = GoogleRSS.process_photo(item)
            GoogleRSS.populate_image_ids(item, result)
        elif object_type == 'album':
            result = GoogleRSS.process_album(item)
            GoogleRSS.populate_image_ids(item, result)
        elif object_type == 'video':
            result = GoogleRSS.process_link(item, object_type=object_type)
        elif object_type in ['link', 'article', 'audio', 'event']:
            result = GoogleRSS.process_link(item)
        #text only for catch-all
        else:
            result = GoogleRSS.process_text(item)

        return result

    @staticmethod
    def get_update_timestamp(activities_doc):
        if 'updated' in activities_doc:
            return GoogleRSS.get_timestamp(activities_doc['updated'])
        else:
            return 0

    @staticmethod
    def get_item_updated(item):
        if 'updated' in item:
            return item['updated']
        return ''

    @staticmethod
    def get_item_updated_stamp(item):
        if 'updated' in item:
            return GoogleRSS.get_timestamp(item['updated'])
        return 0

    @staticmethod
    def get_item_published(item):
        if 'published' in item:
            return item['published']
        return ''

    @staticmethod
    def get_item_published_stamp(item):
        if 'published' in item:
            return GoogleRSS.get_timestamp(item['published'])
        return ''

    @staticmethod
    def get_item_id(item):
        if 'id' in item:
            return item['id']
        return ''

    @staticmethod
    def get_item_etag(item):
        if 'etag' in item:
            return item['etag']
        return ''

    @staticmethod
    def get_item_is_share(item):
        return 'verb' in item and item['verb'] == 'share'

    @staticmethod
    def get_item_is_community(item):
        return 'access' in item and item['access']['description'] != 'Public'

    @staticmethod
    def get_updated_since(activities_doc, timestamp):
        items = [item for item in activities_doc.get('items', []) if 'updated' in item and GoogleRSS.get_timestamp(item['updated']) > timestamp]
        # sort by updated
        items.sort(key=lambda item: GoogleRSS.get_timestamp(item['published']))
        return items

    @staticmethod
    def get_timestamp(iso_str):
        return calendar.timegm(parse(iso_str).timetuple())

    @staticmethod
    def format_timestamp_rss(timestamp):
        try:
            return datetime.datetime.utcfromtimestamp(timestamp).strftime('%a, %d %b %Y %H:%M:%S -0000')
        except:
            return datetime.datetime.utcfromtimestamp(0).strftime('%a, %d %b %Y %H:%M:%S -0000')

    @staticmethod
    def _remap_url(cache, url):
        return cache[url] if url in cache else url

    @staticmethod
    def remap_urls(item, cache):
        """
        @type cache: dict
        """
        try:
            item['url'] = GoogleRSS._remap_url(cache, GoogleRSS.get_unicode_string(item['url']))
            item['object']['url'] = GoogleRSS._remap_url(cache, GoogleRSS.get_unicode_string(item['object']['url']))
        except:
            logging.error('Url shortening failed with exception')

    @staticmethod
    def get_long_urls(item):
        return [GoogleRSS.get_unicode_string(item['url']), GoogleRSS.get_unicode_string(item['object']['url'])]

    @staticmethod
    def get_user_name(user_info):
        if not user_info:
            return None
        elif 'displayName' in user_info:
            return user_info['displayName']
        elif 'name' in user_info:
            return user_info['name']
        return None