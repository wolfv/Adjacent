"""A small constraint-based 2D CAD editor built on Adjacent and Tk Canvas."""

from dataclasses import dataclass
import math
import tkinter as tk
from tkinter import messagebox, simpledialog

from . import _adjacent as adjacent
from ._adjacent import constraints


@dataclass
class EntityRecord:
    kind: str
    object: object
    name: str


class CadApp:
    scale = 80.0
    origin_x = 180.0
    origin_y = 520.0

    def __init__(self, root):
        self.root = root
        root.title("Adjacent CAD")
        root.geometry("1100x760")
        self.sketch = adjacent.Sketch()
        self.points = []
        self.entities = []
        self.constraints = []
        self.tool = "select"
        self.pending = []
        self.selected_point = None
        self.selected_entity = None
        self.dragging = None
        self.counter = 0

        toolbar = tk.Frame(root, padx=5, pady=5, bg="#e2e8f0")
        toolbar.pack(side=tk.LEFT, fill=tk.Y)
        self.add_group(toolbar, "Create", [
            ("Select / drag", "select"), ("Point", "point"), ("Line", "line"),
            ("Circle", "circle"), ("Cubic Bézier", "bezier"),
        ])
        self.add_group(toolbar, "Constrain", [
            ("Fix point", "fixed"), ("Coincident", "coincident"),
            ("Point on curve", "point_on"), ("Horizontal", "horizontal"),
            ("Vertical", "vertical"), ("Distance", "distance"),
            ("Length", "length"), ("Diameter", "diameter"),
            ("Parallel", "parallel"), ("Perpendicular", "perpendicular"),
            ("Angle", "angle"), ("Equal length", "equal_length"),
            ("Equal radius", "equal_radius"), ("Midpoint", "midpoint"),
            ("Concentric", "concentric"), ("Tangent", "tangent"),
        ])
        tk.Button(toolbar, text="New sketch", command=self.new_sketch).pack(fill=tk.X, pady=(12, 2))

        right = tk.Frame(root)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(right, text="Constraints", font=("TkDefaultFont", 10, "bold")).pack(pady=(8, 2))
        self.constraint_list = tk.Listbox(right, width=27, height=30)
        self.constraint_list.pack(fill=tk.BOTH, expand=True, padx=6)

        center = tk.Frame(root)
        center.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(center, bg="#f8fafc", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status = tk.StringVar()
        tk.Label(center, textvariable=self.status, anchor="w", padx=8, pady=6).pack(fill=tk.X)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        root.bind("<Escape>", lambda _event: self.cancel())
        self.set_tool("select")

    def add_group(self, parent, title, tools):
        tk.Label(parent, text=title, bg="#e2e8f0", font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w", pady=(6, 2))
        for label, tool in tools:
            tk.Button(parent, text=label, width=16, anchor="w",
                      command=lambda value=tool: self.set_tool(value)).pack(fill=tk.X, pady=1)

    def set_tool(self, tool):
        self.tool = tool
        self.pending.clear()
        self.dragging = None
        hints = {
            "select": "Click an entity to select it; drag point handles",
            "point": "Click to place a point", "line": "Click two endpoints",
            "circle": "Click center, then a point on the rim",
            "bezier": "Click four control points",
            "fixed": "Select a point", "coincident": "Select two points",
            "point_on": "Select a point, then a curve", "horizontal": "Select a line",
            "vertical": "Select a line", "distance": "Select two points",
            "length": "Select a curve", "diameter": "Select a circle",
            "parallel": "Select two lines", "perpendicular": "Select two lines",
            "angle": "Select two lines", "equal_length": "Select two curves",
            "equal_radius": "Select two circles", "midpoint": "Select a point, then a line",
            "concentric": "Select two circles", "tangent": "Select two curves",
        }
        self.status.set(hints.get(tool, tool) + "  •  Esc cancels")
        self.redraw()

    def new_sketch(self):
        if self.entities and not messagebox.askyesno("New sketch", "Discard the current sketch?"):
            return
        self.sketch = adjacent.Sketch()
        self.points.clear(); self.entities.clear(); self.constraints.clear(); self.pending.clear()
        self.constraint_list.delete(0, tk.END)
        self.selected_point = self.selected_entity = None
        self.set_tool("select")

    def next_name(self, prefix):
        self.counter += 1
        return f"{prefix}{self.counter}"

    def to_world(self, x, y):
        return (x-self.origin_x)/self.scale, (self.origin_y-y)/self.scale

    def to_screen(self, point):
        return self.origin_x+point[0]*self.scale, self.origin_y-point[1]*self.scale

    def add_point(self, x, y):
        point = adjacent.Point(float(x), float(y))
        self.points.append(point)
        self.entities.append(EntityRecord("point", point, self.next_name("P")))
        self.sketch.add_entity(point)
        return point

    def point_near(self, event, required=False):
        if not self.points:
            return None
        distances = []
        for point in self.points:
            x, y = self.to_screen(point.eval())
            distances.append((x-event.x)**2 + (y-event.y)**2)
        index = min(range(len(distances)), key=distances.__getitem__)
        if required or distances[index] <= 15**2:
            return self.points[index]
        return None

    @staticmethod
    def segment_distance(p, a, b):
        dx, dy = b[0]-a[0], b[1]-a[1]
        denominator = dx*dx + dy*dy
        t = 0.0 if denominator == 0 else max(0.0, min(1.0,
            ((p[0]-a[0])*dx + (p[1]-a[1])*dy)/denominator))
        return math.hypot(p[0]-(a[0]+t*dx), p[1]-(a[1]+t*dy))

    def entity_distance(self, record, world):
        obj = record.object
        if record.kind == "line":
            return self.segment_distance(world, obj.source().eval(), obj.target().eval())
        if record.kind == "circle":
            return abs(math.dist(world, obj.center().eval()) - obj.radius().eval())
        if record.kind == "bezier":
            samples = [obj.eval(i/40) for i in range(41)]
            return min(self.segment_distance(world, samples[i], samples[i+1]) for i in range(40))
        return float("inf")

    def entity_near(self, event, allowed=None):
        world = self.to_world(event.x, event.y)
        candidates = [record for record in self.entities
                      if record.kind != "point" and (allowed is None or record.kind in allowed)]
        if not candidates:
            return None
        record = min(candidates, key=lambda item: self.entity_distance(item, world))
        return record if self.entity_distance(record, world)*self.scale <= 12 else None

    def point_for_creation(self, event):
        return self.point_near(event) or self.add_point(*self.to_world(event.x, event.y))

    def on_press(self, event):
        if self.tool == "select":
            point = self.point_near(event)
            if point is not None:
                self.selected_point, self.selected_entity, self.dragging = point, None, point
            else:
                self.selected_point, self.selected_entity = None, self.entity_near(event)
            self.redraw(); return
        if self.tool in {"point", "line", "circle", "bezier"}:
            self.creation_click(event); return
        self.constraint_click(event)

    def creation_click(self, event):
        if self.tool == "point":
            self.add_point(*self.to_world(event.x, event.y)); self.solve(); return
        if self.tool == "circle" and self.pending:
            center = self.pending[0]
            radius = math.dist(center.eval(), self.to_world(event.x, event.y))
            if radius < 1e-6:
                self.pending.clear(); messagebox.showerror("Circle", "Radius must be non-zero"); return
            obj = adjacent.Circle(center, adjacent.Param(self.next_name("r"), radius))
            self.entities.append(EntityRecord("circle", obj, self.next_name("C")))
            self.sketch.add_entity(obj)
            self.pending.clear(); self.solve(); return
        point = self.point_for_creation(event)
        self.pending.append(point)
        required = {"line": 2, "circle": 2, "bezier": 4}[self.tool]
        if len(self.pending) < required:
            self.status.set(f"{self.tool}: choose point {len(self.pending)+1} of {required}")
            self.redraw(); return
        if self.tool == "line":
            obj = adjacent.Line(*self.pending); kind, prefix = "line", "L"
        else:
            obj = adjacent.CubicBezier(*self.pending); kind, prefix = "bezier", "B"
        self.entities.append(EntityRecord(kind, obj, self.next_name(prefix)))
        self.sketch.add_entity(obj)
        self.pending.clear(); self.solve()

    def constraint_click(self, event):
        point_steps = {
            "fixed": [True], "coincident": [True, True], "distance": [True, True],
            "point_on": [True, False], "midpoint": [True, False],
        }
        entity_types = {
            "horizontal": {"line"}, "vertical": {"line"}, "length": {"line", "bezier", "circle"},
            "diameter": {"circle"}, "parallel": {"line"}, "perpendicular": {"line"},
            "angle": {"line"}, "equal_length": {"line", "bezier", "circle"},
            "equal_radius": {"circle"}, "concentric": {"circle"},
            "tangent": {"line", "circle", "bezier"}, "point_on": {"line", "circle", "bezier"},
            "midpoint": {"line"},
        }
        steps = point_steps.get(self.tool)
        wants_point = steps[len(self.pending)] if steps and len(self.pending) < len(steps) else False
        picked = self.point_near(event) if wants_point else self.entity_near(event, entity_types.get(self.tool))
        if picked is None:
            self.status.set("Nothing suitable selected — try closer to the geometry"); return
        self.pending.append(picked)
        needed = {"fixed": 1, "horizontal": 1, "vertical": 1, "length": 1, "diameter": 1,
                  "coincident": 2, "distance": 2, "point_on": 2, "midpoint": 2,
                  "parallel": 2, "perpendicular": 2, "angle": 2, "equal_length": 2,
                  "equal_radius": 2, "concentric": 2, "tangent": 2}[self.tool]
        if len(self.pending) < needed:
            self.status.set(f"{self.tool}: select item {len(self.pending)+1} of {needed}"); return
        self.make_constraint()

    def ask_value(self, title, prompt, initial):
        return simpledialog.askfloat(title, prompt, initialvalue=initial, parent=self.root)

    def make_constraint(self):
        p = [item.object if isinstance(item, EntityRecord) else item for item in self.pending]
        name = self.tool.replace("_", " ").title()
        try:
            if self.tool == "fixed": constraint = constraints.FixedPoint(p[0])
            elif self.tool == "coincident": constraint = constraints.Coincident(p[0], p[1])
            elif self.tool == "point_on": constraint = constraints.PointOn(p[0], p[1])
            elif self.tool == "horizontal": constraint = constraints.HV(p[0], constraints.HVOrientation.OX)
            elif self.tool == "vertical": constraint = constraints.HV(p[0], constraints.HVOrientation.OY)
            elif self.tool == "midpoint": constraint = constraints.Midpoint(p[0], p[1])
            elif self.tool == "parallel": constraint = constraints.Parallel(p[0], p[1])
            elif self.tool == "perpendicular": constraint = constraints.Perpendicular(p[0], p[1])
            elif self.tool == "equal_length": constraint = constraints.EqualLength(p[0], p[1])
            elif self.tool == "equal_radius": constraint = constraints.EqualRadius(p[0], p[1])
            elif self.tool == "concentric": constraint = constraints.Concentric(p[0], p[1])
            elif self.tool == "tangent": constraint = constraints.Tangent(p[0], p[1])
            elif self.tool == "distance":
                value = self.ask_value(name, "Distance", math.dist(p[0].eval(), p[1].eval()))
                if value is None: self.cancel(); return
                constraint = constraints.Distance(p[0], p[1], value); name += f" = {value:g}"
            elif self.tool == "length":
                value = self.ask_value(name, "Length", 1.0)
                if value is None: self.cancel(); return
                constraint = constraints.Length(p[0], value); name += f" = {value:g}"
            elif self.tool == "diameter":
                value = self.ask_value(name, "Diameter", 2*p[0].radius().eval())
                if value is None: self.cancel(); return
                constraint = constraints.Diameter(p[0], value); name += f" = {value:g}"
            elif self.tool == "angle":
                value = self.ask_value(name, "Angle in degrees", 90.0)
                if value is None: self.cancel(); return
                constraint = constraints.Angle(p[0], p[1], math.radians(value)); name += f" = {value:g}°"
            else: return
            self.sketch.add_constraint(constraint)
            result = self.sketch.update()
            if result != adjacent.SolveResult.OKAY:
                self.sketch.remove_constraint(constraint); self.sketch.update()
                messagebox.showerror("Constraint", "The constraint could not be satisfied")
            else:
                self.constraints.append(constraint)
                self.constraint_list.insert(tk.END, name)
        except Exception as error:
            messagebox.showerror("Constraint", str(error))
        self.pending.clear(); self.redraw()

    def solve(self):
        result = self.sketch.update()
        self.status.set(f"{result.name}  •  DOF {self.sketch.degrees_of_freedom()}")
        self.redraw()

    def on_motion(self, event):
        if self.dragging is None:
            return
        result = self.sketch.drag_point(self.dragging, *self.to_world(event.x, event.y))
        self.status.set(f"{result.name}  •  DOF {self.sketch.degrees_of_freedom()}")
        self.redraw()

    def on_release(self, _event):
        self.dragging = None

    def cancel(self):
        self.pending.clear(); self.dragging = None; self.set_tool("select")

    def draw_grid(self):
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        spacing = self.scale
        x = self.origin_x % spacing
        while x < width:
            self.canvas.create_line(x, 0, x, height, fill="#e2e8f0"); x += spacing
        y = self.origin_y % spacing
        while y < height:
            self.canvas.create_line(0, y, width, y, fill="#e2e8f0"); y += spacing
        self.canvas.create_line(0, self.origin_y, width, self.origin_y, fill="#94a3b8")
        self.canvas.create_line(self.origin_x, 0, self.origin_x, height, fill="#94a3b8")

    def redraw(self):
        self.draw_grid()
        selected = self.selected_entity.object if self.selected_entity else None
        for record in self.entities:
            obj = record.object
            color = "#dc2626" if obj is selected else "#1e40af"
            if record.kind == "line":
                a, b = self.to_screen(obj.source().eval()), self.to_screen(obj.target().eval())
                self.canvas.create_line(*a, *b, fill=color, width=3)
            elif record.kind == "circle":
                center = self.to_screen(obj.center().eval()); radius = obj.radius().eval()*self.scale
                self.canvas.create_oval(center[0]-radius, center[1]-radius,
                                        center[0]+radius, center[1]+radius, outline=color, width=3)
            elif record.kind == "bezier":
                samples = [self.to_screen(obj.eval(i/80)) for i in range(81)]
                coords = [value for point in samples for value in point]
                self.canvas.create_line(*coords, fill=color, width=3)
        for point in self.points:
            x, y = self.to_screen(point.eval())
            fill = "#dc2626" if point is self.selected_point else "#f97316"
            self.canvas.create_oval(x-6, y-6, x+6, y+6, fill=fill, outline="white", width=1)
        for point in self.pending:
            obj = point.object if isinstance(point, EntityRecord) else point
            if hasattr(obj, "eval") and isinstance(obj, adjacent.Point):
                x, y = self.to_screen(obj.eval())
                self.canvas.create_oval(x-10, y-10, x+10, y+10, outline="#16a34a", width=2)


def main():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise SystemExit(f"Could not open a GUI display: {error}") from error
    CadApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
