from __future__ import annotations


class Entity[Identifier]:
    __slots__ = ("id",)

    id: Identifier

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        if self.id is None:
            return self is other
        return bool(self.id == other.id)

    def __hash__(self) -> int:
        raise TypeError("entities are mutable and therefore unhashable")
