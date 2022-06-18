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
