"""A string-keyed hash table using separate chaining and Horner hashing."""

from __future__ import annotations

from typing import Generic, TypeVar


Value = TypeVar("Value")


class _Node(Generic[Value]):
    __slots__ = ("key", "value", "next")

    def __init__(
        self,
        key: str,
        value: Value,
        next_node: _Node[Value] | None = None,
    ) -> None:
        self.key = key
        self.value = value
        self.next = next_node


class HashTable(Generic[Value]):
    """A fixed-capacity hash table with string keys and separate chaining."""

    def __init__(self, capacity: int = 8) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self.capacity = capacity
        self._buckets: list[_Node[Value] | None] = [None] * capacity
        self._size = 0

    def _index(self, key: str) -> int:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        index = 0
        for character in key:
            index = (31 * index + ord(character)) % self.capacity
        return index

    def put(self, key: str, value: Value) -> None:
        """Insert a key or replace its existing value."""
        index = self._index(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self._buckets[index] = _Node(key, value, self._buckets[index])
        self._size += 1

    def get(self, key: str) -> Value | None:
        """Return the value for key, or None when key is absent."""
        node = self._buckets[self._index(key)]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next
        return None

    def contains(self, key: str) -> bool:
        """Return whether key is present."""
        node = self._buckets[self._index(key)]
        while node is not None:
            if node.key == key:
                return True
            node = node.next
        return False

    def __len__(self) -> int:
        return self._size
