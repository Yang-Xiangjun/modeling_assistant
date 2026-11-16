"""CAD backends behind the CadBackend interface. Never imports a CAD API (rule 4)."""

from typing import Any

from drawgen.backends.base import CadBackend


def get_backend(name: str, **kwargs: Any) -> CadBackend:
    if name == "mock":
        from drawgen.backends.mock import MockBackend

        return MockBackend(**kwargs)
    if name == "nx":
        from drawgen.backends.nx import NxBackend

        return NxBackend(**kwargs)
    raise ValueError(f"unknown backend: {name}")


__all__ = ["get_backend"]
