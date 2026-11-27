"""A string-keyed hash table using separate chaining and Horner hashing."""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar


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

    def items(self) -> Iterator[tuple[str, Value]]:
        """Yield all key-value pairs in bucket and chain order."""
        for first_node in self._buckets:
            node = first_node
            while node is not None:
                yield node.key, node.value
                node = node.next


class _Entry(Generic[Value]):
    __slots__ = ("key", "value")

    def __init__(self, key: str, value: Value) -> None:
        self.key = key
        self.value = value


class LinearProbingHashTable(Generic[Value]):
    """A fixed-capacity string-keyed table using linear probing."""

    def __init__(self, capacity: int = 8) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self.capacity = capacity
        self._slots: list[_Entry[Value] | None] = [None] * capacity
        self._size = 0

    def _index(self, key: str) -> int:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        index = 0
        for character in key:
            index = (31 * index + ord(character)) % self.capacity
        return index

    def _find_slot(self, key: str) -> tuple[int | None, int]:
        start = self._index(key)
        for distance in range(self.capacity):
            index = (start + distance) % self.capacity
            entry = self._slots[index]
            if entry is None or entry.key == key:
                return index, distance + 1
        return None, self.capacity

    def put(self, key: str, value: Value) -> None:
        """Insert or replace a key, raising OverflowError when full."""
        index, _ = self._find_slot(key)
        if index is None:
            raise OverflowError("hash table is full")

        entry = self._slots[index]
        if entry is not None:
            entry.value = value
            return

        self._slots[index] = _Entry(key, value)
        self._size += 1

    def get(self, key: str) -> Value | None:
        """Return the value for key, or None when key is absent."""
        index, _ = self._find_slot(key)
        if index is None:
            return None
        entry = self._slots[index]
        if entry is None:
            return None
        return entry.value

    def contains(self, key: str) -> bool:
        """Return whether key is present."""
        index, _ = self._find_slot(key)
        return index is not None and self._slots[index] is not None

    def probe_count(self, key: str) -> int:
        """Return the number of slots inspected to find key or an empty slot."""
        _, probes = self._find_slot(key)
        return probes

    def __len__(self) -> int:
        return self._size

    def items(self) -> Iterator[tuple[str, Value]]:
        """Yield all occupied key-value pairs in slot order."""
        for entry in self._slots:
            if entry is not None:
                yield entry.key, entry.value
