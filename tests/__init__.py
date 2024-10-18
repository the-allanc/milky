import types

import pytest

has_ = types.SimpleNamespace()

for module in ['requests', 'httpx']:
    try:
        __import__(module)
        setattr(has_, module, True)
    except ImportError:  # noqa: PERF203
        setattr(has_, module, False)
del module, types

has_httplib = has_.requests or has_.httpx
needs_httplib = pytest.mark.skipif(not has_httplib, reason='needs http lib')
