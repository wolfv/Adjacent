# Adjacent Web

Experimental native-Canvas editor backed by the C++ hyperbezier implementation compiled to WebAssembly with Emscripten.

```bash
pixi run build
pixi run serve
# open http://localhost:8000
```

Features in this branch include draggable G2 auto-splines, draggable manual hyperbezier handles, smooth/corner nodes, line and circle tools, project JSON, glyph metadata, and SVG export. Hyperbezier anchors and ordinary CAD points share the same constraint sketch. CAD points, lines, circles, direct manipulation, DOF reporting, line/circle tangency, and sixteen other geometric constraint operations are bound directly to `libadjacent` in WASM. Full browser-side OpenType compilation remains subsequent work.
