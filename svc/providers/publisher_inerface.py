

class PublisherInterface(object):
    def register_destination(self, context):
        pass

    def refresh_avatar(self, user):
        pass

    def publish_photo(self, user, feed, message, message_id, token):
        pass

    def publish_album(self, user, album, feed, message, message_id, token):
        pass

    def publish_text(self, user, feed, message, message_id, token):
        pass

    def publish_link(self, user, feed, message, message_id, token):
        pass

    def is_delete_message(self, user, feed):
        return True

    def is_expand_buzz(self):
        return True

    def delete_message(self, user, message_id, token):
        return True

    def get_root_endpoint(self):
        pass

    def get_token(self, user):
        pass

    def is_dummy(self):
        pass

    def get_user_param(self, user, param):
        pass

    def process_result(self, message_id, result, user, log_func, context):
        pass
