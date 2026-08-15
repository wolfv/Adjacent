"""Native Adjacent hyperbezier API.

The implementation lives in ``libadjacent`` and is shared by Python and the
Emscripten/WASM build. Its mathematics is adapted from linebender/spline,
Copyright (c) 2020 Raph Levien; see HYPERBEZIER_LICENSE-MIT.
"""

from ._adjacent import AutoHyperSpline, HyperBezier, HyperBezierResult, HyperSegment

__all__ = ["AutoHyperSpline", "HyperBezier", "HyperBezierResult", "HyperSegment"]
