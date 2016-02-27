import functools
import urllib as urllib_parse

from tornado import gen, escape
from tornado.auth import OAuthMixin, _auth_return_future, AuthError
from tornado.concurrent import return_future


class Px500Mixin(OAuthMixin):
    """PX500 OAuth authentication.
    """
    _OAUTH_REQUEST_TOKEN_URL = "https://api.500px.com/v1/oauth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "https://api.500px.com/v1/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://api.500px.com/v1/oauth/authorize"
    _OAUTH_AUTHENTICATE_URL = _OAUTH_AUTHORIZE_URL
    _OAUTH_NO_CALLBACKS = False
    _500PX_BASE_URL = "https://api.500px.com/v1"

    @return_future
    def authenticate_redirect(self, callback_uri=None, callback=None):
        """Just like `~OAuthMixin.authorize_redirect`, but
        auto-redirects if authorized.

        This is generally the right interface to use if you are using
        PX500 for single-sign on.

        .. versionchanged:: 3.1
           Now returns a `.Future` and takes an optional callback, for
           compatibility with `.gen.coroutine`.
        """
        http = self.get_auth_http_client()
        http.fetch(self._oauth_request_token_url(callback_uri=callback_uri),
                   functools.partial(self._on_request_token, self._OAUTH_AUTHENTICATE_URL, None, callback))

    def _oauth_consumer_token(self):
        self.require_setting("500px_consumer_key", "500px OAuth")
        self.require_setting("500px_consumer_secret", "500px OAuth")
        return dict(
            key=self.settings["500px_consumer_key"].encode(encoding='utf-8', errors='ignore'),
            secret=self.settings["500px_consumer_secret"].encode(encoding='utf-8', errors='ignore'))

    @_auth_return_future
    def api_request(self, path, callback=None, access_token=None, post_args=None, **args):
        """Fetches the given API path, e.g., ``statuses/user_timeline/btaylor``
        """
        if path.startswith('http:') or path.startswith('https:'):
            # Raw urls are useful for e.g. search which doesn't follow the
            # usual pattern: http://search.PX500.com/search.json
            url = path
        else:
            url = self._500PX_BASE_URL + path
        # Add the OAuth resource request signature if we have credentials
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            method = "POST" if post_args is not None else "GET"
            oauth = self._oauth_request_parameters(
                url, access_token, all_args, method=method)
            args.update(oauth)
        if args:
            url += "?" + urllib_parse.urlencode(args)
        http = self.get_auth_http_client()
        http_callback = functools.partial(self._on_request, callback)
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib_parse.urlencode(post_args),
                       callback=http_callback)
        else:
            http.fetch(url, callback=http_callback)

    def _on_request(self, future, response):
        if response.error:
            future.set_exception(AuthError("Error response %s fetching %s" % (response.error, response.request.url)))
            return
        future.set_result(escape.json_decode(response.body))

    @gen.coroutine
    def _oauth_get_user_future(self, access_token):

        user = yield self.api_request('/users', access_token=access_token)

        raise gen.Return(user)