import pytest
from milky.transport import Transport
from rtmapi import RtmRequestFailedException

class TestTransport:

    # These are all made up, but they are used consistently across the
    # cassettes (which have been manually modified).
    API_KEY = "c90238bdea098efa089dfa9bda082903"
    SECRET = "b239dabcd9109e8f"
    TOKEN = "23d0cfec20adf80e0dddcf395032851085005318"

    @pytest.mark.vcr
    def test_desktop_auth(self):
       r = Transport(self.API_KEY, self.SECRET)
       r.start_auth()
       r.finish_auth()
 
    @pytest.mark.vcr
    def test_invalid_api_key(self):
       r = Transport(self.API_KEY, self.SECRET)
       with pytest.raises(RtmRequestFailedException):
            r.start_auth()

    @pytest.mark.vcr
    def test_invalid_signature(self):
       r = Transport(self.API_KEY, self.SECRET)
       with pytest.raises(RtmRequestFailedException):
            r.start_auth()

    @pytest.mark.vcr
    def test_bad_frob(self):
       r = Transport(self.API_KEY, self.SECRET)
       r.start_auth()
       with pytest.raises(RuntimeError, match='could not finish auth'):
            r.finish_auth()

    @pytest.mark.block_network
    def test_mobile_auth(self):
        r = Transport(self.API_KEY, self.SECRET)
        r.start_auth(webapp=True)

    @pytest.mark.vcr
    def test_given_token(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        assert r.authed

    @pytest.mark.vcr
    def test_bad_token(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        assert not r.authed
        
    @pytest.mark.vcr
    def test_invoke_with_token(self):
        r = Transport(self.API_KEY, self.SECRET, self.TOKEN)
        r.invoke('rtm.test.login')
        r.invoke('rtm.time.parse', text='jun 19')

    @pytest.mark.vcr("TestTransport.test_desktop_auth.yaml", "TestTransport.test_invoke_with_token.yaml")
    def test_invoke_get_token(self):
        # Just combine auth part and then invoke.
        r = Transport(self.API_KEY, self.SECRET)
        r.start_auth()
        r.invoke('rtm.test.login')
        r.invoke('rtm.time.parse', text='jun 19')

    @pytest.mark.block_network
    def test_invoke_no_token(self):
        #should just raise an error, no request"
        r = Transport(self.API_KEY, self.SECRET)
        with pytest.raises(RuntimeError, match='token is required'):
            r.invoke('rtm.test.login')
