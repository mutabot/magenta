from logging import Logger

from tornado import gen

from core.schema import S1
from core import DataDynamo
from providers.facebook import FacebookPublisher
from providers.flickr import FlickrPublisher
from providers.linkedin import LinkedInPublisher
from providers.px500 import Px500Publisher
from providers.tumblr import TumblrPublisher
from providers.twitter import TwitterPublisher
from services.service_base import ServiceBase


class PublisherProviders(object):
    NAME_MAP = {
       'facebook': 'facebook',
       'twitter': 'twitter',
       'tumblr': 'tumblr',
       'flickr': 'flickr',
       '500px': 'px500',
       'linkedin': 'linkedin'
    }

    class facebook(FacebookPublisher):
        pass

    class twitter(TwitterPublisher):
        pass

    class tumblr(TumblrPublisher):
        pass

    class flickr(FlickrPublisher):
        pass

    class px500(Px500Publisher):
        pass

    class linkedin(LinkedInPublisher):
        pass

    @staticmethod
    def create(provider, logger, data, config_path):
        p_class = getattr(PublisherProviders, PublisherProviders.NAME_MAP[provider])
        return p_class(logger, data, config_path)


class Publisher(ServiceBase):
    def __init__(self, logger, name, data, provider_names, config_path, dummy=False):
        """
        @type data: DataDynamo
        @type logger: Logger
        @type provider_names: list
        """
        super(Publisher, self).__init__(logger, name, data, provider_names, config_path, dummy)

        self.providers = {S1.publisher_channel_name(p): PublisherProviders.create(p, logger, data, config_path)
                          for p in provider_names}

    @gen.coroutine
    def _on_publish_updates(self, channel, root_gid, pid):

        if root_gid:
            self.logger.info('Publishing updates for [{0}:{1}]'.format(root_gid, pid))
            if channel in self.providers.keys():
                context = yield self.load_context(root_gid, pid)
                self.providers[channel].publish(context)
        else:
            self.logger.debug('Not publishing updates, GID is empty')

    @gen.coroutine
    def _on_register(self, channel, pid):
        self.logger.info('Registering destination for [{0}]:[{1}]'.format(channel, pid))
        if channel in self.providers.keys():
            if self.providers[channel].register_destination(pid):
                self.logger.debug('Resetting error count for [{0}]:[{1}]'.format(self.providers[channel].name, pid))
                self.data.set_provider_error_count(self.providers[channel].name, pid, 0)
            else:
                self.logger.warning('Error while registering destination for [{0}]:[{1}]'.format(channel, pid))
        else:
            self.logger.error('ERROR: provider {0} not configured'.format(channel))

    @gen.coroutine
    def _on_update_avatar(self, channel, user):
        """
        invoked by queue to refresh avatars periodically
        """
        self.logger.info('Avatar refresh for [{0}:{1}]'.format(self.name, user))
        self.providers[channel].refresh_avatar(user)

    @gen.coroutine
    def run(self, *args, **kwargs):
        self.logger.info('Publisher [{0}], starting...'.format(self.name))

        callback = {
            S1.msg_publish(): self._on_publish_updates,
            S1.msg_register(): self._on_register,
            S1.msg_update_avatar(): self._on_update_avatar,
        }

        channels = [S1.publisher_channel_name('all'), S1.publisher_channel_name(self.name)]
        channels.extend([name for name in self.providers.keys() if name != self.name])

        # this will start infinite loop (in Pubsub)
        yield self.listener(channels, callback)
        self.logger.warning('Publisher [{0}], listener exit!'.format(self.name))

    def on_terminate(self, *args, **kwargs):
        self.logger.warning('Publisher is force terminating')
        self.terminate()

    def on_exit(self, channel):
        self.logger.warning('Publisher terminating on exit message')
        self.terminate()

    @gen.coroutine
    def load_context(self, root_gid, pid):
        gl_user = yield self.data.load_account_async(root_gid)
        # find all
