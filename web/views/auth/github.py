import urllib.parse
import uuid

from logzero import logger

from tornado import httpclient
from tornado import escape
from tornado.auth import OAuth2Mixin
from tornado.httputil import url_concat
from tornado.util import unicode_type
from tornado.web import RequestHandler

from typing import List, Any, Dict, cast, Iterable, Union, Optional


class GithubOAuth2Mixin(OAuth2Mixin):

    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_SETTINGS_KEY = 'github'

    async def get_authenticated_user(self, redirect_uri: str, code: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        http = self.get_auth_http_client()
        body = urllib.parse.urlencode(
            {
                "redirect_uri": redirect_uri,
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
            }
        )

        response = await http.fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json"},
            body=body,
        )
        return escape.json_decode(response.body)
