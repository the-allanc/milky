from __future__ import annotations

from typing import TYPE_CHECKING

from milky import rtmtypes
from milky.cache import cache_controlled
from milky.datatypes import Action, Bottle, DynamicCrate, SimpleCrate

if TYPE_CHECKING:
    from collections.abc import Iterator

    from milky.transport import ParamType


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
    name = rtmtypes.Str().setter('rtm.lists.setName')
    id = rtmtypes.Int()
    deleted = rtmtypes.Bool()
    locked = rtmtypes.Bool()
    archived = rtmtypes.Bool()
    position = rtmtypes.Int()
    smart = rtmtypes.Bool()
    query = rtmtypes.OptionalStr('filter').getter(default=None)

    def delete(self) -> None:
        self('rtm.lists.delete', Action.UPDATE)

    @property
    def identity(self) -> dict[str, ParamType]:
        return {'list_id': self.id}


class Lists(DynamicCrate):
    def _load_content(self) -> Bottle:
        return self('rtm.lists.getList')

    def create(self, name: str, query: str | None = None) -> List:
        kwargs = {'name': name}
        if query:
            kwargs['filter'] = query
        bottle = self('rtm.lists.add', Action.WRITE, **kwargs)
        result = List(self.milky, bottle)
        self._lists.append(result)
        return result

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
