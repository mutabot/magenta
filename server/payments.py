import os
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor

import tornado
from tornado import httpserver, web, ioloop, log

from core import data, payments
from handlers import api
import utils


class Application(tornado.web.Application):
    @staticmethod
    def run():
        parser = argparse.ArgumentParser(prog='G+RSS')
        parser.add_argument('--port', required=True, type=int)
        parser.add_argument('--config_path', required=True)
        parser.add_argument('--debug', default=False, type=bool)
        args = parser.parse_args()

        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        logger = logging.getLogger(__name__)
        logger.level = logging.DEBUG

        # create application
        # configure the App
        cfg = utils.config.load_config(args.config_path, 'server_config.json')
        application = Application(args, logger, cfg)

        # load plan limits
        cfg = utils.config.load_config(args.config_path, 'limits.json')
        application.settings.update({'limits': cfg})

        #apply log config and launch
        tornado.log.access_log.level = logging.INFO
        tornado.log.app_log.level = logging.INFO
        tornado.log.gen_log.level = logging.INFO
        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(args.port)

        logger.info('Starting server v{0}, port={1}'.format(utils.config.version, args.port))
        #run
        tornado.ioloop.IOLoop.instance().start()

    def __init__(self, args, logger, cfg):
        self.pool = ThreadPoolExecutor(cfg['max_threads'])
        self.logger = logger
        self.data = data.Data(logger=logger, redis_host=cfg['master_redis_host'], redis_port=cfg['master_redis_port'], redis_db=cfg['master_redis_db'])
        self.payments = payments.Payments(logger=logger, data=self.data, redis_host=cfg['payments_redis_host'], redis_port=cfg['payments_redis_port'], redis_db=cfg['payments_redis_db'])
        self.payments.initialize(args.config_path)

        handlers = [
            # Payments
            (r'/api/v1/order/(.*)', api.payments.OrderApiHandler),
        ]

        settings = dict(
            cookie_secret="%T38*30$25^G2N43@13%6*0-OJtRew@134^7(OjgTR$4yIJv042!-8y74+5+=JI&TGu6t58",
            login_url="",
            xsrf_cookies=False,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "templates/static"),
            autoescape=None,
        )
        # prepend path to each handler with path to the app
        tornado.web.Application.__init__(self, handlers, **settings)


if __name__ == '__main__':
    Application.run()
