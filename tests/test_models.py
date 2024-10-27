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


class TestLists:

    EXPECTED_LISTS = ('Inbox', 'Work', 'Sent', 'Personal')

    def test_list_the_lists(self, conn: Milky):
        ls = conn.lists
        expected = set(self.EXPECTED_LISTS)
        assert {ll.name for ll in ls} == expected

        # Add a list via the lower-level API. Because we're using
        # caching, we don't expect to see the new list.
        conn.invoke('rtm.lists.add', timeline=True, name='Biscuit')
        assert {ll.name for ll in ls} == expected

        # Delete the cache, and the new list should be there.
        del conn.lists
        ls = conn.lists
        expected.add('Biscuit')
        assert {ll.name for ll in ls} == expected

    def test_list_attributes(self, conn: Milky):
        inbox = conn.lists['Inbox']
        assert inbox == conn.lists['Inbox']

        assert inbox.deleted is False
        assert inbox.locked is True
        assert inbox.archived is False
        assert inbox.position == -1
        assert inbox.smart is False
        assert inbox.query is None

        foobar = conn.lists['foobar']
        assert foobar.locked is False
        assert foobar.position == 0
        assert foobar.smart is True
        assert foobar.query == 'name:foo OR name:bar'
