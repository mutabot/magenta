import functools
import urllib as urllib_parse

from tornado import escape, httpclient
from tornado.auth import _auth_return_future, AuthError, OAuth2Mixin


class LinkedInMixin(OAuth2Mixin):
    """Linked-In OAuth2 authentication.
    """
    _OAUTH_ACCESS_TOKEN_URL = "https://www.linkedin.com/uas/oauth2/accessToken?"
    _OAUTH_AUTHORIZE_URL = "https://www.linkedin.com/uas/oauth2/authorization?"
    _OAUTH_NO_CALLBACKS = False
    _LINKEDIN_BASE_URL = "https://api.linkedin.com/v1"

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, client_id, client_secret,
                               code, callback, extra_fields=None):
        """Handles the login for the LinkedIn user, returning a user object.

        Example usage::

            class LinkedInLoginHandler(LoginHandler, LinkedInMixin):
              @tornado.web.asynchronous
              @tornado.gen.coroutine
              def get(self):
                  if self.get_argument("code", False):
                      user = yield self.get_authenticated_user(
                          redirect_uri='/auth/linkedin/',
                          client_id=self.settings["linkedin_api_key"],
                          client_secret=self.settings["linkedin_secret"],
                          code=self.get_argument("code"))
                      # Save the user with e.g. set_secure_cookie
                  else:
                      yield self.authorize_redirect(
                          redirect_uri='/auth/linkedin/',
                          client_id=self.settings["linkedin_api_key"],
                          extra_params={"scope": "r_fullprofile,r_emailaddress,r_network"})
        """
        http = self.get_auth_http_client()
        args = {
            "extra_params": {"grant_type": "authorization_code"},
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        http.fetch(self._oauth_request_token_url(**args),
                   functools.partial(
                       self._on_access_token, redirect_uri, client_id,
                       client_secret, callback, None))

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                         future, fields, response):
        if response.error:
            future.set_exception(AuthError('LinkedIn auth error: %s' % str(response)))
            return

        session = escape.json_decode(response.body)
        http_callback = functools.partial(self._on_get_user_info, future, session)
        self.linkedin_request(
            path="/people/~:(id,formatted-name,public-profile-url,picture-url;secure=true)",
            callback=http_callback,
            access_token=session["access_token"])

    def _on_get_user_info(self, future, session, user):
        if user is None:
            future.set_result(None)
            return

        user.update(session)
        future.set_result(user)

    @_auth_return_future
    def linkedin_request(self, path, callback, access_token=None,
                         post_args=None, **args):
        """Fetches the given relative API path, e.g., "/people/~"

        If the request is a POST, ``post_args`` should be provided. Query
        string arguments should be given as keyword arguments.

        Many methods require an OAuth access token which you can
        obtain through `~OAuth2Mixin.authorize_redirect` and
        `get_authenticated_user`. The user returned through that
        process includes an ``access_token`` attribute that can be
        used to make authenticated requests via this method.

        Example usage::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.LinkedInMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                @tornado.gen.coroutine
                def get(self):
                    new_entry = yield self.linkedin_request(
                        "/people/~/shares",
                        post_args={"content": "I am posting from my Tornado application!"},
                        access_token=self.current_user["access_token"])

                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        yield self.authorize_redirect()
                        return
                    self.finish("Posted a message!")

        """
        url = self._LINKEDIN_BASE_URL + path
        all_args = {
            "secure-urls": "true",
            "format": "json"
        }
        if access_token:
            all_args["oauth2_access_token"] = access_token
            all_args.update(args)

        if all_args:
            url += "?" + urllib_parse.urlencode(all_args)
        http = self.get_auth_http_client()
        http_callback = functools.partial(self._on_linkedin_request, callback)
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib_parse.urlencode(post_args),
                       callback=http_callback)
        else:
            http.fetch(url, callback=http_callback)

    def _on_linkedin_request(self, future, response):
        if response.error:
            future.set_exception(AuthError("Error response %s fetching %s" %
                                           (response.error, response.request.url)))
            return

        future.set_result(escape.json_decode(response.body))

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()

