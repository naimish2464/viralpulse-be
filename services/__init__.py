"""Pipeline and domain services (lazy ``run_pipeline`` to avoid import cycles)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ("run_pipeline",)


def __getattr__(name: str) -> Any:
    if name == "run_pipeline":
        from services.pipeline import run_pipeline as rp

        return rp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()))
