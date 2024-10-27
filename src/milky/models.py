from __future__ import annotations

from typing import TYPE_CHECKING

from milky import rtmtypes
from milky.cache import cache_controlled
from milky.datatypes import Bottle, DynamicCrate, SimpleCrate

if TYPE_CHECKING:
    from collections.abc import Iterator


class Settings(DynamicCrate):
    def _load_content(self) -> Bottle:
        return self('rtm.settings.getList')

    timezone = rtmtypes.OptionalStr()
    date_format = rtmtypes.Int('dateformat/')
    time_format = rtmtypes.Int('timeformat/')
    language = rtmtypes.Str()
    pro = rtmtypes.Bool()
    default_due_date = rtmtypes.OptionalStr('defaultduedate/')
    default_list_id = rtmtypes.OptionalInt('defaultlist/')


class List(SimpleCrate):
    name = rtmtypes.Str()
    id = rtmtypes.Int()
    deleted = rtmtypes.Bool()
    locked = rtmtypes.Bool()
    archived = rtmtypes.Bool()
    position = rtmtypes.Int()
    smart = rtmtypes.Bool()
    query = rtmtypes.OptionalStr('filter').getter(default=None)


class Lists(DynamicCrate):

    def _load_content(self) -> Bottle:
        return self('rtm.lists.getList')

    def get(self, name: str) -> List | None:
        for rlist in self:
            if rlist.name == name:
                return rlist
        return None

    def __getitem__(self, name: str) -> List:
        if (rlist := self.get(name)) is None:
            raise KeyError(name)
        return rlist

    @cache_controlled(None)
    def _lists(self) -> list[List]:
        return [List(self.milky, ls) for ls in self.bottle.all('list')]

    def __iter__(self) -> Iterator[List]:
        return iter(self._lists)
