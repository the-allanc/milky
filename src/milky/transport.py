"""Logic to communicate with Remember The Milk's API."""

from __future__ import annotations

import contextlib
import enum
import hashlib
import urllib.parse
import webbrowser

from dataclasses import dataclass
from typing import Any, TypeAlias, TYPE_CHECKING

from xml.etree import ElementTree as ET  # noqa: RUF100, DUO107, S405

import milky

from milky.cache import cache_controlled

if TYPE_CHECKING:
    from collections.abc import Sequence

    import httpx
    import requests

    Response: TypeAlias = requests.models.Response | httpx.Response
    ResponseContent = ET.Element | dict[str, Any]
    Client: TypeAlias = requests.Session | httpx.Client
    ParamType = int | str


def _client_maker() -> Client | None:
    with contextlib.suppress(ImportError):
        import httpx

        return httpx.Client(follow_redirects=True)

    with contextlib.suppress(ImportError):
        import requests

        return requests.Session()

    return None


class ResponseError(Exception):
    """Error returned by Remember The Milk."""

    def __init__(self, response: ResponseContent, code: int, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message
        self.response = response

    def __str__(self) -> str:
        return f'{self.code}: {self.message}'

    @classmethod
    def from_response(
        cls: type, response: ResponseContent, err_obj: ET.Element | dict[str, str]
    ) -> ResponseError:
        code = int(err_obj.get('code', '0'))
        message = err_obj.get('msg', 'Unknown error')
        return cls(response, code, message)


@dataclass(frozen=True)
class Identity:
    """Object that represents a logged-in user."""

    username: str
    perms: str
    user_id: int
    fullname: str

    @staticmethod
    def from_response(resp: ET.Element) -> Identity:
        """Create an Identity object from an `Element` object."""
        usr = resp.find('auth/user')
        assert usr is not None
        u = usr.attrib

        perms = resp.find('auth/perms')
        assert perms is not None

        return Identity(
            perms=perms.text or '',
            user_id=int(u['id']),
            username=u['username'],
            fullname=u['fullname'],
        )

    def __str__(self) -> str:
        return f'"{self.username}" with {self.perms} permissions'


class ResponseCodes(enum.Enum):
    """Response codes returned by RTM."""

    LOGIN_FAILED_OR_BAD_TOKEN = 98
    INVALID_FROB = 101


class Transport:
    """Class that represents a connection to Remember The Milk."""

    AUTH_URL = 'https://api.rememberthemilk.com/services/auth/'
    REST_URL = 'https://api.rememberthemilk.com/services/rest/'
    frob = None

    def __init__(
        self,
        api_key: str,
        secret: str,
        token: str | None = None,
        client: Client | None = None,
    ) -> None:
        """Create a Transport object.

        Args:
          api_key: A string containing the API key.
          secret: A string containing the shared secret.
          token: The token to use, if one is available.
          client: A httpx.Client or [requests.Session][] object to use,
                  otherwise one will be automatically created.
        """
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

    def invoke_request(self, method: str, **kwargs: ParamType) -> Response:
        """Invokes a RTM method and returns the HTTP response. This method is
        mainly provided for overriding and debugging purposes - the "invoke" and
        "invoke_json" methods are preferable as they decode the response.

        Parameters to pass the method should be given as keyword arguments.
        Some parameters have special behaviours in this method:
          * "auth_token" is automatically populated if it is missing, and if
            the authentication flow needs to be completed first, this will
            be done first.
          * If "auth_token" is set to False, this will be treated as an
            unauthenticated method call.
          * "version" defaults to "2" unless overridden.

        Args:
          method: The name of the RTM method to invoke (e.g "rtm.test.echo").
          **kwargs: Parameters to send for the method.

        Raises:
          RuntimeError: if authentication is required, but no token is given.
          HTTPError: if an HTTP error occurs handling the response.
        """
        if kwargs.get('auth_token') is False:
            del kwargs['auth_token']
        elif not self.token:
            raise RuntimeError('token is required')
        else:
            kwargs.setdefault('auth_token', self.token)

        kwargs.setdefault('v', 2)
        params = self.sign_params(method=method, **kwargs)

        resp = self.client.get(
            self.REST_URL, params=dict(params), headers={"cache-control": "no-cache"}
        )
        resp.raise_for_status()
        return resp

    def invoke(self, method: str, **kwargs: ParamType) -> ET.Element:
        """Invokes a RTM method, decodes the HTTP response and returns the content
        as an XML element.

        The behaviour of this method is the same as `invoke_request` - the specific
        details of that method also apply here.

        Args:
          method: The name of the RTM method to invoke (e.g "rtm.test.echo").
          **kwargs: Parameters to send for the method.

        Raises:
          RuntimeError: if authentication is required, but no token is given.
          HTTPError: if an HTTP error occurs handling the response.
          ResponseError: if RTM reports an error in the response.
        """
        if kwargs.get('format') not in [None, 'xml']:
            raise ValueError('invalid format given')

        resp = self.invoke_request(method, **kwargs)
        result = ET.fromstring(resp.text)  # noqa: S314
        if result.get('stat') == 'fail':
            err = result.find('err')
            assert err is not None
            raise ResponseError.from_response(result, err)

        return result

    def invoke_json(self, method: str, **kwargs: ParamType) -> dict[str, Any]:
        """Invokes a RTM method, decodes the HTTP response and returns the content
        as a JSON-decoded structure.

        The behaviour of this method is the same as `invoke_request` - the specific
        details of that method also apply here.

        Args:
          method: The name of the RTM method to invoke (e.g "rtm.test.echo").
          **kwargs: Parameters to send for the method.

        Raises:
          RuntimeError: if authentication is required, but no token is given.
          HTTPError: if an HTTP error occurs handling the response.
          ResponseError: if RTM reports an error in the response.
        """
        if kwargs.get('format') not in [None, 'json']:
            raise ValueError('invalid format given')

        resp = self.invoke_request(method, format='json', **kwargs)

        result = resp.json()  # noqa: RUF100, S303
        if result['rsp']['stat'] == 'fail':
            err = result['rsp']['err']
            raise ResponseError.from_response(result, err)

        return result

    def sign_params(self, **params: str | int) -> Sequence[tuple[str, ParamType]]:
        """Sign some parameters for Remember The Milk.

        Given some key-value parameters to send to Remember The Milk,
        return a sequence of key, value pairs that includes a signature
        parameter that will verify this is a valid request.
        """
        params.setdefault('api_key', self.api_key)
        param_pairs = tuple(sorted(params.items()))
        paramstr = ''.join(f'{k}{v}' for (k, v) in param_pairs)
        payload = f'{self.secret}{paramstr}'
        sig = hashlib.md5(payload.encode('utf-8')).hexdigest()  # noqa: S324
        return (*param_pairs, ('api_sig', sig))

    def __autoauth(self) -> bool:
        if (not self._token) and self.frob:
            self.finish_auth()
            return True
        return False

    @property
    def token(self) -> str | None:
        """Return the current token associated with the connection."""
        self.__autoauth()
        return self._token

    @token.setter
    def token(self, value: str | None) -> None:
        self._token = value
        with contextlib.suppress(AttributeError):
            del self.frob
        with contextlib.suppress(AttributeError):
            del self.whoami

    def __check_token(self) -> ET.Element | None:
        if not self._token:
            return None
        try:
            return self.invoke('rtm.auth.checkToken')
        except ResponseError as e:
            if e.code == ResponseCodes.LOGIN_FAILED_OR_BAD_TOKEN.value:
                return None
            raise

    @cache_controlled(None)
    def whoami(self) -> Identity | None:
        """The Identity object describing the current user associated.

        If the user is not authenticated, the value will be None.

        This attribute is updated upon authentication, and whenever
        the `authed` attribute is accessed. Repeated accesses will
        not normally result in a call to Remember The Milk being made.
        """
        # If true, evaluating self.authed will set the whoami object.
        return self.whoami if self.authed else None

    @property
    def authed(self) -> bool:
        """Indicates if the transport is currently authorised.

        Accessing this attribute will normally cause
        a call to Remember The Milk to determine it each time.
        """
        # Handle the auto-authentication workflow.
        try:
            if self.__autoauth():
                return True
        except ResponseError as e:
            if e.code == ResponseCodes.INVALID_FROB.value:
                return False
            raise

        res = self.__check_token()
        self.whoami = Identity.from_response(res) if res else None
        return bool(res)

    def start_auth(
        self,
        perms: str = 'read',
        open: bool = False,  # noqa: A002
        webapp: bool = False,
    ) -> str:
        """Start the authentication process.

           Once the user has confirmed
           access, the finish_auth method can optionally be called to complete
           the authentication process. Otherwise, this will be done automatically
           as the Transport object is used to make method invocations.

        Args:
          perms: The level of permissions desired - should be one of "read",
                 "write" or "delete" (the highest level of permissions).
          open: If true, this will call `webbrowser.open` with the link that
                  is returned to request the user to grant access.
          webapp: If true, this uses the "webapp" workflow for authentication.

        Returns:
          A string containing the URL a user should visit to grant access.
        """
        params = {}
        if not webapp:
            rsp: ET.Element = self.invoke('rtm.auth.getFrob', auth_token=False)
            self.token = None
            efrob = rsp.find('frob')
            assert efrob is not None
            params['frob'] = self.frob = efrob.text or ''

        param_pairs = self.sign_params(perms=perms, **params)
        url = self.AUTH_URL + '?' + urllib.parse.urlencode(param_pairs)

        if open:
            if webapp:
                raise ValueError('cannot use "open" and "webapp" together')
            webbrowser.open(url)

        return url

    def finish_auth(self) -> None:
        """Finish the authentication process.

        This should be called after start_auth, after the user has granted
        access to their account.
        """
        if not self.frob:
            raise RuntimeError('must call start_auth first')
        resp: ET.Element = self.invoke(
            'rtm.auth.getToken', frob=self.frob, auth_token=False
        )
        token = resp.find('auth/token')
        assert token is not None
        self.token = token.text
        self.whoami = Identity.from_response(resp)
