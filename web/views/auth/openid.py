#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""This module contains implementations of various third-party
authentication schemes.

All the classes in this file are class mixins designed to be used with
the `tornado.web.RequestHandler` class.  They are used in two ways:

* On a login handler, use methods such as ``authenticate_redirect()``,
  ``authorize_redirect()``, and ``get_authenticated_user()`` to
  establish the user's identity and store authentication tokens to your
  database and/or cookies.
* In non-login handlers, use methods such as ``facebook_request()``
  or ``twitter_request()`` to use the authentication tokens to make
  requests to the respective services.

They all take slightly different arguments due to the fact all these
services implement authentication and authorization slightly differently.
See the individual service classes below for complete documentation.

Example usage for Google OAuth:

.. testcode::

    class GoogleOAuth2LoginHandler(tornado.web.RequestHandler,
                                   tornado.auth.GoogleOAuth2Mixin):
        async def get(self):
            if self.get_argument('code', False):
                user = await self.get_authenticated_user(
                    redirect_uri='http://your.site.com/auth/google',
                    code=self.get_argument('code'))
                # Save the user with e.g. set_secure_cookie
            else:
                await self.authorize_redirect(
                    redirect_uri='http://your.site.com/auth/google',
                    client_id=self.settings['google_oauth']['key'],
                    scope=['profile', 'email'],
                    response_type='code',
                    extra_params={'approval_prompt': 'auto'})

.. testoutput::
   :hide:

"""

import base64
import binascii
import hashlib
import hmac
import time
import urllib.parse
import uuid

from tornado import httpclient
from tornado import escape
from tornado.httputil import url_concat
from tornado.util import unicode_type
from tornado.web import RequestHandler

from typing import List, Any, Dict, cast, Iterable, Union, Optional


class AuthError(Exception):
    pass


class OpenIdMixin(object):
    """Abstract implementation of OpenID and Attribute Exchange.

    Class attributes:

    * ``_OPENID_ENDPOINT``: the identity provider's URI.
    """

    def authenticate_redirect(
            self,
            callback_uri: str = None,
            ax_attrs: List[str] = ["nickname", "email", "fullname"],
    ) -> None:
        """Redirects to the authentication URL for this service.

        After authentication, the service will redirect back to the given
        callback URI with additional parameters including ``openid.mode``.

        We request the given attributes for the authenticated user by
        default (name, email, language, and username). If you don't need
        all those attributes for your app, you can request fewer with
        the ax_attrs keyword argument.

        .. versionchanged:: 6.0

            The ``callback`` argument was removed and this method no
            longer returns an awaitable object. It is now an ordinary
            synchronous function.
        """
        handler = cast(RequestHandler, self)
        callback_uri = callback_uri or handler.request.uri
        assert callback_uri is not None
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs)
        endpoint = self._OPENID_ENDPOINT  # type: ignore
        from pprint import pprint
        pprint(args)
        handler.redirect(endpoint + "?" + urllib.parse.urlencode(args))

    async def get_authenticated_user(
            self,
            http_client: httpclient.AsyncHTTPClient = None) -> Dict[str, Any]:
        """Fetches the authenticated user data upon redirect.

        This method should be called by the handler that receives the
        redirect from the `authenticate_redirect()` method (which is
        often the same as the one that calls it; in that case you would
        call `get_authenticated_user` if the ``openid.mode`` parameter
        is present and `authenticate_redirect` if it is not).

        The result of this method will generally be used to set a cookie.

        .. versionchanged:: 6.0

            The ``callback`` argument was removed. Use the returned
            awaitable object instead.
        """
        handler = cast(RequestHandler, self)
        # Verify the OpenID response via direct request to the OP
        args = dict((k, v[-1]) for k, v in handler.request.arguments.items()
                    )  # type: Dict[str, Union[str, bytes]]
        args["openid.mode"] = u"check_authentication"
        url = self._OPENID_ENDPOINT  # type: ignore
        if http_client is None:
            http_client = self.get_auth_http_client()
        resp = await http_client.fetch(
            url, method="POST", body=urllib.parse.urlencode(args))
        return self._on_authentication_verified(resp)

    def _openid_args(self,
                     callback_uri: str,
                     ax_attrs: Iterable[str] = [],
                     oauth_scope: str = None) -> Dict[str, str]:
        handler = cast(RequestHandler, self)
        url = urllib.parse.urljoin(handler.request.full_url(), callback_uri)
        args = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.claimed_id":
            "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.identity":
            "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.return_to": url,
            "openid.realm": urllib.parse.urljoin(url, "/"),
            "openid.mode": "checkid_setup",
        }
        if ax_attrs:
            args.update({
                "openid.ns.sreg":
                "http://openid.net/extensions/sreg/1.1",  # Patch(ssx)
                "openid.ns.ax": "http://openid.net/srv/ax/1.0",
                "openid.ax.mode": "fetch_request",
            })
            # ax_attrs = set(ax_attrs)
            # required = []  # type: List[str]
            # if "name" in ax_attrs:
            #     ax_attrs -= set(["name", "firstname", "fullname", "lastname"])
            #     required += ["firstname", "fullname", "lastname"]
            #     args.update({
            #         "openid.ax.type.firstname":
            #         "http://axschema.org/namePerson/first",
            #         "openid.ax.type.fullname":
            #         "http://axschema.org/namePerson",
            #         "openid.ax.type.lastname":
            #         "http://axschema.org/namePerson/last",
            #     })
            # known_attrs = {
            #     "email": "http://axschema.org/contact/email",
            #     "language": "http://axschema.org/pref/language",
            #     "username": "http://axschema.org/namePerson/friendly",
            # }
            # for name in ax_attrs:
            #     args["openid.ax.type." + name] = known_attrs[name]
            #     required.append(name)
            # args["openid.ax.required"] = ",".join(required)

            args["openid.sreg.required"] = ",".join(ax_attrs)  # Patch(ssx)
        if oauth_scope:
            args.update({
                "openid.ns.oauth":
                "http://specs.openid.net/extensions/oauth/1.0",
                "openid.oauth.consumer":
                handler.request.host.split(":")[0],
                "openid.oauth.scope":
                oauth_scope,
            })
        return args

    def _on_authentication_verified(
            self, response: httpclient.HTTPResponse) -> Dict[str, Any]:
        handler = cast(RequestHandler, self)
        if b"is_valid:true" not in response.body:
            raise AuthError("Invalid OpenID response: %s" % response.body)

        # Make sure we got back at least an email from attribute exchange
        # ax_ns = None
        # for key in handler.request.arguments:
        #     if (key.startswith("openid.ns.") and handler.get_argument(key) ==
        #             u"http://openid.net/srv/ax/1.0"):
        #         ax_ns = key[10:]
        #         break

        def get_ax_arg(ax_name):
            return handler.get_argument(ax_name, u"")

        # def get_ax_arg(uri: str) -> str:
        #     if not ax_ns:
        #         return u""
        #     prefix = "openid." + ax_ns + ".type."
        #     ax_name = None
        #     for name in handler.request.arguments.keys():
        #         if handler.get_argument(name) == uri and name.startswith(
        #                 prefix):
        #             part = name[len(prefix):]
        #             ax_name = "openid." + ax_ns + ".value." + part
        #             break
        #     if not ax_name:
        #         return u""
        #     return handler.get_argument(ax_name, u"")

        email = get_ax_arg("openid.sreg.email")
        name = get_ax_arg("openid.sreg.fullname")
        username = email.split("@")[0]
        return dict(
            email=email,
            username=username,
            name=name,
        )
        # email = get_ax_arg("http://axschema.org/contact/email")
        # name = get_ax_arg("http://axschema.org/namePerson")
        # first_name = get_ax_arg("http://axschema.org/namePerson/first")
        # last_name = get_ax_arg("http://axschema.org/namePerson/last")
        # username = get_ax_arg("http://axschema.org/namePerson/friendly")
        # locale = get_ax_arg("http://axschema.org/pref/language").lower()
        # user = dict()
        # name_parts = []
        # if first_name:
        #     user["first_name"] = first_name
        #     name_parts.append(first_name)
        # if last_name:
        #     user["last_name"] = last_name
        #     name_parts.append(last_name)
        # if name:
        #     user["name"] = name
        # elif name_parts:
        #     user["name"] = u" ".join(name_parts)
        # elif email:
        #     user["name"] = email.split("@")[0]
        # if email:
        #     user["email"] = email
        # if locale:
        #     user["locale"] = locale
        # if username:
        #     user["username"] = username
        # claimed_id = handler.get_argument("openid.claimed_id", None)
        # if claimed_id:
        #     user["claimed_id"] = claimed_id
        # return user

    def get_auth_http_client(self) -> httpclient.AsyncHTTPClient:
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()
