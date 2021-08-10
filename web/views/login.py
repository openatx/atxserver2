# coding: utf-8
#

from logzero import logger
from tornado.auth import OAuth2Mixin

from .auth import AuthError, OpenIdMixin, GithubOAuth2Mixin
from .base import BaseRequestHandler

from ..settings import AUTH_BACKENDS, GITHUB


class OpenIdLoginHandler(BaseRequestHandler, OpenIdMixin):
    _OPENID_ENDPOINT = AUTH_BACKENDS['openid']['endpoint']

    async def get(self):
        if self.get_argument("openid.mode", False):
            try:
                user = await self.get_authenticated_user()
            except AuthError as e:
                self.write(
                    "<code>Auth error: {}</code> <a href='/login'>Login</a>".
                    format(e))
            else:
                logger.info("User info: %s", user)
                await self.set_current_user(user['email'], user['name'])
                next_url = self.get_argument('next', '/')
                self.redirect(next_url)
        else:
            self.authenticate_redirect()


class SimpleLoginHandler(BaseRequestHandler):
    def get(self):
        self.set_cookie("next", self.get_argument("next", "/"))
        self.write('<html><body><form action="/login" method="post">'
                   'Name: <input type="text" name="name" required>'
                   '<input type="submit" value="Sign in">'
                   '</form></body></html>')

    async def post(self):
        name = self.get_argument("name")
        email = name + "@anonymous.com"
        await self.set_current_user(email, name)
        next_url = self.get_cookie("next", "/")
        self.clear_cookie("next")
        self.redirect(next_url)


class GithubLoginHandler(BaseRequestHandler, GithubOAuth2Mixin):

    async def get(self):
        if self.get_argument('code', False):
            access = await self.get_authenticated_user(
                redirect_uri=GITHUB['redirect_uri'],
                client_id=GITHUB['client_id'],
                client_secret=GITHUB['client_secret'],
                code=self.get_argument('code'))
            http = self.get_auth_http_client()

            response = await http.fetch(
                "https://api.github.com/user",
                headers={"Authorization": "token " + access["access_token"]}
            )
            user = escape.json_decode(response.body)
            logger.info("User info: %s", user)
            await self.set_current_user(user['email'], user['name'])
            next_url = self.get_argument('next', '/')
            self.redirect(next_url)
        # Save the user and access token with
        # e.g. set_secure_cookie.
        else:
            await self.authorize_redirect(
                redirect_uri=GITHUB['redirect_uri'],
                client_id=GITHUB['client_id'],
                scope=['user'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'})
