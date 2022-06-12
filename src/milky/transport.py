from xml.etree import ElementTree
import hashlib
import httpx
import milky
import urllib.parse

class RtmError(Exception): pass
class Transport:

    AUTH_URL = 'https://api.rememberthemilk.com/services/auth/'
    REST_URL = 'https://api.rememberthemilk.com/services/rest/'
    frob = None

    def __init__(self, api_key, secret, token=None, client=None):
        self.api_key = api_key
        self.secret = secret
        self._token = token

        if not client:
            client = httpx.Client()
            hdrs = client.headers
            hdrs['User-Agent'] = f"{hdrs['User-Agent']} milky/{milky.__version__}"
        self.client = client

    def invoke(self, method, **kwargs):
        if kwargs.get('auth_token') is False:
            del kwargs['auth_token']
        elif not self._token:
            raise RuntimeError('token is required')
        else:
            kwargs.setdefault('auth_token', self.token)
        if 'v' in kwargs and kwargs['v'] is None:
            del kwargs['v']
        else:
            kwargs['v'] = 2
        kwargs = self.sign_params(method=method, **kwargs)

        resp = self.client.get(self.REST_URL, params=kwargs, headers={"cache-control": "no-cache"})
        resp.raise_for_status()

        result = ElementTree.fromstring(resp.text)
        if result.get('stat') == 'fail':
            err = result.find('err')
            error = RtmError(err.get('msg'))
            error.code = int(err.get('code'))
            raise error

        return result

    def sign_params(self, **params):
        params.setdefault('api_key', self.api_key)
        param_pairs = tuple(sorted(params.items()))
        paramstr = ''.join(f'{k}{v}' for (k, v) in param_pairs)
        payload = f'{self.secret}{paramstr}'
        sig = hashlib.md5(payload.encode('utf-8')).hexdigest()
        return param_pairs + (('api_sig', sig),)

    @property
    def token(self):
        if (not self._token) and self.frob:
            self.finish_auth()
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        del self.frob

    @property
    def authed(self):
        if not self._token:
            return False
        try:
            self.invoke('rtm.auth.checkToken', v=None)
            return True
        except RtmError as e:
            if e.code == 98:
                return False
            raise

    def start_auth(self, perms='read', open=False, webapp=False):
        params = {}
        if not webapp:
            rsp = self.invoke('rtm.auth.getFrob', auth_token=False)
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
        rsp = self.invoke('rtm.auth.getToken', frob=self.frob, auth_token=False, v=None)
        self._token = rsp.find('auth/token').text
        del self.frob
