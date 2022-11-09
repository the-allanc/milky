from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from milky.transport import ElementTree


@dataclass
class Bottle:

    element: ElementTree.Element

    def __post_init__(self):
        assert isinstance(self.element, ElementTree.Element), type(self.element)

    def __getitem__(self, name: str) -> str:
        subpath, _, attr = name.rpartition('/')
        element = self.element
        if subpath and (element := element.find(subpath)) is None:
            raise KeyError(name)

        if not attr:
            return element.text
        elif attr in element.attrib:
            return element.attrib[attr]
        elif (element := element.find(attr)) is not None:
            return element.text
        else:
            raise KeyError(name)

    def __getattr__(self, name: str) -> str:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def one(self, name: str) -> Bottle:
        if (result := self.first(name)) is None:
            raise ValueError(name)
        return result

    def first(self, name: str) -> Optional[Bottle]:
        if res := self.element.find(name):
            return Bottle(res)
        return None

    def all(self, name: str) -> Sequence[Bottle]:
        return [Bottle(r) for r in self.element.findall(name)]

    @property
    def text(self):
        return self.element.text

    def __str__(self) -> str:
        return ElementTree.tostring(self.element, encoding='unicode')
