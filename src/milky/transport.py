from __future__ import annotations

import contextlib
import hashlib
import os
import urllib.parse
import webbrowser
from dataclasses import dataclass
from functools import cached_property

try:
    from defusedxml.etree import ElementTree
except ImportError:
    from xml.etree import ElementTree  # noqa: DUO107, S405

from typing import Any, Dict, Optional, Sequence, Tuple, TYPE_CHECKING, Union

import milky

TYPE_CHECKING = TYPE_CHECKING or os.environ.get('TYPE_CHECKING') == '1'

if TYPE_CHECKING:
    import httpx
    import requests
    from typing_extensions import TypeAlias

    Response = Union[requests.models.Response, httpx.Response]
    Element: TypeAlias = ElementTree.Element  # pytype: disable=invalid-annotation
    ResponseContent = Union[Element, Dict[str, Any]]
    Client = Union[requests.Session, httpx.Client]


def _client_maker() -> Optional[Client]:
    with contextlib.suppress(ImportError):
        import httpx

        return httpx.Client(follow_redirects=True)

    with contextlib.suppress(ImportError):
        import requests

        return requests.Session()

    return None


class ResponseError(Exception):
    def __init__(self, response: ResponseContent, code: int, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message
        self.response = response

    def __str__(self) -> str:
        return f'{self.code}: {self.message}'


@dataclass(frozen=True)
class Identity:
    username: str
    perms: str
    user_id: int
    fullname: str

    @classmethod
    def from_response(cls, resp: Element) -> Identity:
        u = resp.find('auth/user').attrib
        return Identity(
            perms=resp.find('auth/perms').text,
            user_id=int(u['id']),
            username=u['username'],
            fullname=u['fullname'],
        )

    def __str__(self) -> str:
        return f'"{self.username}" with {self.perms} permissions'


class Transport:

    AUTH_URL = 'https://api.rememberthemilk.com/services/auth/'
    REST_URL = 'https://api.rememberthemilk.com/services/rest/'
    frob = None

    def __init__(
        self,
        api_key: str,
        secret: str,
        token: Optional[str] = None,
        client: Optional[Client] = None,
    ) -> None:
        self.api_key = api_key
        self.secret = secret
        self._token = token

        # Try to create a client if one isn't given.
        if not client:
            if not (client := _client_maker()):
                err = 'cannot import "httpx" or "requests" to create client'
                raise RuntimeError(err)

            hdrs = client.headers
            our_ua = hdrs['User-Agent']
            my_ua = f" milky/{milky.__version__}"

            if isinstance(our_ua, bytes):
                our_ua = our_ua.decode('utf-8')
            hdrs['User-Agent'] = our_ua + my_ua

        self.client = client

    def invoke(self, method: str, **kwargs: Union[str, int, bool]) -> ResponseContent:
        if kwargs.get('auth_token') is False:
            del kwargs['auth_token']
        elif not self.token:
            raise RuntimeError('token is required')
        else:
            kwargs.setdefault('auth_token', self.token)

        kwargs.setdefault('v', 2)
        is_json = kwargs.get('format') == 'json'

        params = self.sign_params(method=method, **kwargs)

        resp = self.client.get(
            self.REST_URL, params=dict(params), headers={"cache-control": "no-cache"}
        )
        resp.raise_for_status()

        return self.process_response(resp, is_json)

    @classmethod
    def process_response(cls, resp: Response, is_json: bool) -> ResponseContent:
        err = None

        if is_json:
            result = resp.json()
            if result['rsp']['stat'] == 'fail':
                err = result['rsp']['err']
        else:
            result = ElementTree.fromstring(resp.text)  # noqa: S314
            if result.get('stat') == 'fail':
                err = result.find('err')

        if err is not None:
            raise ResponseError(result, int(err.get('code')), err.get('msg'))

        return result

    def sign_params(
        self, **params: Union[str, int]
    ) -> Sequence[Tuple[str, Union[str, int]]]:
        params.setdefault('api_key', self.api_key)
        param_pairs = tuple(sorted(params.items()))
        paramstr = ''.join(f'{k}{v}' for (k, v) in param_pairs)
        payload = f'{self.secret}{paramstr}'
        sig = hashlib.md5(payload.encode('utf-8')).hexdigest()  # noqa: S303
        return param_pairs + (('api_sig', sig),)

    def __autoauth(self) -> bool:
        if (not self._token) and self.frob:
            self.finish_auth()
            return True
        return False

    @property
    def token(self) -> Optional[str]:
        self.__autoauth()
        return self._token

    @token.setter
    def token(self, value: Optional[str]) -> None:
        self._token = value
        with contextlib.suppress(AttributeError):
            del self.frob
        with contextlib.suppress(AttributeError):
            del self.whoami

    def __check_token(self) -> Optional[Element]:
        if not self._token:
            return None
        try:
            return self.invoke('rtm.auth.checkToken')
        except ResponseError as e:
            if e.code == 98:
                return None
            raise

    @cached_property
    def whoami(self) -> Optional[Identity]:
        # If true, evaluating self.authed will set the whoami object.
        return self.whoami if self.authed else None

    @property
    def authed(self) -> bool:
        # Handle the auto-authentication workflow.
        try:
            if self.__autoauth():
                return True
        except ResponseError as e:
            if e.code == 101:  # Invalid or unauthenticated frob.
                return False
            raise

        res = self.__check_token()
        self.whoami = Identity.from_response(res) if res else None
        return bool(res)

    def start_auth(
        self, perms: str = 'read', open: bool = False, webapp: bool = False
    ) -> str:
        params = {}
        if not webapp:
            rsp: Element = self.invoke('rtm.auth.getFrob', auth_token=False)
            self.token = None
            params['frob'] = self.frob = rsp.find('frob').text

        param_pairs = self.sign_params(perms=perms, **params)
        url = self.AUTH_URL + '?' + urllib.parse.urlencode(param_pairs)

        if open:
            if webapp:
                raise ValueError('cannot use "open" and "webapp" together')
            webbrowser.open(url)

        return url

    def finish_auth(self) -> None:
        if not self.frob:
            raise RuntimeError('must call start_auth first')
        resp: Element = self.invoke(
            'rtm.auth.getToken', frob=self.frob, auth_token=False
        )
        self.token = resp.find('auth/token').text
        self.whoami = Identity.from_response(resp)
