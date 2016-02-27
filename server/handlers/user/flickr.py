class UserData(object):
    @staticmethod
    def populate(raw):
        if not raw or not 'user' in raw:
            return None

        user = raw['user']
        return {'id': user['id'].encode(encoding='utf-8', errors='ignore'),
                'name': user['username']['_content'].encode(encoding='utf-8', errors='ignore') if 'username' in user else user['id'].encode(encoding='utf-8', errors='ignore'),
                'url': 'https://flickr.com/{0}'.format(user['id'].encode(encoding='utf-8', errors='ignore')),
                'picture_url': '',
                'token': raw['access_token'] if 'access_token' in raw else None,
                'master': True}

    @staticmethod
    def is_token_refresh():
        return False