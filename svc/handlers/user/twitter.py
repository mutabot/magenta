class UserData(object):
    @staticmethod
    def populate(raw):
        if not raw or not 'id' in raw:
            return None

        return {'id': raw['id_str'],
                'name': raw['name'],
                'url': 'https://twitter.com/{0}'.format(raw['username']),
                'picture_url': raw['profile_image_url_https'] if 'profile_image_url_https' in raw else raw['profile_image_url'],
                'token': raw['access_token'],
                'master': True}

    @staticmethod
    def is_token_refresh():
        return False