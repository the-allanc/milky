from __future__ import annotations

import typing

from .cache import Cache, cache_controlled
from .datatypes import Bottle

if typing.TYPE_CHECKING:
    from .transport import ElementTree, Transport


class Milky:
    def __init__(self, transport: Transport):
        self.transport = transport
        self.cache = Cache()

    def invoke(
        self,
        method: str,
        /,
        timeline: bool | str = False,
        unwrap: bool = True,
        **kwargs: str | int | bool,
    ) -> Bottle:
        if timeline:
            kwargs['timeline'] = self.timeline if timeline is True else timeline
        res = self.transport.invoke(method, **kwargs)
        return Bottle(self._unwrap_response(res) if unwrap else res)

    @staticmethod
    def _unwrap_response(res: ElementTree) -> ElementTree:
        # If they want content, we'll have to extract it.
        if res.tag != 'rsp':
            msg = f'Response has tag "{res.element.tag}" rather than "rsp"'
            raise RuntimeError(msg)

        # We expect at most one child element which is not a transaction.
        if not (kids := [kid for kid in list(res) if kid.tag != 'transaction']):
            raise RuntimeError("no elements in response, consider using unwrap=False")
        if len(kids) > 1:
            msg = 'Response has multiple content elements, cannot select just one'
            raise RuntimeError(msg)
        return kids[0]

    @cache_controlled('timeline')
    def timeline(self) -> str:
        return self.invoke('rtm.timelines.create').text
