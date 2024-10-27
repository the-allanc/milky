"""Common datastructures used by Milky."""
from __future__ import annotations

import abc

import enum
from dataclasses import dataclass
from typing import Generic, overload, TYPE_CHECKING, TypeVar

from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from milky.root import Milky
    from milky.transport import ParamType


@dataclass
class Bottle:
    """Wrapper for Element objects.

    Intended to easily pick out attribute names or text content
    from the wrapped element or subelements.

    Usage:
       bottle['id'] # Returns attribute 'id' of wrapped element
       bottle.id # Same as above
       bottle['location/id'] # Returns attribute 'id' of child element 'location'
       bottle['location/country/code'] # Returns attribute 'code' from the
                                       # descendant element 'location/country'
       bottle['location/'] # Returns text of child element 'location'

    If no attribute can be found, then a Bottle instance will search for
    a child element with that tag and return the text of it.
    """

    element: ET.Element

    def __post_init__(self):
        if not isinstance(self.element, ET.Element):
            raise TypeError(type(self.element))

    def _resolve_element_and_attr(self, name: str) -> tuple[ET.Element, str]:
        subpath, _, attr = name.rpartition('/')

        element: ET.Element = self.element

        if subpath:
            if (subelement := element.find(subpath)) is None:
                raise KeyError(name)
            element = subelement

        return element, attr

    def __getitem__(self, name: str) -> str:
        element, attr = self._resolve_element_and_attr(name)

        if not attr:
            return element.text or ''
        if attr in element.attrib:
            return element.attrib[attr]
        if (subelement := element.find(attr)) is not None:
            return subelement.text or ''
        raise KeyError(name)

    def __getattr__(self, name: str) -> str:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def one(self, name: str) -> Bottle:
        """Return the only descendant element that matches the path given.

        Raises ValueError if one cannot be found.
        """
        if len(result := self.all(name)) == 1:
            return result[0]
        raise ValueError(name)

    def first(self, name: str) -> Bottle | None:
        """Return the first descendant element that matches the path given.

        Returns None otherwise.
        """
        if (res := self.element.find(name)) is not None:
            return Bottle(res)
        return None

    def all(self, name: str) -> Sequence[Bottle]:
        """Returns all of the descendant elements that match the path given."""
        return [Bottle(r) for r in self.element.findall(name)]

    @property
    def tag(self) -> str:
        """The name of the tag."""
        return self.element.tag

    @property
    def text(self) -> str:
        """The text of the element itself."""
        return self.element.text or ''

    def __str__(self) -> str:
        return ET.tostring(self.element, encoding='unicode')


class Action(enum.Enum):
    """Indicates what type of action we want to perform with RTM - a
    read-only operation (READ), a write operation (WRITE), or a write
    operation that performs an update to an existing object (UPDATE)."""

    READ = enum.auto()
    WRITE = enum.auto()
    UPDATE = enum.auto()


class Crate:
    """Base class which represents a RTM object that pulls its information
    from a XML element."""

    bottle_class: type[Bottle] = Bottle

    def __init__(self, milky: Milky):
        """
        Construct a Crate object.

        Args:
            milky: Milky object that the object should be attached to.
        """
        self.milky = milky
        self._bottle: Bottle | None = None

    def _get_bottle(self) -> Bottle:
        assert self._bottle is not None
        return self._bottle

    def _set_bottle(self, bottle: ET.Element | Bottle) -> None:
        if isinstance(bottle, ET.Element):
            bottle = self.bottle_class(bottle)
        elif type(bottle) is self.bottle_class:
            pass
        elif isinstance(bottle, Bottle):
            bottle = self.bottle_class(bottle.element)
        else:
            raise ValueError(type(bottle))
        self._bottle = bottle

    # https://github.com/python/mypy/issues/14684
    bottle = property(_get_bottle, _set_bottle)

    def __call__(
        self, method: str, action: Action = Action.READ, /, **params: ParamType
    ) -> Bottle:
        """
        Invoke a method against this object.

        Args:
          method: The name of the RTM method to invoke (e.g "rtm.test.echo").
          action: Indicates the type of method that is being invoked.
          **params: Parameters to send for the method.

        Raises:
          RuntimeError: if authentication is required, but no token is given.
          HTTPError: if an HTTP error occurs handling the response.
          ResponseError: if RTM reports an error in the response.
        """
        params.update(self.identity)

        result = self.milky.invoke(
            method, action is not Action.READ, unwrap=True, **params
        )

        if action is Action.UPDATE:
            # Re-wrap it if we need to.
            if self.bottle_class is not Bottle:
                result = self.bottle_class(result.element)
            self.bottle = result
            return self.bottle

        return result

    @property
    def identity(self) -> dict[str, ParamType]:
        """
        Return a dictionary of key-value pairs that are needed to
        identify this object when making calls to RTM.
        """
        return {}


class SimpleCrate(Crate):
    def __init__(self, milky: Milky, bottle: ET.Element | Bottle):
        """
        Construct a Crate object with XML data.

        Args:
            milky: Milky object that the object should be attached to.
            bottle: The XML element which describes the object.
        """
        super().__init__(milky)
        Crate.bottle.fset(self, bottle)


class DynamicCrate(Crate, abc.ABC):

    """
    A crate object which will dynamically load the XML content only
    when required.
    """

    @Crate.bottle.getter
    def bottle(self) -> Bottle:
        if self._bottle is not None:
            return self._bottle

        self.bottle = bottle = self._load_content()
        return bottle

    @abc.abstractmethod
    def _load_content(self) -> Bottle:
        ...


T = TypeVar('T')


class BottleDescriptor(Generic[T]):

    loader: Callable[[str], T]

    def __init__(self, attr: str | None, loader: Callable[[str], T]) -> None:
        self.attr = attr
        self.loader = loader

    def getter(self, default: T) -> BottleDescriptor[T]:
        self.default = default
        return self

    def __set_name__(self, owner: type[Crate], name: str) -> None:
        self.attr = self.attr or name

    @overload
    def __get__(self, instance: None, owner: type[Crate]) -> BottleDescriptor[T]:
        ...

    @overload
    def __get__(self, instance: Crate, owner: type[Crate]) -> T:
        ...

    def __get__(
        self, instance: Crate | None, owner: type[Crate] | None
    ) -> BottleDescriptor | T:
        if instance is None:
            return self

        assert self.attr is not None

        try:
            value = instance.bottle[self.attr]
        except KeyError:
            if hasattr(self, 'default'):
                return self.default
            raise AttributeError(self.attr) from None
        else:
            return self.loader(value)
