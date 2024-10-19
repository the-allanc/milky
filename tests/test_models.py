import pytest
from milky import Milky, Transport

from . import has_httplib

if not has_httplib:
    pytest.skip("Requires HTTP library", allow_module_level=True)

pytestmark = pytest.mark.vcr


@pytest.fixture
def conn(t_params):
    return Milky(Transport(**t_params))


def test_settings(conn: Milky) -> None:
    s = conn.settings
    assert s.timezone == "Europe/London"
    assert s.date_format == 0
    assert s.time_format == 0
    assert s.language == 'en-GB'
    assert s.pro is False
    assert s.default_due_date == 'today'
    assert s.default_list_id is None
