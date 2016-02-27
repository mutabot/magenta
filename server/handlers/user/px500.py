class UserData(object):
    @staticmethod
    def populate(raw):
        if not raw or not 'user' in raw:
            return None

        user = raw['user']
        return {'id': str(user['id']),
                'name': user['fullname'].encode(encoding='utf-8', errors='ignore') if 'fullname' in raw else user['username'].encode(encoding='utf-8', errors='ignore'),
                'url': 'http://500px.com/{0}'.format(user['username'].encode(encoding='utf-8', errors='ignore')),
                'picture_url': user['userpic_https_url'].encode(encoding='utf-8', errors='ignore') if 'userpic_https_url' in user else user['userpic_url'].encode(encoding='utf-8', errors='ignore'),
                'token': raw['access_token'] if 'access_token' in raw else None,
                'master': True}

    @staticmethod
    def is_token_refresh():
        return False