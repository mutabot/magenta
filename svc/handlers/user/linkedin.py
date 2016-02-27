class UserData(object):
    @staticmethod
    def populate(raw):
        if not raw or not 'id' in raw:
            return None

        return {'id': raw['id'],
                'name': raw['formattedName'],
                'url': raw['publicProfileUrl'] if 'publicProfileUrl' in raw else u'',
                'picture_url': raw['pictureUrl'] if 'pictureUrl' in raw else u'',
                'token': raw['access_token'],
                'master': raw['master'] if 'master' in raw else True}

    @staticmethod
    def is_token_refresh():
        return False