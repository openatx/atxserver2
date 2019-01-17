# coding: utf-8
"""
Extract code from https://github.com/tornadoweb/tornado/blob/master/tornado/auth.py
Modify in order to make it can be used in NetEase
"""
from __future__ import (absolute_import, division, print_function,
                        with_statement)

import functools
import sys

from tornado import httpclient
from tornado.concurrent import TracebackFuture, chain_future, return_future
from tornado.log import gen_log
from tornado.stack_context import ExceptionStackContext
from tornado.util import ArgReplacer, unicode_type
from tornado.web import RequestHandler

if sys.version_info > (3, 0):
    import urllib.parse as urlparse
    import urllib.parse as urllib_parse
    long = int
else:
    import urlparse
    import urllib as urllib_parse


class AuthError(Exception):
    pass


def _auth_future_to_callback(callback, future):
    try:
        result = future.result()
    except AuthError as e:
        gen_log.warning(str(e))
        result = None
    callback(result)


def _auth_return_future(f):
    """Similar to tornado.concurrent.return_future, but uses the auth
    module's legacy callback interface.
    Note that when using this decorator the ``callback`` parameter
    inside the function will actually be a future.
    """
    replacer = ArgReplacer(f, 'callback')

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        future = TracebackFuture()
        callback, args, kwargs = replacer.replace(future, args, kwargs)
        if callback is not None:
            future.add_done_callback(
                functools.partial(_auth_future_to_callback, callback))

        def handle_exception(typ, value, tb):
            if future.done():
                return False
            else:
                future.set_exc_info((typ, value, tb))
                return True
        with ExceptionStackContext(handle_exception):
            f(*args, **kwargs)
        return future
    return wrapper


class OpenIdMixin(object):
    """Abstract implementation of OpenID and Attribute Exchange.
    Class attributes:
    * ``_OPENID_ENDPOINT``: the identity provider's URI.
    """
    @return_future
    def authenticate_redirect(self, callback_uri=None,
                              ax_attrs=["nickname", "email", "fullname"],
                              callback=None):
        """Redirects to the authentication URL for this service.
        After authentication, the service will redirect back to the given
        callback URI with additional parameters including ``openid.mode``.
        We request the given attributes for the authenticated user by
        default (name, email, language, and username). If you don't need
        all those attributes for your app, you can request fewer with
        the ax_attrs keyword argument.
        .. versionchanged:: 3.1
           Returns a `.Future` and takes an optional callback.  These are
           not strictly necessary as this method is synchronous,
           but they are supplied for consistency with
           `OAuthMixin.authorize_redirect`.
        """
        callback_uri = callback_uri or self.request.uri
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs)
        self.redirect(self._OPENID_ENDPOINT + "?" + urllib_parse.urlencode(args))
        callback()

    @_auth_return_future
    def get_authenticated_user(self, callback=None, http_client=None):
        """Fetches the authenticated user data upon redirect.
        This method should be called by the handler that receives the
        redirect from the `authenticate_redirect()` method (which is
        often the same as the one that calls it; in that case you would
        call `get_authenticated_user` if the ``openid.mode`` parameter
        is present and `authenticate_redirect` if it is not).
        The result of this method will generally be used to set a cookie.
        """
        # Verify the OpenID response via direct request to the OP
        args = dict((k, v[-1]) for k, v in self.request.arguments.items())
        args["openid.mode"] = u"check_authentication"
        url = self._OPENID_ENDPOINT
        if http_client is None:
            http_client = self.get_auth_http_client()
        http_client.fetch(url, functools.partial(
            self._on_authentication_verified, callback),
            method="POST", body=urllib_parse.urlencode(args))

    def _openid_args(self, callback_uri, ax_attrs=[], oauth_scope=None):
        url = urlparse.urljoin(self.request.full_url(), callback_uri)
        args = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.claimed_id":
            "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.identity":
            "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.return_to": url,
            "openid.realm": urlparse.urljoin(url, '/'),
            "openid.mode": "checkid_setup",
        }
        if ax_attrs:
            args.update({
                "openid.ns.sreg": "http://openid.net/extensions/sreg/1.1",
                "openid.ns.ax": "http://openid.net/srv/ax/1.0",
                "openid.ax.mode": "fetch_request",
            })
            args["openid.sreg.required"] = ",".join(ax_attrs)
        if oauth_scope:
            args.update({
                "openid.ns.oauth":
                "http://specs.openid.net/extensions/oauth/1.0",
                "openid.oauth.consumer": self.request.host.split(":")[0],
                "openid.oauth.scope": oauth_scope,
            })

        return args

    def _on_authentication_verified(self, future, response):
        if response.error or b"is_valid:true" not in response.body:
            future.set_exception(AuthError(
                "Invalid OpenID response: %s" % (response.error or
                                                 response.body)))
            return

        def get_ax_arg(ax_name):
            return self.get_argument(ax_name, u"")

        email = get_ax_arg("openid.sreg.email")
        user = dict(
            email=email,
            username=email.split("@")[0],
            name=get_ax_arg("openid.sreg.fullname"),
        )
        claimed_id = self.get_argument("openid.claimed_id", None)
        if claimed_id:
            user["claimed_id"] = claimed_id

        future.set_result(user)

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.
        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()
