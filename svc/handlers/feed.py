import re
import time

import tornado
from tornado import gen
from tornado import web
from tornado.ioloop import IOLoop

from providers.google_rss import GoogleRSS
from utils import config


class FeedHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        pass

    def __init__(self, application, request, **kwargs):
        self.logger = application.logger
        self.data = application.data

        super(FeedHandler, self).__init__(application, request, **kwargs)

    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        self.set_header('Content-Type', 'application/rss+xml;charset=utf-8')
        gid = self.get_argument('gid')
        if not (gid and self.data.is_valid_gid(gid)):
            raise tornado.web.HTTPError(403, reason='Unregistered ID {0}. Subscribe at https://magentariver.com'.format(gid))

        filter_arg = self.get_argument('filter', '')
        self.logger.info('Request: {0},{1}'.format(gid, filter_arg))

        # check cache for miss/hit
        if not self.data.cache.is_cache(gid, filter_arg):
            # cache miss
            self.logger.warning('Cache miss for [{0}]'.format(gid))
            stamp = time.time()
            # re-register gid if valid
            if not self.data.is_valid_gid(gid):
                # do a simple string validation
                if re.search('[!-\*:-@\\\/]', gid):
                    self.logger.warning('Warning: Invalid characters in user ID for RSS {0}'.format(gid))
                    raise tornado.web.HTTPError(400, reason='Invalid characters in user ID {0}'.format(gid))

                # do a validation before registering
                # validate the GID
                self.data.begin_validate_gid(gid)
                valid_gid = None

                # wait for data update from Google
                for n in range(0, 5):
                    # wait for up to 10 seconds
                    yield gen.Task(IOLoop.instance().add_timeout, time.time() + 2)
                    valid_gid = self.data.get_validate_gid(gid)
                    if valid_gid:
                        break

                if not valid_gid or 'None' == valid_gid:
                    self.logger.warning('Warning: invalid GID for RSS {0}'.format(gid))
                    raise tornado.web.HTTPError(400, reason='Invalid user ID {0}'.format(gid))

            # now can re-register the gid
            self.data.register_gid(gid)

            #poll for an update
            self.logger.info('Waiting for update...')
            for n in range(0, 5):
                yield gen.Task(IOLoop.instance().add_timeout, time.time() + 2)
                if self.data.cache.is_poll_after(gid, stamp):
                    break

            if self.data.cache.is_poll_after(gid, stamp):
                self.logger.info('...update received')
            else:
                self.logger.warning('... Time out waiting for Google Plus API update')

        # read the cache anyway
        activities_doc = self.data.cache.get_activities(gid)

        # process activities if any
        if activities_doc:
            updated = self.data.cache.get_poll_stamp(gid)
            self.logger.info('Items received, update stamp: {0}'.format(time.strftime('%x %X %z', time.gmtime(updated))))
            self.process_activities(gid, filter_arg, activities_doc)
        else:
            self.logger.warning('Warning: no activities for {0}'.format(gid))
            raise tornado.web.HTTPError(400, reason='No data available for {0}'.format(gid))

    def process_activities(self, gid, option, activities_doc):
        items = GoogleRSS.gen_items(activities_doc, option, self.data.cache)
        self.render('feed.xml', version=config.version, gid=gid, pubDate=GoogleRSS.format_timestamp_rss(time.time()), items=items)
