from milky import rtmtypes
from milky.datatypes import Crate


class Settings(Crate):
    timezone = rtmtypes.OptionalStr('timezone/')
    date_format = rtmtypes.Int('dateformat/')
    time_format = rtmtypes.Int('timeformat/')
    language = rtmtypes.Str('language/')
    pro = rtmtypes.Bool('pro/')
    default_due_date = rtmtypes.OptionalStr('defaultduedate/')
    default_list_id = rtmtypes.OptionalInt('defaultlist/')
