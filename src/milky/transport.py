from cached_property import cached_property
from dataclasses import dataclass
from xml.etree import ElementTree
import contextlib
import hashlib
import milky
import urllib.parse
import webbrowser

_client_maker = lambda: None
for _mod, _clazz in [('httpx', 'Client'), ('requests', 'Session')]:
    try:
        _client_maker = getattr(__import__(_mod), _clazz)
        break
    except ImportError:
        pass # Try the next one.
del _mod, _clazz


class ResponseError(Exception):

    def __init__(self, response, code, message):
        super().__init__(code, message)
        self.code = code
        self.message = message
        self.response = response

    def __str__(self):
        return f'{self.code}: {self.message}'


@dataclass(frozen=True)
class Identity:
    username: str
    perms: str
    user_id: int
    fullname: str

    def __str__(self):
        return f'"{self.username}" with {self.perms} permissions'

    @classmethod
    def from_response(cls, resp):
        u = resp.find('auth/user').attrib
        return Identity(
            perms=resp.find('auth/perms').text,
            user_id=int(u['id']),
            username=u['username'],
            fullname=u['fullname'],
        )



class Transport:

    AUTH_URL = 'https://api.rememberthemilk.com/services/auth/'
    REST_URL = 'https://api.rememberthemilk.com/services/rest/'
    frob = None

    def __init__(self, api_key, secret, token=None, client=None):
        self.api_key = api_key
        self.secret = secret
        self._token = token

        # Try to create a client if one isn't given.
        if not client:
            if client := _client_maker():
                hdrs = client.headers
                hdrs['User-Agent'] = f"{hdrs['User-Agent']} milky/{milky.__version__}"
            else:
                err = 'cannot import "httpx" or "requests" to create client'
                raise RuntimeError(err)            

        self.client = client

    def invoke(self, method, **kwargs):
        if kwargs.get('auth_token') is False:
            del kwargs['auth_token']
        elif not self.token:
            raise RuntimeError('token is required')
        else:
            kwargs.setdefault('auth_token', self.token)

        kwargs.setdefault('v', 2)
        is_json = kwargs.get('format') == 'json'

        kwargs = self.sign_params(method=method, **kwargs)

        resp = self.client.get(self.REST_URL, params=kwargs, headers={"cache-control": "no-cache"})
        resp.raise_for_status()

        err = None

        if is_json:
            result = resp.json()
            if result['rsp']['stat'] == 'fail':
                err = result['rsp']['err']
        else:
            result = ElementTree.fromstring(resp.text)
            if result.get('stat') == 'fail':
                err = result.find('err')

        if err is not None:
            raise ResponseError(result, int(err.get('code')), err.get('msg'))

        return result

    def sign_params(self, **params):
        params.setdefault('api_key', self.api_key)
        param_pairs = tuple(sorted(params.items()))
        paramstr = ''.join(f'{k}{v}' for (k, v) in param_pairs)
        payload = f'{self.secret}{paramstr}'
        sig = hashlib.md5(payload.encode('utf-8')).hexdigest()
        return param_pairs + (('api_sig', sig),)

    def __autoauth(self):
        if (not self._token) and self.frob:
            self.finish_auth()
            return True
        return False

    @property
    def token(self):
        self.__autoauth()
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        with contextlib.suppress(AttributeError):
            del self.frob
        with contextlib.suppress(AttributeError):
            del self.whoami

    def __check_token(self):
        if not self._token:
            return None
        try:
            return self.invoke('rtm.auth.checkToken')
        except ResponseError as e:
            if e.code == 98:
                return None
            raise

    @cached_property
    def whoami(self):
        # If auto-authentication kicked in, then the cached result
        # will already be written.
        if self.__autoauth():
            return self.whoami
        if token := self.__check_token():
            return Identity.from_response(token)

    @property
    def authed(self):
        # Handle the auto-authentication workflow.
        try:
            if self.__autoauth():
                return True
        except ResponseError as e:
            if e.code == 101: # Invalid or unauthenticated frob.
                return False
            raise

        res = self.__check_token()
        self.whoami = Identity.from_response(res) if res else None
        return bool(res)

    def start_auth(self, perms='read', open=False, webapp=False):
        params = {}
        if not webapp:
            rsp = self.invoke('rtm.auth.getFrob', auth_token=False)
            self.token = None
            params['frob'] = self.frob = rsp.find('frob').text

        params = self.sign_params(perms=perms, **params)
        url = self.AUTH_URL + '?' + urllib.parse.urlencode(params)

        if open:
            if webapp:
                raise ValueError('cannot use "open" and "webapp" together')
            webbrowser.open(url)

        return url

    def finish_auth(self):
        if not self.frob:
            raise RuntimeError('must call start_auth first')
        resp = self.invoke('rtm.auth.getToken', frob=self.frob, auth_token=False)
        self.token = resp.find('auth/token').text
        self.whoami = Identity.from_response(resp)
