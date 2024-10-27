from __future__ import annotations

from typing import Any

import pytest
from milky import Milky, ResponseError, Transport

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
    @pytest.fixture
    def conn(self, conn):
        conn.cache.lists.on = False
        return conn

    EXPECTED_LISTS = ('Inbox', 'Work', 'Sent', 'Personal')

    def test_list_the_lists(self, conn: Milky):
        ls = conn.lists
        expected = set(self.EXPECTED_LISTS)
        assert {ll.name for ll in ls} == expected

        # Add a list via the lower-level API. Because we're using
        # caching, we don't expect to see the new list.
        conn.invoke('rtm.lists.add', timeline=True, name='Biscuit')
        assert {ll.name for ll in ls} == expected

        # The new list should be there.
        ls = conn.lists
        expected.add('Biscuit')
        assert {ll.name for ll in ls} == expected

    def test_list_attributes(self, conn: Milky):
        clists = conn.lists
        inbox = clists['Inbox']
        assert inbox == clists['Inbox']

        assert inbox.deleted is False
        assert inbox.locked is True
        assert inbox.archived is False
        assert inbox.position == -1
        assert inbox.smart is False
        assert inbox.query is None

        foobar = clists['foobar']
        assert foobar.locked is False
        assert foobar.position == 0
        assert foobar.smart is True
        assert foobar.query == 'name:foo OR name:bar'

    def test_add_and_delete_list(self, conn: Milky):
        ls = conn.lists
        expected = set(self.EXPECTED_LISTS)
        assert {ll.name for ll in ls} == expected

        # Create two lists.
        home = ls.create('Home')
        hipri = ls.create('High Priority', query='priority:1')

        # The queries should be found.
        assert hipri.query == 'priority:1'
        assert home.query is None

        # The lists we've created should be on our own Lists object.
        expected |= {'Home', 'High Priority'}
        assert {ll.name for ll in ls} == expected

        home.delete()
        assert home.deleted is True

        # Deleting a list won't remove it from our own Lists object.
        assert {ll.name for ll in ls} == expected

        # Though deleted lists won't show up when you get them again.
        ls = conn.lists
        expected.remove('Home')
        assert {ll.name for ll in ls} == expected

    def test_add_list_fails(self, conn: Milky):
        with pytest.raises(ResponseError) as e:
            conn.lists.create('Inbox')
        assert e.value.message == "List name provided is invalid."

    def test_list_rename(self, conn: Milky):

        # Rename a list.
        ls = conn.lists
        foobar = ls['foobar']
        foobar.name = 'barfoo'
        assert foobar.name == 'barfoo'

        # Looking it up by new name should find it,
        # but not by the old one.
        assert ls['barfoo'].name == 'barfoo'
        with pytest.raises(KeyError):
            ls['foobar']
        assert ls.get('foobar') is None

        # Should be able to find the new list.
        barfoo = conn.lists['barfoo']
        assert barfoo.name == 'barfoo'

        # Just to show that we aren't just reusing the
        # same List object.
        assert foobar is not barfoo
