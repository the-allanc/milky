import pytest
from milky.cache import Cache, cache_controlled


def make_cache():
    c = Cache()
    c._settings = {  # noqa: SLF001
        'aa': True,
        'aa.bb': False,
        'aa.bb.cc': True,
        'dd': False,
    }
    return c


class Cacheulator:
    def __init__(self):
        self.cache = make_cache()

    @cache_controlled(None)
    def always_cached(self):
        return object()

    @cache_controlled('aa')
    def the_a(self):
        return object()

    @cache_controlled('aa.bb')
    def the_b(self):
        return object()


class Proxylator:
    def __init__(self):
        self.milky = Cacheulator()

    @cache_controlled('aa.bb.cc')
    def the_c(self):
        return object()

    @cache_controlled('dd')
    def the_d(self):
        return object()

    @cache_controlled('ee')
    def the_e(self):
        return object()


def test_main():
    c = make_cache()
    assert c['aa.bb'] is False
    assert c['aa.bb.cc'] is True
    assert str(c) == "Cache(aa=on, aa.bb=off, aa.bb.cc=on, dd=off)"

    rep = "Cache({'aa': True, 'aa.bb': False, 'aa.bb.cc': True, 'dd': False})"  # noqa: FS003
    assert repr(c) == rep

    # Switch settings.
    c['aa.bb'] = True
    c['aa.bb.cc'] = False
    assert str(c) == "Cache(aa=on, aa.bb=on, aa.bb.cc=off, dd=off)"

    with pytest.raises(KeyError):
        c['ee']

    with pytest.raises(KeyError):
        c['aa.b']

    with pytest.raises(KeyError):
        c['aa.b'] = True

    with pytest.raises(AttributeError):
        _ = c.aa.cc


def test_view():
    c = make_cache()
    aa = c.aa

    assert aa.on is True
    aa.on = False
    assert c['aa'] is False

    bb = aa.bb
    bb.on = True
    assert c['aa.bb'] is True
    assert str(bb) == "CacheView('aa.bb')"


def test_decorator():
    c = Cacheulator()
    p = Proxylator()

    # Always cached.
    assert c.always_cached is c.always_cached

    # Configured to not use cache.
    assert c.the_b is not c.the_b

    # Assigning a value to it won't stick,
    # because it isn't cacheable.
    b_val = c.the_b = object()
    assert c.the_b is not b_val

    # Configured to use cache.
    a = c.the_a
    assert a is c.the_a

    # Cache can be cleared.
    del c.the_a
    assert a is not c.the_a

    # Cache can also be assigned to.
    c.the_a = a
    assert a is c.the_a

    # Using an indirect cache.
    assert p.the_c is p.the_c
    assert p.the_d is not p.the_d

    # We should raise an error if someone has used
    # a cache key that isn't recognised.
    with pytest.raises(AttributeError):
        _ = p.the_e
