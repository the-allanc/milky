import types

import pytest
from milky.transport import ResponseCodes, ResponseError, Transport

has_ = types.SimpleNamespace()

for module in ['requests', 'httpx']:
    try:
        __import__(module)
        setattr(has_, module, True)
    except ImportError: # noqa: PERF203
        setattr(has_, module, False)
del module, types


class Settings:

    # These are all made up, but they are used consistently across the
    # cassettes (which have been manually modified).
    API_KEY = "c90238bdea098efa089dfa9bda082903"
    SECRET = "b239dabcd9109e8f"  # noqa: S105
    TOKEN = "23d0cfec20adf80e0dddcf395032851085005318"  # noqa: S105
    AUTH_URL = f"https://api.rememberthemilk.com/services/auth/?api_key={API_KEY}"


class TestClient(Settings):
    @pytest.mark.skipif(not has_.httpx, reason='needs httpx')
    @pytest.mark.skipif(has_.requests, reason='requests is installed')
    @pytest.mark.vcr('TestClient.test_server_error.yaml')
    def test_server_error_httpx(self):
        from httpx import HTTPStatusError

        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(HTTPStatusError, match="Server error '500 Not OK'"):
            r.start_auth()

    @pytest.mark.skipif(not has_.requests, reason='needs requests')
    @pytest.mark.skipif(has_.httpx, reason='httpx is installed')
    @pytest.mark.vcr('TestClient.test_server_error.yaml')
    def test_server_error_requests(self):
        from requests.exceptions import HTTPError

        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(HTTPError, match="500 Server Error: Not OK"):
            r.start_auth()

    @pytest.mark.skipif(has_.requests or has_.httpx, reason='needs no http lib')
    @pytest.mark.block_network()
    def test_no_httplib(self):
        msg = 'cannot import "httpx" or "requests" to create client'
        with pytest.raises(RuntimeError, match=msg):
            Transport(self.API_KEY, self.SECRET)


@pytest.mark.skipif(not (has_.requests or has_.httpx), reason='needs http lib')
class TestTransport(Settings):
    @pytest.mark.vcr()
    def test_desktop_auth(self):
        frob = "85cfb0d6aece75f477f99c1afe4b8d006977244e"
        sig = "d61c462cdf39e5ceea5c30f4997cc19f"
        r = Transport(self.API_KEY, self.SECRET)
        assert not r.authed

        url = r.start_auth("delete")
        r.finish_auth()
        assert url == f"{self.AUTH_URL}&frob={frob}&perms=delete&api_sig={sig}"

        # We should have the identity stored.
        me = r.whoami
        assert me.username == 'money.mark'
        assert me.perms == 'delete'

    @pytest.mark.vcr()
    def test_invalid_api_key(self):
        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(ResponseError):
            r.start_auth()

    @pytest.mark.vcr()
    def test_invalid_signature(self):
        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(ResponseError):
            r.start_auth()

    @pytest.mark.vcr()
    def test_bad_frob(self):
        r = Transport(self.API_KEY, self.SECRET)
        r.start_auth()
        with pytest.raises(
            ResponseError, match="101: Invalid frob - did you authenticate?"
        ):
            r.finish_auth()

    @pytest.mark.vcr('TestTransport.test_bad_frob.yaml')
    def test_bad_frob_authed(self):
        r = Transport(self.API_KEY, self.SECRET)
        r.start_auth()
        assert not r.authed

    @pytest.mark.vcr('TestTransport.test_bad_frob.yaml')
    def test_bad_frob_whoami(self):
        r = Transport(self.API_KEY, self.SECRET)
        r.start_auth()
        assert r.whoami is None

    @pytest.mark.block_network()
    def test_mobile_auth(self):
        sig = "53a81b6a80e7f6319dd3f30b623a1f2c"
        r = Transport(self.API_KEY, self.SECRET)
        url = r.start_auth(perms="delete", webapp=True)
        assert url == f"{self.AUTH_URL}&perms=delete&api_sig={sig}"

    @pytest.mark.vcr()
    def test_given_token(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        assert r.authed

        user_id = 7447825

        # It should have the identity set.
        me = r.whoami
        assert str(me) == '"milkymark" with write permissions'
        assert me.fullname == 'Milky Mark'
        assert me.user_id == user_id

    @pytest.mark.vcr()
    def test_given_token_json(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        result = r.invoke('rtm.auth.checkToken', format='json')
        assert result['rsp']['auth']['perms'] == 'read'

    @pytest.mark.vcr()
    def test_bad_token(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        assert not r.authed
        assert r.whoami is None  # shouldn't cause another request

    @pytest.mark.skipif(not has_.requests, reason='needs requests')
    @pytest.mark.skipif(not has_.httpx, reason='needs httpx')
    @pytest.mark.parametrize('client', [None, 'requests.Session', 'httpx.Client'])
    @pytest.mark.vcr("TestTransport.test_bad_token.yaml")
    def test_bad_token_xml(self, client):
        if client is not None:
            client = client.split('.')
            client = getattr(__import__(client[0]), client[1])()
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN, client=client)
        with pytest.raises(
            ResponseError, match='98: Login failed / Invalid auth token'
        ) as e:
            r.invoke('rtm.auth.checkToken')
        assert e.value.code == ResponseCodes.LOGIN_FAILED_OR_BAD_TOKEN.value
        assert e.value.response.get('stat') == 'fail'

    @pytest.mark.vcr()
    def test_bad_token_json(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        with pytest.raises(
            ResponseError, match='98: Login failed / Invalid auth token'
        ) as e:
            r.invoke('rtm.auth.checkToken', format='json')
        assert e.value.code == ResponseCodes.LOGIN_FAILED_OR_BAD_TOKEN.value
        assert e.value.response['rsp']['stat'] == 'fail'

    @pytest.mark.vcr(
        "TestTransport.test_given_token.yaml",
        "TestTransport.test_bad_token.yaml",
    )
    def test_whoami_cached(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        me = r.whoami
        assert me is not None
        assert me is r.whoami  # should be cached

        # Deleting it should result in it being retrieved.
        del r.whoami
        me = r.whoami
        assert me is None
        assert r.whoami is None  # still cached

    @pytest.mark.vcr(
        "TestTransport.test_given_token.yaml",
        "TestTransport.test_bad_token.yaml",
    )
    def test_authed_nocache(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)

        # No caching in place.
        assert r.authed
        assert not r.authed

    @pytest.mark.vcr()
    def test_invoke_with_token(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        resp = r.invoke("rtm.test.login")
        r.invoke("rtm.time.parse", text="jun 19")

        # Top-level element.
        assert resp.tag == 'rsp'

        # User element inside that.
        kids = list(resp)
        assert len(kids) == 1
        assert kids[0].tag == 'user'
        assert kids[0].attrib['id'] == '7447825'

        # Username element inside that.
        uname = list(kids[0])[0]
        assert uname.tag == 'username'
        assert uname.text == 'milkymark'

    @pytest.mark.vcr(
        "TestTransport.test_desktop_auth.yaml",
        "TestTransport.test_invoke_with_token.yaml",
    )
    def test_invoke_get_token(self):
        # Just combine auth part and then invoke.
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        r.start_auth("read")
        r.invoke("rtm.test.login")
        resp = r.invoke("rtm.time.parse", text="jun 19")

        # Top level element.
        assert resp.attrib['stat'] == 'ok'

        # Time element.
        time = list(resp)[0]
        assert time.attrib['precision'] == 'date'
        assert time.text == '2022-06-19T00:00:00Z'

    @pytest.mark.block_network()
    def test_invoke_no_token(self):
        # should just raise an error, no request"
        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(RuntimeError, match="token is required"):
            r.invoke("rtm.test.login")

    @pytest.mark.vcr(
        "TestTransport.test_given_token.yaml",
        "TestTransport.test_desktop_auth.yaml",
    )
    def test_invalidate_cache_on_finish_auth(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        assert str(r.whoami) == '"milkymark" with write permissions'

        r.start_auth("delete")
        assert str(r.whoami) == '"money.mark" with delete permissions'

    @pytest.mark.vcr(
        "TestTransport.test_desktop_auth.yaml",
        "TestTransport.test_given_token.yaml",
    )
    def test_invalidate_cache_on_set_token(self):
        r = Transport(self.API_KEY, self.SECRET)
        r.start_auth("delete")
        assert str(r.whoami) == '"money.mark" with delete permissions'

        r.token = self.TOKEN
        assert str(r.whoami) == '"milkymark" with write permissions'

    @pytest.mark.vcr("TestTransport.test_desktop_auth.yaml")
    def test_authed_uses_finish_auth(self):
        r = Transport(self.API_KEY, self.SECRET)
        r.start_auth("delete")
        assert r.authed
        assert r.whoami.fullname == 'Money Mark'
