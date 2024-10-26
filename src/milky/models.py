from __future__ import annotations

from milky import rtmtypes
from milky.datatypes import Bottle, DynamicCrate


class Settings(DynamicCrate):
    def _load_content(self) -> Bottle:
        return self.milky.invoke('rtm.settings.getList')

    timezone = rtmtypes.OptionalStr('timezone/')
    date_format = rtmtypes.Int('dateformat/')
    time_format = rtmtypes.Int('timeformat/')
    language = rtmtypes.Str('language/')
    pro = rtmtypes.Bool('pro/')
    default_due_date = rtmtypes.OptionalStr('defaultduedate/')
    default_list_id = rtmtypes.OptionalInt('defaultlist/')
