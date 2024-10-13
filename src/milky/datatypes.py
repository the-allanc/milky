"""Common datastructures used by Milky."""
from __future__ import annotations

import abc
import enum

from dataclasses import dataclass
from typing import TYPE_CHECKING

from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from collections.abc import Sequence

    from milky.root import Milky


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

    def __getitem__(self, name: str) -> str:
        subpath, _, attr = name.rpartition('/')
        element = self.element
        if subpath and (element := element.find(subpath)) is None:
            raise KeyError(name)

        if not attr:
            return element.text
        if attr in element.attrib:
            return element.attrib[attr]
        if (element := element.find(attr)) is not None:
            return element.text
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
        return self.element.text

    def __str__(self) -> str:
        return ET.tostring(self.element, encoding='unicode')


class Action(enum.Enum):
    """Indicates what type of action we want to perform with RTM - a
    read-only operation (READ), a write operation (WRITE), or a write
    operation that performs an update to an existing object (UPDATE)."""

    READ = enum.auto()
    WRITE = enum.auto()
    UPDATE = enum.auto()


class Crate(abc.ABC):
    """Base class which represents a RTM object that pulls its information
    from a XML element."""

    bottle_class = Bottle

    def __init__(self, milky: Milky, bottle: ET.Element | Bottle):
        """
        Construct a Crate object.

        Args:
            milky: Milky object that the object should be attached to.
            bottle: The XML element which describes the object.
        """
        self.milky = milky
        if isinstance(bottle, ET.Element):
            bottle = self.bottle_class(bottle)
        elif type(bottle) is self.bottle_class:
            pass
        elif isinstance(bottle, Bottle):
            bottle = self.bottle_class(bottle.element)
        else:
            raise ValueError(type(bottle))
        self.bottle = bottle

    def __call__(
        self, method: str, action: Action, /, **params: bool | int | str
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
    @abc.abstractmethod
    def identity(self) -> dict[str, str | int | bool]:
        """
        Return a dictionary of key-value pairs that are needed to
        identify this object when making calls to RTM.
        """
