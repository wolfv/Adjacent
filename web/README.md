# Adjacent Web

Experimental native-Canvas editor backed by the C++ hyperbezier implementation compiled to WebAssembly with Emscripten.

```bash
pixi run build
pixi run serve
# open http://localhost:8000
```

Features in this branch include draggable G2 auto-splines, draggable manual hyperbezier handles, smooth/corner nodes, line and circle tools, project JSON, glyph metadata, and SVG export. The remaining native CAD constraint bindings and full font compilation UI are intentionally tracked as subsequent work.
