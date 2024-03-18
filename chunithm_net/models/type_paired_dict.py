from typing import Generic, TypeVar

T = TypeVar("T")
VT = TypeVar("VT")


class TypePairedDictKey(Generic[T]):
    pass


class TypePairedDict(dict):
    """
    A `dict` subclass that types values based on their keys. The intended usage is
    something like this:

    ```python
    # Keep the key as a constant, and optionally export it so consumers can also
    # get the stored value.
    KEY_SOMETHING = TypePairedDictKey[int]()

    data = TypePairedDict()
    reveal_type(data[KEY_SOMETHING])  # should be int
    ```
    """

    def __getitem__(self, __key: TypePairedDictKey[T]) -> T:
        return super().__getitem__(__key)

    def __setitem__(self, __key: TypePairedDictKey[T], __value: T) -> None:
        return super().__setitem__(__key, __value)

    def get(self, __key: TypePairedDictKey[T]) -> T | None:  # type: ignore[reportInconsistentOverload]
        return super().get(__key)
