import os
import logging
import argparse

import tornado
from tornado import httpserver, web, ioloop, log

from core import data
from handlers import api
from handlers.auth import tumblr, google
from handlers import feed
from handlers.auth import facebook, twitter, flickr, px500, linkedin
import utils


class Application(tornado.web.Application):
    @staticmethod
    def run():
        parser = argparse.ArgumentParser(prog='Magenta River FE')
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

        # set up facebook credentials
        cfg = utils.config.load_config(args.config_path, 'facebook_credentials.json')

        application.settings.update(dict(
            facebook_api_key=cfg['facebook_api_key'],
            facebook_secret=cfg['facebook_secret'],
            facebook_scope=cfg['scope'],
            config_path=args.config_path,
            debug=args.debug,
            auth_redirects={
                'main': '/i.html#!/login.html',
                'selector': '/i.html#!/selector.html'
            },
        ))

        # set up twitter credentials
        cfg = utils.config.load_config(args.config_path, 'twitter_credentials.json')

        application.settings.update(dict(
            twitter_consumer_key=cfg['twitter_consumer_key'],
            twitter_consumer_secret=cfg['twitter_consumer_secret']
        ))

        # set up tumblr credentials
        cfg = utils.config.load_config(args.config_path, 'tumblr_credentials.json')

        application.settings.update(dict(
            tumblr_consumer_key=cfg['tumblr_consumer_key'],
            tumblr_consumer_secret=cfg['tumblr_consumer_secret']
        ))

        # set up flickr credentials
        cfg = utils.config.load_config(args.config_path, 'flickr_credentials.json')

        application.settings.update(dict(
            flickr_consumer_key=cfg['flickr_consumer_key'],
            flickr_consumer_secret=cfg['flickr_consumer_secret']
        ))

        # set up 500px credentials
        cfg = utils.config.load_config(args.config_path, '500px_credentials.json')

        application.settings.update({
            '500px_consumer_key': cfg['500px_consumer_key'],
            '500px_consumer_secret': cfg['500px_consumer_secret']
        })

        # set up linkedin credentials
        cfg = utils.config.load_config(args.config_path, 'linkedin_credentials.json')

        application.settings.update({
            'linkedin_consumer_key': cfg['consumer_key'],
            'linkedin_consumer_secret': cfg['consumer_secret']
        })

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
        self.logger = logger
        self.data = data.Data(logger=logger, redis_host=cfg['master_redis_host'], redis_port=cfg['master_redis_port'], redis_db=cfg['master_redis_db'])
        handlers = [
            # Google
            (r'/gl/login/?(.*)', google.GoogleLoginHandler),
            (r'/gl/logout/?', google.GoogleLogoutHandler),
            # Facebook
            (r'/fb/login', facebook.AuthLoginHandler),
            (r'/fbp/login', facebook.AuthLoginHandler, dict(m='p')),
            (r'/fbg/login', facebook.AuthLoginHandler, dict(m='g')),
            (r'/fba/login', facebook.AuthLoginHandler, dict(m='pg')),
            (r'/fb/logout', facebook.AuthLogoutHandler),
            # Twitter
            (r'/tw/login', twitter.AuthLoginHandler),
            (r'/tw/logout', twitter.AuthLogoutHandler),
            # Tumblr
            (r'/tl/login', tumblr.AuthLoginHandler),
            (r'/tl/logout', tumblr.AuthLogoutHandler),
            # Flickr
            (r'/fr/login', flickr.AuthLoginHandler),
            (r'/fr/logout', flickr.AuthLogoutHandler),
            # 500px
            (r'/5p/login', px500.AuthLoginHandler),
            (r'/5p/logout', px500.AuthLogoutHandler),
            # LinkedIn
            (r'/in/login', linkedin.AuthLoginHandler),
            (r'/in/logout', linkedin.AuthLogoutHandler),
            # RSS
            (r'/feed/??', feed.FeedHandler),
            # API
            (r'/api/v1/view/(.*)', api.view.ViewApiHandler),
            (r'/api/v1/user/?(.*)', api.user.UserApiHandler),
            (r'/api/v1/account/(.*)', api.account.AccountApiHandler),
            (r'/api/v1/source/(.*)', api.source.SourceApiHandler),
            (r'/api/v1/service/?(.*)', api.service.ServiceApiHandler),
        ]

        settings = dict(
            cookie_secret="%T38*30$25^G2N43@13%6*0-OJtRew@134^7(OjgTR$4yIJv042!-8y74+5+=JI&TGu6t58",
            login_url="",
            xsrf_cookies=False,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "templates/static"),
            autoescape=None,
            api_path=cfg['api_path'],
            payments_node=cfg['payments_node']
        )
        # prepend path to each handler with path to the app
        tornado.web.Application.__init__(self, handlers, **settings)


if __name__ == '__main__':
    Application.run()