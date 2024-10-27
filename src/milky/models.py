from __future__ import annotations

from milky import rtmtypes
from milky.datatypes import Bottle, DynamicCrate


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
