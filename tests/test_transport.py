import httpx
import pytest
import requests
from milky.transport import Transport, ResponseError

class TestTransport:

    # These are all made up, but they are used consistently across the
    # cassettes (which have been manually modified).
    API_KEY = "c90238bdea098efa089dfa9bda082903"
    SECRET = "b239dabcd9109e8f"
    TOKEN = "23d0cfec20adf80e0dddcf395032851085005318"
    AUTH_URL = f"https://api.rememberthemilk.com/services/auth/?api_key={API_KEY}"

    @pytest.mark.vcr
    def test_desktop_auth(self):
        FROB = "85cfb0d6aece75f477f99c1afe4b8d006977244e"
        SIG = "4c4d26f4445c2740b08b74f566560277"
        r = Transport(self.API_KEY, self.SECRET)
        url = r.start_auth("write")
        r.finish_auth()
        assert url == f"{self.AUTH_URL}&frob={FROB}&perms=write&api_sig={SIG}"

    @pytest.mark.vcr
    def test_invalid_api_key(self):
        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(ResponseError):
            r.start_auth()

    @pytest.mark.vcr
    def test_invalid_signature(self):
        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(ResponseError):
            r.start_auth()

    @pytest.mark.vcr
    def test_bad_frob(self):
        r = Transport(self.API_KEY, self.SECRET)
        r.start_auth()
        with pytest.raises(ResponseError, match="101: Invalid frob - did you authenticate?"):
            r.finish_auth()

    @pytest.mark.block_network
    def test_mobile_auth(self):
        SIG = "53a81b6a80e7f6319dd3f30b623a1f2c"
        r = Transport(self.API_KEY, self.SECRET)
        url = r.start_auth(perms="delete", webapp=True)
        assert url == f"{self.AUTH_URL}&perms=delete&api_sig={SIG}"

    @pytest.mark.vcr
    def test_given_token(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        assert r.authed

    @pytest.mark.vcr
    def test_given_token_json(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        result = r.invoke('rtm.auth.checkToken', format='json')
        assert result['rsp']['auth']['perms'] == 'read'

    @pytest.mark.vcr
    def test_bad_token(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        assert not r.authed

    @pytest.mark.parametrize('client', [None, 'requests.Session', 'httpx.Client'])
    @pytest.mark.vcr(
        "TestTransport.test_bad_token.yaml",
    )
    def test_bad_token_xml(self, client):
        if client is not None:
            client = client.split('.')
            client = getattr(__import__(client[0]), client[1])()
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN, client=client)
        with pytest.raises(ResponseError, match='98: Login failed / Invalid auth token') as e:
            r.invoke('rtm.auth.checkToken')
        assert e.value.code == 98
        assert e.value.response.get('stat') == 'fail'

    @pytest.mark.vcr
    def test_bad_token_json(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        with pytest.raises(ResponseError, match='98: Login failed / Invalid auth token') as e:
            r.invoke('rtm.auth.checkToken', format='json')
        assert e.value.code == 98
        assert e.value.response['rsp']['stat'] == 'fail'

    @pytest.mark.vcr
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

    @pytest.mark.block_network
    def test_invoke_no_token(self):
        # should just raise an error, no request"
        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(RuntimeError, match="token is required"):
            r.invoke("rtm.test.login")
