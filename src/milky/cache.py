from __future__ import annotations

from functools import partial
from typing import Any, Callable


class Cache:
    DEFAULTS = (
        ('timeline', True),
        ('timezone', True),
    )

    __slots__ = ['_settings']

    def __init__(self):
        self._settings = dict(self.DEFAULTS)

    def __getitem__(self, key: str):
        return self._settings[key]

    def __setitem__(self, key: str, value: bool):
        if key not in self._settings:
            raise KeyError(key)
        self._settings[key] = value

    def __getattr__(self, attr: str):
        if attr in self._settings or any(
            a for a in self._settings if a.startswith(attr + '.')
        ):
            return CacheView(self, attr)
        raise AttributeError(attr)

    def __str__(self):
        attrs = ((k, v and 'on' or 'off') for (k, v) in sorted(self._settings.items()))
        attrstr = ', '.join((k + '=' + v) for (k, v) in attrs)
        return f"Cache({attrstr})"

    def __repr__(self):
        return f"Cache({self._settings!r})"


class CacheView:
    __slots__ = ['cache', 'key']

    def __init__(self, cache: Cache, key: str):
        self.cache = cache
        self.key = key

    def __getattr__(self, attr: str):
        return getattr(self.cache, self.key + '.' + attr)

    @property
    def on(self) -> bool:
        return self.cache[self.key]

    @on.setter
    def on(self, value: bool) -> None:
        self.cache[self.key] = value

    def __str__(self):
        return f"CacheView({self.key!r})"


class CacheableProperty:

    name: str

    def __init__(self, location: str | None, inner: Callable):
        self.location = location
        self.inner = inner

    def __set_name__(self, owner: type, name: str):
        self.name = name

    def can_cache_on(self, instance: Any) -> bool:
        # No location means we always do it.
        if self.location is None:
            return True

        milky = getattr(instance, 'milky', instance)
        cache = milky.cache
        try:
            return bool(cache and cache[self.location])
        except KeyError:
            raise AttributeError(self.location) from None

    def __get__(self, instance: Any, owner: type):  # noqa: ANN401
        # Use cache if it exists.
        if self.name in instance.__dict__:
            return instance.__dict__[self.name]

        # See if we need to store it on the cache.
        result = self.inner(instance)

        if self.can_cache_on(instance):
            instance.__dict__[self.name] = result

        return result

    def __set__(self, instance: Any, value: Any):
        if self.can_cache_on(instance):
            instance.__dict__[self.name] = value

    def __delete__(self, instance: Any):
        if self.name in instance.__dict__:
            del instance.__dict__[self.name]


def cache_controlled(key: str | None) -> Callable:
    return partial(CacheableProperty, key)
