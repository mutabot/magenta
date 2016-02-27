import traceback
import redis


class Pubsub(object):
    MESSAGE_PREFIX = '~M~'
    MESSAGE_PREFIX_LEN = 3
    EXIT_MESSAGE = '~EXIT~'

    def __init__(self, logger, rc):
        """
        @type rc: redis.Redis
        """
        super(Pubsub, self).__init__()
        self.logger = logger
        self.rc = rc
        self.is_running = True

    @staticmethod
    def _format_message(message, args):
        if args:
            return ''.join([Pubsub.MESSAGE_PREFIX, message, '/', '/'.join(args)])
        else:
            return ''.join([Pubsub.MESSAGE_PREFIX, message])

    def broadcast_data(self, channel, data):
        """ send a command via Redis list push """
        self.logger.debug('DTA --> {0} <-- [{1}]'.format(channel, data))
        self.rc.rpush(channel, data)

    def broadcast_data_now(self, channel, data):
        """ send a command via Redis list push """
        self.logger.debug('DTA NOW --> {0} <-- [{1}]'.format(channel, data))
        self.rc.lpush(channel, data)

    def broadcast_command(self, channel, message, *args):
        """ send a command via Redis list push """
        msg = Pubsub._format_message(message, args)
        self.logger.debug('CMD --> {0} <-- [{1}]'.format(channel, msg))
        self.rc.rpush(channel, msg)

    def broadcast_command_now(self, channel, message, *args):
        """ send a command via Redis list push """
        msg = Pubsub._format_message(message, args)
        self.logger.debug('CMD NOW --> {0} <-- [{1}]'.format(channel, msg))
        self.rc.lpush(channel, msg)

    def send_exit(self, channel, self_target=False):
        if self_target and not self.is_running:
            self.logger.warning('Can\'t send exit to self, my listener is not running')
            return False

        self.broadcast_command_now(channel, Pubsub.EXIT_MESSAGE)
        self.logger.warning('Exit sent to: {0}'.format(channel))

    def listener(self, channels, callback, timeout=0):
        """
        infinite command processing loop
        channels: list of channels to subscribe to
        callback: dict where key is a callback name, and value is a callback func
        @type channels: list
        """
        self.logger.info('Listener start on {0}'.format(channels))
        while self.is_running:
            item = self.rc.blpop(channels, timeout=timeout)
            try:
                # fire timeout callback on timeout
                if not item:
                    self.on_timeout()
                    continue

                # else try callback option
                if item[1].startswith(Pubsub.MESSAGE_PREFIX):

                    params = item[1][Pubsub.MESSAGE_PREFIX_LEN:].split('/')
                    cb = params.pop(0)
                    if callback and cb in callback:
                        # normal callback
                        callback[cb](item[0], *params)
                    elif cb == Pubsub.EXIT_MESSAGE:
                        self.logger.warning('Exit message received!')
                        # exit message detected
                        self.on_exit(item[0])
                else:
                    # raw data processor callback
                    self.on_raw(item[0], item[1])

            except Exception as e:
                self.logger.error('Exception in listener {0}, {1}'.format(e, traceback.format_exc()))

        self.logger.info('Listener exit')

    def terminate(self):
        self.is_running = False

    def on_timeout(self):
        pass

    def on_raw(self, channel, raw):
        pass

    def on_exit(self, channel):
        """
        Fired when EXIT_MESSAGE is sent to this listener. Users must call self.terminate() to exit listener loop nicely
        @param channel:
        @return:
        """
        pass