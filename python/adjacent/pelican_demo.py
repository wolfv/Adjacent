"""A constrained, draggable pelican riding a bicycle.

Every blue/orange node is a solver point.  Drag one and Adjacent preserves the
geometric constraints while temporary soft stays keep the rest of the drawing
as still as possible.
"""

import math
import tkinter as tk

from . import _adjacent as adjacent
from ._adjacent import constraints


class PelicanBicycleModel:
    """Geometry and constraints, kept separate so it can be tested headlessly."""

    def __init__(self):
        self.sketch = adjacent.Sketch()
        self.points = []
        self.control_points = set()
        self.lines = []
        self.curves = []
        self.circles = []
        self.constraint_names = []

        def point(x, y, control=False):
            p = adjacent.Point(x, y)
            self.points.append(p)
            if control:
                self.control_points.add(id(p))
            return p

        def line(a, b, color="#334155", width=4):
            entity = adjacent.Line(a, b)
            self.sketch.add_entity(entity)
            self.lines.append((entity, color, width))
            return entity

        def curve(a, b, c, d, color="#475569", width=4):
            entity = adjacent.CubicBezier(a, b, c, d)
            self.sketch.add_entity(entity)
            self.curves.append((entity, color, width))
            return entity

        def circle(center, radius, color="#334155", width=4):
            entity = adjacent.Circle(center, adjacent.Param("radius", radius))
            self.sketch.add_entity(entity)
            self.circles.append((entity, color, width))
            return entity

        def constrain(name, value):
            self.sketch.add_constraint(value)
            self.constraint_names.append(name)

        # Bicycle wheels and frame.
        rear = point(2.0, 1.6)
        front = point(8.0, 1.6)
        crank = point(5.0, 1.6)
        rear_wheel = circle(rear, 1.35)
        front_wheel = circle(front, 1.35)
        wheel_axis = line(rear, front, "#94a3b8", 2)

        seat = point(3.8, 4.0)
        head = point(6.2, 4.0)
        handle = point(6.2, 5.15)
        rear_chain = line(rear, crank)
        front_chain = line(crank, front)
        rear_stay = line(rear, seat)
        seat_tube = line(seat, crank)
        top_tube = line(seat, head)
        down_tube = line(head, crank)
        fork = line(head, front)
        stem = line(head, handle)
        bar_end = point(6.75, 5.15)
        handlebar = line(handle, bar_end)
        seat_left, seat_right = point(3.45, 4.15), point(4.15, 4.15)
        saddle = line(seat_left, seat_right, "#0f172a", 7)

        pedal_a, pedal_b = point(4.55, 1.35), point(5.45, 1.85)
        crank_arm = line(pedal_a, pedal_b, "#64748b", 3)
        circle(crank, 0.30, "#64748b", 3)

        constrain("wheel centers horizontal", constraints.HV(wheel_axis, constraints.HVOrientation.OX))
        constrain("wheels have equal radius", constraints.EqualRadius(rear_wheel, front_wheel))
        constrain("crank is axle midpoint", constraints.Midpoint(crank, wheel_axis))
        constrain("chain stays equal", constraints.EqualLength(rear_chain, front_chain))
        constrain("top tube horizontal", constraints.HV(top_tube, constraints.HVOrientation.OX))
        constrain("frame stays equal", constraints.EqualLength(rear_stay, fork))
        constrain("frame diagonals equal", constraints.EqualLength(seat_tube, down_tube))
        constrain("handle stem vertical", constraints.HV(stem, constraints.HVOrientation.OY))
        constrain("handlebar horizontal", constraints.HV(handlebar, constraints.HVOrientation.OX))
        constrain("saddle horizontal", constraints.HV(saddle, constraints.HVOrientation.OX))
        constrain("pedal crank midpoint", constraints.Midpoint(crank, crank_arm))

        # Pelican body: four cubic Beziers form a plump closed silhouette.
        tail = point(2.75, 5.25)
        shoulder = point(3.75, 7.15)
        chest = point(5.25, 6.55)
        belly = point(4.65, 5.05)
        body_curves = [
            curve(tail, point(2.8, 6.35, True), point(3.05, 7.1, True), shoulder,
                  "#f8fafc", 5),
            curve(shoulder, point(4.25, 7.35, True), point(5.0, 7.05, True), chest,
                  "#f8fafc", 5),
            curve(chest, point(5.55, 6.0, True), point(5.35, 5.25, True), belly,
                  "#f8fafc", 5),
            curve(belly, point(4.0, 4.8, True), point(3.25, 4.9, True), tail,
                  "#f8fafc", 5),
        ]
        self.body_curves = body_curves

        # Long neck, head, enormous bill and pouch.
        neck_top = point(6.45, 8.45)
        neck = curve(chest, point(5.75, 7.05, True), point(5.7, 8.2, True), neck_top,
                     "#f8fafc", 6)
        crown = point(7.05, 8.75)
        head_curve = curve(neck_top, point(6.5, 8.85, True), point(6.8, 8.95, True), crown,
                           "#f8fafc", 5)
        bill_tip = point(9.35, 8.35)
        upper_bill = curve(crown, point(7.8, 8.75, True), point(8.7, 8.55, True), bill_tip,
                           "#f59e0b", 6)
        throat = point(5.95, 7.35)
        pouch = curve(bill_tip, point(8.45, 7.35, True), point(6.85, 6.9, True), throat,
                      "#f59e0b", 6)
        neck_inner = curve(throat, point(6.0, 7.75, True), point(6.0, 8.15, True), neck_top,
                           "#f8fafc", 5)
        beak_edge = line(crown, bill_tip, "#f59e0b", 2)

        eye = point(6.75, 8.62)
        eye_circle = circle(eye, 0.10, "#0f172a", 3)

        # Wing and two constrained legs resting on the top tube.
        wing_a, wing_b = point(3.25, 6.45), point(4.65, 5.65)
        wing = curve(wing_a, point(3.7, 6.75, True), point(4.55, 6.45, True), wing_b,
                     "#94a3b8", 4)
        hip_a, foot_a = point(3.95, 5.15), point(3.95, 4.0)
        hip_b, foot_b = point(4.45, 5.15), point(4.45, 4.0)
        leg_a = line(hip_a, foot_a, "#f59e0b", 4)
        leg_b = line(hip_b, foot_b, "#f59e0b", 4)

        constrain("legs vertical", constraints.HV(leg_a, constraints.HVOrientation.OY))
        constrain("legs parallel", constraints.Parallel(leg_a, leg_b))
        constrain("legs equal length", constraints.EqualLength(leg_a, leg_b))
        constrain("left foot on top tube", constraints.PointOn(foot_a, top_tube))
        constrain("right foot on top tube", constraints.PointOn(foot_b, top_tube))
        constrain("bill chord slopes with crown", constraints.Length(beak_edge, 2.37))
        constrain("eye size", constraints.Diameter(eye_circle, 0.20))

        # Keep references alive and make the intended structure discoverable.
        self.body_fill_curves = body_curves
        self.neck_fill_curves = [neck, neck_inner]
        self.bill_fill_curves = [upper_bill, pouch]
        self.named_parts = {
            "body": body_curves, "neck": [neck, neck_inner], "head": [head_curve],
            "bill": [upper_bill, pouch, beak_edge], "wing": [wing],
        }
        self.last_result = self.sketch.update()


class PelicanBicycleView:
    width, height = 1100, 760
    scale, origin_x, origin_y = 70.0, 45.0, 700.0

    def __init__(self, root):
        self.root = root
        self.model = PelicanBicycleModel()
        self.selected = None
        root.title("Adjacent — a constrained pelican on a bicycle")
        self.canvas = tk.Canvas(root, width=self.width, height=self.height, bg="#dff4ff",
                                highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status = tk.StringVar()
        tk.Label(root, textvariable=self.status, anchor="w", padx=10, pady=6).pack(fill=tk.X)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.redraw()

    def screen(self, value):
        return self.origin_x + value[0] * self.scale, self.origin_y - value[1] * self.scale

    def world(self, x, y):
        return (x - self.origin_x) / self.scale, (self.origin_y - y) / self.scale

    def positions(self):
        return [p.eval() for p in self.model.points]

    def pick(self, event):
        distances = []
        for p in self.positions():
            x, y = self.screen(p)
            distances.append((x - event.x) ** 2 + (y - event.y) ** 2)
        if not distances:
            return None
        index = min(range(len(distances)), key=distances.__getitem__)
        return index if distances[index] < 15 ** 2 else None

    def on_press(self, event):
        self.selected = self.pick(event)
        if self.selected is not None:
            self.canvas.configure(cursor="fleur")

    def on_motion(self, event):
        if self.selected is None:
            return
        x, y = self.world(event.x, event.y)
        point = self.model.points[self.selected]
        stays = [p for index, p in enumerate(self.model.points) if index != self.selected]
        self.model.last_result = self.model.sketch.drag_point_with_stays(point, x, y, stays)
        self.redraw()

    def on_release(self, _event):
        self.selected = None
        self.canvas.configure(cursor="")
        self.redraw()

    def coords(self, points):
        return [coordinate for p in points for coordinate in self.screen(p)]

    def redraw(self):
        c = self.canvas
        c.delete("all")
        width, height = c.winfo_width(), c.winfo_height()
        c.create_rectangle(0, self.origin_y - 1.35 * self.scale, width, height,
                           fill="#dcfce7", outline="")
        c.create_line(0, self.origin_y, width, self.origin_y, fill="#65a30d", width=3)
        c.create_text(830, 32, text="CONSTRAINTS", fill="#0f172a",
                      font=("TkDefaultFont", 13, "bold"), anchor="nw")
        for index, name in enumerate(self.model.constraint_names):
            c.create_text(830, 62 + index * 22, text=f"• {name}", fill="#334155", anchor="nw")

        # Filled silhouettes are sampled from the same solver-controlled curves.
        body = []
        for entity in self.model.body_fill_curves:
            body.extend(entity.eval(i / 20.0) for i in range(20))
        c.create_polygon(*self.coords(body), fill="#ffffff", outline="")
        neck_outer, neck_inner = self.model.neck_fill_curves
        neck_shape = ([neck_outer.eval(i / 20.0) for i in range(21)]
                      + [neck_inner.eval(i / 20.0) for i in range(20, -1, -1)])
        c.create_polygon(*self.coords(neck_shape), fill="#ffffff", outline="")
        upper_bill, pouch = self.model.bill_fill_curves
        bill_shape = ([upper_bill.eval(i / 20.0) for i in range(21)]
                      + [pouch.eval(i / 20.0) for i in range(1, 21)])
        c.create_polygon(*self.coords(bill_shape), fill="#fde68a", outline="")

        # Wheels first, with decorative spokes derived from the constrained circles.
        for entity, color, line_width in self.model.circles:
            center = entity.center().eval()
            radius = entity.radius().value()
            x, y = self.screen(center)
            r = radius * self.scale
            c.create_oval(x-r, y-r, x+r, y+r, outline=color, width=line_width)
            if radius > 1.0:
                for angle in range(0, 180, 30):
                    dx = math.cos(math.radians(angle)) * r
                    dy = math.sin(math.radians(angle)) * r
                    c.create_line(x-dx, y-dy, x+dx, y+dy, fill="#94a3b8", width=1)

        for entity, color, line_width in self.model.lines:
            c.create_line(*self.coords([entity.source().eval(), entity.target().eval()]),
                          fill=color, width=line_width, capstyle=tk.ROUND)
        for entity, color, line_width in self.model.curves:
            samples = [entity.eval(i / 40.0) for i in range(41)]
            c.create_line(*self.coords(samples), fill=color, width=line_width,
                          smooth=False, capstyle=tk.ROUND, joinstyle=tk.ROUND)

        for index, (point, position) in enumerate(zip(self.model.points, self.positions())):
            x, y = self.screen(position)
            control = id(point) in self.model.control_points
            radius = 4 if control else 6
            fill = "#fb923c" if control else "#0284c7"
            outline = "#ef4444" if index == self.selected else "white"
            c.create_oval(x-radius, y-radius, x+radius, y+radius, fill=fill,
                          outline=outline, width=2)

        self.status.set(
            "Drag any node — blue: shape nodes, orange: Bézier controls  |  "
            f"{self.model.last_result.name}  |  DOF {self.model.sketch.degrees_of_freedom()}"
        )


def main():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise SystemExit(f"Could not open a GUI display: {error}") from error
    PelicanBicycleView(root)
    root.mainloop()


if __name__ == "__main__":
    main()
