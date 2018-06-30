import redis
from core.schema import S1


class ProviderData(object):
    def __init__(self, rc, name):
        """
        @type rc: redis.Redis
        """
        self.rc = rc
        self.name = name

    def get_user_token(self, user):
        return self.rc.hget(self.root_key(user), self.token_key())

    def set_user_token(self, user, token, expires):
        self.rc.hset(self.root_key(user), self.token_key(), token)
        self.rc.hset(self.root_key(user), self.token_expiry_key(), expires)

    def set_user_param(self, user, param, value):
        self.rc.hset(self.root_key(user), self.param_key_fmt(param), value)

    def get_user_param(self, user, param):
        return self.rc.hget(self.root_key(user), self.param_key_fmt(param))

    def get_user_params(self, user):
        return self.rc.hgetall(self.root_key(user))

    def delete_user_token(self, user):
        self.rc.hdel(self.root_key(user), self.token_key())
        self.rc.hdel(self.root_key(user), self.token_expiry_key())

    def delete_user(self, user):
        self.rc.delete(self.root_key(user))

    def set_user_album_id(self, user, album_id):
        return self.rc.hset(self.root_key(user), self.album_key(), album_id)

    def get_user_album_id(self, user):
        return self.rc.hget(self.root_key(user), self.album_key())

    def root_key(self, user):
        return S1.provider_root_key(self.name, user)

    @staticmethod
    def token_key():
        return 'token'

    @staticmethod
    def token_expiry_key():
        return 'token.expiry'

    @staticmethod
    def album_key():
        return 'album'

    @staticmethod
    def param_key_fmt(param):
        return 'param:{0}'.format(param)