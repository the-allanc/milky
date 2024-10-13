from pathlib import Path

import pytest
import yaml


def pytest_recording_configure(config, vcr):
    # Make response bodies readable by convert bytes to text.
    from vcr.serializers import yamlserializer as ysz

    class MyYAMLSerializer:
        def serialize(self, cassette_dict):
            for intd in cassette_dict["interactions"]:
                val = intd["response"]["body"]["string"]
                if isinstance(val, bytes):
                    intd["response"]["body"]["string"] = val.decode("utf-8")
            return ysz.serialize(cassette_dict)

        def deserialize(self, cassette_string):
            return ysz.deserialize(cassette_string)

    vcr.register_serializer("myyaml", MyYAMLSerializer())
    vcr.serializer = "myyaml"
    vcr.decode_compressed_response = True


@pytest.fixture
def vcr_config():
    # Default configuration for VCR is to strip out those parameters
    # and to force record when there are cassettes missing.
    return {
        "filter_query_parameters": ["api_key", "api_sig", "auth_token"],
        "record_mode": "once",
    }


@pytest.fixture
def t_params():
    path = Path(__file__).parent / 'credentials' / 'user.yaml'
    if not path.exists():
        return dict(api_key='APIKEY', secret='SECRET', token='TOKEN')  # noqa: S106
    with path.open() as f:
        return yaml.full_load(f)
