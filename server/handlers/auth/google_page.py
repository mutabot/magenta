from handlers.auth.google import BaseGoogleLoginHandler


class BaseGooglePageLoginHandler(BaseGoogleLoginHandler):
    def __init__(self, application, request, **kwargs):
        super(BaseGooglePageLoginHandler, self).__init__(application,
                                                         request,
                                                         scope=[
                                                             'https://www.googleapis.com/auth/userinfo.profile',
                                                             'https://www.googleapis.com/auth/userinfo.email',
                                                             'https://www.googleapis.com/auth/plus.login',
                                                             'https://www.googleapis.com/auth/plus.me',
                                                             'https://www.googleapis.com/auth/youtube.readonly'
                                                         ],
                                                         **kwargs)


class GooglePageLoginHandler(BaseGooglePageLoginHandler):
    def get(self):
        self.redirect(self.flow.step1_get_authorize_url())