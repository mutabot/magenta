from logging import Logger

from tornado import gen

from core import DataDynamo
from core.model import SocialAccount
from core.schema import S1
from providers import PublisherContext
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

    @staticmethod
    def get_service(service_name, logger, data, config_path):
        if service_name == 'facebook':
            from providers.facebook import FacebookPublisher
            return FacebookPublisher(logger, data, config_path)

        if service_name == 'flickr':
            from providers.flickr import FlickrPublisher
            return FlickrPublisher(logger, data, config_path)

        if service_name == 'linkedin':
            from providers.linkedin import LinkedInPublisher
            return LinkedInPublisher(logger, data, config_path)

        if service_name == '500px':
            from providers.px500 import Px500Publisher
            return Px500Publisher(logger, data, config_path)

        if service_name == 'tumblr':
            from providers.tumblr import TumblrPublisher
            return TumblrPublisher(logger, data, config_path)

        if service_name == 'twitter':
            from providers.twitter import TwitterPublisher
            return TwitterPublisher(logger, data, config_path)

        raise NotImplementedError('Unknown provider')

    @staticmethod
    def create(provider, logger, data, config_path):
        return PublisherProviders.get_service(provider, logger, data, config_path)


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
                yield self.providers[channel].publish(context)

                # serialise the user's data
                yield self.save_context(context)
        else:
            self.logger.debug('Not publishing updates, GID is empty')

    @gen.coroutine
    def _on_register(self, channel, root_gid, pid):
        if channel not in self.providers.keys():
            self.logger.error('ERROR: provider {0} not configured'.format(channel))
            return

        provider = self.providers[channel].name
        self.logger.info('Registering destination for [{0}]:[{1}]'.format(provider, pid))

        context = yield self.load_context(root_gid, pid)  # type: PublisherContext

        # only care about the target in this context
        target_key = SocialAccount('', provider, pid).Key
        context.target = DataDynamo.get_account(context.root, target_key)

        result = self.providers[channel].register_destination(context)
        if result:
            self.logger.debug('NOT Resetting error count for [{0}]:[{1}]'.format(provider, pid))
            # TODO: Is this even used?
            # self.data.set_provider_error_count(self.providers[channel].name, pid, 0)

            # serialise the user's data
            context.root.dirty.add('accounts')
            yield self.save_context(context)
        else:
            self.logger.warning('Error while registering destination for [{0}]:[{1}]'.format(provider, pid))

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
        # type: (str, str) -> PublisherContext

        gl_user = yield self.data.load_account_async(root_gid)

        # find all targets for the pid and this provider
        # TODO: Google hardcoded
        source_key = SocialAccount.make_key('google', pid)
        # not required as downstream code will loop over links for this source
        # links = [Publisher.get_context(gl_user, link) for link in gl_user.links.itervalues() if link.source == source_key]  # type: List[Link]

        result = PublisherContext()
        result.root = gl_user
        result.source = SocialAccount(root_gid, 'google', pid)

        raise gen.Return(result)

    # @staticmethod
    # def get_context(gl_user, link):
    #    result = PublisherContext()
    #    result.root = gl_user
    #    result.link = link
    #    result.source = DataDynamo.get_account(gl_user, link.source)
    #    result.target = DataDynamo.get_account(gl_user, link.target)
    #    return result

    @gen.coroutine
    def save_context(self, context):
        # type: (PublisherContext) -> None
        yield self.data.save_account_async(context.root)
