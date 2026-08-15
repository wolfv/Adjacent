# Adjacent

A symbolic, nonlinear 2D geometric constraint solver in C++17 with Python bindings.

## Geometry and constraints

Entities: points, lines, circles, circular arcs, and cubic Bezier curves.

Constraints include coincidence, point-on-curve, point distance, point-to-line distance,
length, diameter, horizontal/vertical, parallel, perpendicular, directed angle, tangent,
equal length/radius, fixed point, midpoint, and concentricity.

The equation system uses analytic derivatives and a damped minimum-norm Newton step. It
supports under-constrained and redundant systems, reports degrees of freedom, reverts a
failed solve, and can add or remove sketch entities and constraints.

## Pixi workspace

The repository contains two independently buildable Pixi packages:

- `lib/` — `libadjacent`, the shared C++ library, headers, and CMake package.
- `python/` — `adjacent-python`, Python bindings and installed CAD applications. It
  declares `../lib` as a path dependency.

The root workspace composes both source packages. Install and test everything with:

```bash
pixi install
pixi run test
```

Build distributable Conda packages from the Pixi package manifests:

```bash
pixi run build-packages
# Equivalent individual builds:
pixi publish --path lib --target-dir dist
pixi publish --path python --target-dir dist
```

The C++ project remains usable as an installed CMake package through
`find_package(adjacent CONFIG REQUIRED)` and target `adjacent::adjacent`. For direct C++
development:

```bash
pixi run --manifest-path lib/pixi.toml test
```

## Python example

```python
import adjacent
from adjacent import constraints

p0 = adjacent.Point(0, 0)
p1 = adjacent.Point(2, 1)
line = adjacent.Line(p0, p1)

sketch = adjacent.Sketch()
sketch.add_entity(line)
sketch.add_constraint(constraints.FixedPoint(p0))
sketch.add_constraint(constraints.HV(line, constraints.HVOrientation.OX))
sketch.add_constraint(constraints.Length(line, 5))
assert sketch.update() == adjacent.SolveResult.OKAY
```

## SVG and font editor

Launch the constraint-based glyph outline editor:

```bash
pixi run font-editor
# Installed package command:
adjacent-font-editor
```

It provides multi-glyph projects, line and cubic Bézier contours, direct node/handle
editing, snapping, point constraints, contour-preserving soft stays during dragging,
panning and zooming, SVG path import/export, project save/load, glyph metrics, and
TrueType export through FontTools.

## Simple CAD editor

Create points, lines, circles, and cubic Bézier curves, drag their handles, and apply
dimensional or geometric constraints:

```bash
pixi run cad
```

Choose a creation or constraint tool in the left toolbar and follow the status-line
prompt. Supported editor constraints include fixed/coincident/point-on, horizontal and
vertical, distance/length/diameter/angle, parallel/perpendicular/tangent, equal
length/radius, midpoint, and concentricity.

## Interactive demos

Run the direct Tk Canvas GUI and drag points while the solver maintains its hard
constraints. This frontend uses native press/motion/release events rather than a plotting
library:

```bash
pixi run demo          # constrained rectangle
pixi run demo-bezier   # draggable cubic Bézier control points
pixi run demo-pelican  # constrained pelican riding a bicycle (all nodes draggable)
```

The bindings also expose `Sketch.drag_point(point, x, y)` for integration into
other GUI frameworks.

## Further roadmap

Production CAD integrations may additionally need inequality/bounded curve parameters,
constraint priorities, conflict-set diagnosis, ellipse/B-spline entities, and sparse linear
algebra for very large sketches. These are separate extensions to the implemented 2D
solver core rather than placeholders in the current API.
