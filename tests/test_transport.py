import pytest
from rtmapi import Rtm

class TestTransport:

    # These are all made up, but they are used consistently across the
    # cassettes (which have been manually modified).
    API_KEY = "c90238bdea098efa089dfa9bda082903"
    SECRET = "b239dabcd9109e8f"
    TOKEN = "23d0cfec20adf80e0dddcf395032851085005318"

    @pytest.mark.vcr
    def test_desktop_auth(self):
       r = Rtm(self.API_KEY, self.SECRET, 'write', api_version=2)
       url, frob = r.authenticate_desktop()
       r.retrieve_token(frob)
 
    @pytest.mark.vcr
    def test_invalid_api_key(self):
       r = Rtm(self.API_KEY, self.SECRET, 'read', api_version=2)
       url, frob = r.authenticate_desktop()

    @pytest.mark.vcr
    def test_invalid_signature(self):
       r = Rtm(self.API_KEY, self.SECRET, 'delete', api_version=2)
       url, frob = r.authenticate_desktop()

    @pytest.mark.vcr
    def test_bad_frob(self):
       r = Rtm(self.API_KEY, self.SECRET, 'write', api_version=2)
       url, frob = r.authenticate_desktop()
       r.retrieve_token(frob)

    @pytest.mark.block_network
    def test_mobile_auth(self):
        "todo"

    @pytest.mark.vcr
    def test_given_token(self):
        r = Rtm(self.API_KEY, self.SECRET, 'read', api_version=2, token=self.TOKEN)
        assert r.token_valid()

    @pytest.mark.vcr
    def test_bad_token(self):
        r = Rtm(self.API_KEY, self.SECRET, 'write', api_version=2, token=self.TOKEN)
        assert not r.token_valid()
        
    @pytest.mark.vcr
    def test_invoke_with_token(self):
        r = Rtm(self.API_KEY, self.SECRET, 'delete', api_version=2, token=self.TOKEN)
        r._call_method_auth('rtm.test.login')
        r._call_method_auth('rtm.time.parse', text='jun 19')

    @pytest.mark.vcr
    def test_invoke_get_token(self):
        # Just combine auth part and then invoke.
        pass

    @pytest.mark.block_network
    def test_invoke_no_token(self):
        #should just raise an error, no request"
        pass