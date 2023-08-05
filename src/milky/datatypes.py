"""Common datastructures used by Milky."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from milky.transport import ElementTree


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

    element: ElementTree.Element

    def __post_init__(self):
        if not isinstance(self.element, ElementTree.Element):
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
        return ElementTree.tostring(self.element, encoding='unicode')
