from rtmapi import Rtm

class Transport:

    PERM_READ = 'read'
    PERM_WRITE = 'write'
    PERM_FULL = 'delete'

    def __init__(self, api_key, secret, perms='read', token=None):
        self._api = Rtm(api_key, secret, perms, token, api_version=2)
        self._frob = None

    def invoke(self, method, **kwargs):
        self.token
        return self._api._call_method_auth(method, **kwargs)._RtmObject__element

    @property
    def token(self):
        if self._frob and not self._api.token:
            self.finish_auth()
        return self._api.token

    @token.setter
    def token(self, value):
        self._api.token = value
        self._frob = None

    @property
    def authed(self):
        return self._api.token_valid()

    def auth_link(self, open=False, webapp=False):
        if webapp:
            if open:
                raise ValueError('cannot use "open" and "webapp" together')
            return self._api.authenticate_webapp()

        url, frob = self._api.authenticate_desktop()
        self._frob = frob
        if open:
            webbrowser.open(url)
        return url

    def finish_auth(self):
        if not self._frob:
            raise RuntimeError('must call auth_link first')
        result = self._api.retrieve_token(self._frob)
        self._frob = None
        if not result:
            raise RuntimeError('could not finish auth')
