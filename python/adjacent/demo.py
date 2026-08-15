"""Direct Tk Canvas frontend for Adjacent.

Unlike the Matplotlib examples, this uses Tk's native mouse event loop and canvas
drawing primitives. Run with ``--bezier`` for the spline editor.
"""

import argparse
import tkinter as tk

from . import _adjacent as adjacent
from ._adjacent import constraints


class CanvasView:
    width = 900
    height = 650
    scale = 100.0
    origin_x = 170.0
    origin_y = 510.0

    def __init__(self, root, title):
        self.root = root
        root.title(title)
        self.canvas = tk.Canvas(root, width=self.width, height=self.height, bg="#f8fafc")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status = tk.StringVar()
        tk.Label(root, textvariable=self.status, anchor="w", padx=8, pady=5).pack(fill=tk.X)
        self.selected = None
        self.last_result = adjacent.SolveResult.OKAY
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def to_screen(self, point):
        return self.origin_x + point[0] * self.scale, self.origin_y - point[1] * self.scale

    def to_world(self, x, y):
        return (x - self.origin_x) / self.scale, (self.origin_y - y) / self.scale

    def draw_background(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        spacing = self.scale
        x = self.origin_x % spacing
        while x < width:
            self.canvas.create_line(x, 0, x, height, fill="#e2e8f0")
            x += spacing
        y = self.origin_y % spacing
        while y < height:
            self.canvas.create_line(0, y, width, y, fill="#e2e8f0")
            y += spacing
        self.canvas.create_line(0, self.origin_y, width, self.origin_y, fill="#94a3b8")
        self.canvas.create_line(self.origin_x, 0, self.origin_x, height, fill="#94a3b8")

    def draw_handle(self, position, color, radius=8):
        x, y = self.to_screen(position)
        self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                fill=color, outline="white", width=2)

    def pick(self, event):
        positions = self.draggable_positions()
        if not positions:
            return None
        distances = []
        for position in positions:
            x, y = self.to_screen(position)
            distances.append((x-event.x) ** 2 + (y-event.y) ** 2)
        index = min(range(len(distances)), key=distances.__getitem__)
        return index if distances[index] <= 18**2 else None

    def on_press(self, event):
        self.selected = self.pick(event)
        if self.selected is not None:
            self.canvas.configure(cursor="fleur")

    def on_motion(self, event):
        if self.selected is None:
            return
        x, y = self.to_world(event.x, event.y)
        self.last_result = self.sketch.drag_point(self.draggable_points[self.selected], x, y)
        self.redraw()

    def on_release(self, _event):
        self.selected = None
        self.canvas.configure(cursor="")


class RectangleView(CanvasView):
    def __init__(self, root):
        self.draggable_points = [
            adjacent.Point(0.0, 0.0), adjacent.Point(4.0, 0.0),
            adjacent.Point(4.0, 3.0), adjacent.Point(0.0, 3.0),
        ]
        self.lines = [adjacent.Line(self.draggable_points[i], self.draggable_points[(i+1) % 4])
                      for i in range(4)]
        self.sketch = adjacent.Sketch()
        for line in self.lines:
            self.sketch.add_entity(line)
        self.sketch.add_constraint(constraints.FixedPoint(self.draggable_points[0]))
        self.sketch.add_constraint(constraints.HV(self.lines[0], constraints.HVOrientation.OX))
        self.sketch.add_constraint(constraints.HV(self.lines[2], constraints.HVOrientation.OX))
        self.sketch.add_constraint(constraints.HV(self.lines[1], constraints.HVOrientation.OY))
        self.sketch.add_constraint(constraints.HV(self.lines[3], constraints.HVOrientation.OY))
        self.sketch.update()
        super().__init__(root, "Adjacent — direct constraint manipulation")
        self.redraw()

    def draggable_positions(self):
        return [point.eval() for point in self.draggable_points]

    def redraw(self):
        self.draw_background()
        points = self.draggable_positions()
        screen = [self.to_screen(point) for point in points + [points[0]]]
        coordinates = [coordinate for point in screen for coordinate in point]
        self.canvas.create_line(*coordinates, fill="#334155", width=3)
        for index, point in enumerate(points):
            self.draw_handle(point, "#64748b" if index == 0 else "#0284c7")
        self.status.set(f"Blue points are draggable; gray point is fixed  |  "
                        f"{self.last_result.name}  |  DOF {self.sketch.degrees_of_freedom()}")


class BezierView(CanvasView):
    def __init__(self, root):
        self.draggable_points = [
            adjacent.Point(0.0, 0.0), adjacent.Point(1.0, 3.0),
            adjacent.Point(4.0, 3.0), adjacent.Point(5.0, 0.0),
        ]
        self.curve = adjacent.CubicBezier(*self.draggable_points)
        self.sketch = adjacent.Sketch()
        self.sketch.add_entity(self.curve)
        self.sketch.update()
        super().__init__(root, "Adjacent — cubic Bezier editor")
        self.redraw()

    def draggable_positions(self):
        return [point.eval() for point in self.draggable_points]

    def redraw(self):
        self.draw_background()
        controls = self.draggable_positions()
        hull = [self.to_screen(point) for point in controls]
        hull_coordinates = [coordinate for point in hull for coordinate in point]
        self.canvas.create_line(*hull_coordinates, fill="#94a3b8", dash=(5, 4), width=2)
        samples = [self.to_screen(self.curve.eval(i / 120.0)) for i in range(121)]
        curve_coordinates = [coordinate for point in samples for coordinate in point]
        self.canvas.create_line(*curve_coordinates, fill="#2563eb", width=4, smooth=False)
        for point in controls:
            self.draw_handle(point, "#f97316")
        # This is a computed marker, not another solver entity. Keeping it derived
        # prevents an under-constrained point-on-curve equation from distributing a
        # dragged handle's motion over all four control points.
        self.draw_handle(self.curve.eval(0.5), "#16a34a", radius=7)
        self.status.set(f"Drag orange control points; green marker is P(0.5)  |  "
                        f"length {self.curve.length():.3f}  |  DOF {self.sketch.degrees_of_freedom()}")


def _run(view):
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise SystemExit(f"Could not open a GUI display: {error}") from error
    view(root)
    root.mainloop()


def rectangle_main():
    _run(RectangleView)


def bezier_main():
    _run(BezierView)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bezier", action="store_true", help="open the cubic Bezier editor")
    args = parser.parse_args()
    bezier_main() if args.bezier else rectangle_main()


if __name__ == "__main__":
    main()
