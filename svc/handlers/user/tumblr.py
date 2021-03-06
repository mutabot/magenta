class UserData(object):
    @staticmethod
    def populate(raw):
        if not raw or not 'name' in raw:
            return None

        return {'id': raw['name'],
                'name': raw['title'],
                'url': 'http://{0}.tumblr.com'.format(raw['name']),
                'picture_url': raw['avatar'] if 'avatar' in raw else '',
                'token': raw['access_token'] if 'access_token' in raw else None,
                'master': raw['master']}

    @staticmethod
    def is_token_refresh():
        return False