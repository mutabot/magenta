
class UserData(object):
    @staticmethod
    def populate(raw):
        if not raw or not 'id' in raw:
            return None

        return {'id': raw['id'],
                'name': raw['name'],
                'url': 'https://facebook.com/{0}'.format(raw['id']),
                'picture_url': raw['picture']['data']['url'] if 'picture' in raw else raw['avatar_url'] if 'avatar_url' in raw else '',
                'token': raw['access_token'],
                'master': raw['master'] if 'master' in raw else False}

    @staticmethod
    def is_token_refresh():
        return True