from milky.datatypes import BottleProperty, Crate


class Settings(Crate):
    timezone: BottleProperty = BottleProperty('timezone/')
    date_format: BottleProperty = BottleProperty('dateformat/')
    time_format: BottleProperty = BottleProperty('timeformat/')
    language: BottleProperty = BottleProperty('language/')
    pro: BottleProperty = BottleProperty('pro/')
    default_due_date: BottleProperty = BottleProperty('defaultduedate/')
    default_list_id: BottleProperty = BottleProperty('defaultlist/')
