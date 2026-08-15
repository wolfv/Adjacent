"""Python interface to the Adjacent 2D constraint solver."""

from ._adjacent import *
from ._adjacent import constraints

__all__ = [name for name in globals() if not name.startswith("_")]
