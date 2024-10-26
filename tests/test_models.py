from __future__ import annotations

from typing import Any

import pytest
from milky import Milky, Transport

from . import has_httplib

if not has_httplib:
    pytest.skip("Requires HTTP library", allow_module_level=True)

pytestmark = pytest.mark.vcr


@pytest.fixture
def conn(t_params):
    return Milky(Transport(**t_params))


def test_settings(conn: Milky, vcr: Any) -> None:
    s = conn.settings

    # Accessing an attribute should force the object to be initialised.
    req_count = vcr.play_count
    assert s.timezone == "Europe/London"
    assert req_count + 1 == vcr.play_count

    assert s.date_format == 0
    assert s.time_format == 0
    assert s.language == 'en-GB'
    assert s.pro is False
    assert s.default_due_date == 'today'
    assert s.default_list_id is None

    # Ensure we're not continuously loading the object when accessing
    # other attributes.
    assert req_count + 1 == vcr.play_count
