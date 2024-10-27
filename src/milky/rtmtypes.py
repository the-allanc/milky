from collections.abc import Callable
from typing import Protocol, TypeVar

from milky.datatypes import BottleDescriptor

T = TypeVar('T')

# Wrap a callable and allow the return type to be optional.
def _f_with_null(f: Callable[[str], T]) -> Callable[[str], T | None]:
    def load(val: str) -> T | None:
        return f(val) if val else None

    return load


class PartialPropertyProtocol(Protocol[T]):
    def __call__(self, attr: str | None = None) -> BottleDescriptor[T]:
        ...


# Partial function generator.
def _property_maker(loader: Callable[[str], T]) -> PartialPropertyProtocol[T]:
    def _partial_property(attr: str | None = None) -> BottleDescriptor[T]:
        return BottleDescriptor(attr, loader)

    return _partial_property


# Helper functions for conversion.
def _str_to_bool(val: str) -> bool:
    return bool(int(val))


__all__ = ['Str', 'Int', 'Bool', 'OptionalStr', 'OptionalInt', 'OptionalBool']

# The types.
Str = _property_maker(str)
Int = _property_maker(int)
Bool = _property_maker(_str_to_bool)

OptionalStr = _property_maker(_f_with_null(str))
OptionalInt = _property_maker(_f_with_null(int))
OptionalBool = _property_maker(_f_with_null(_str_to_bool))
