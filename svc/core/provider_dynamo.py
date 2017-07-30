class ProviderDynamo(object):
    def __init__(self, dynamo_db, name):
        """
        @type dynamo_db: object
        """
        self.dynamo_db = dynamo_db
        self.name = name

    def get_user_token(self, user):
        pass

    def set_user_token(self, user, token, expires):
        pass

    def set_user_param(self, user, param, value):
        pass

    def get_user_param(self, user, param):
        pass

    def delete_user_token(self, user):
        pass

    def delete_user(self, user):
        pass

    def set_user_album_id(self, user, album_id):
        pass

    def get_user_album_id(self, user):
        pass

    def root_key(self, user):
        pass

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