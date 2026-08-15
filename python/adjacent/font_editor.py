"""Adjacent Outline — a compact constraint-based SVG and font editor.

The editor deliberately keeps its document model small: glyphs contain contours made
from line and cubic Bézier segments, while every node and handle is an Adjacent solver
point. This makes geometric constraints and direct manipulation use the same data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from xml.etree import ElementTree

from . import _adjacent as adjacent
from ._adjacent import constraints


@dataclass
class Segment:
    kind: str
    points: list
    entity: object

    @property
    def start(self):
        return self.points[0]

    @property
    def end(self):
        return self.points[-1]

    def sample(self, count=24):
        if self.kind == "line":
            return [self.start.eval(), self.end.eval()]
        return [self.entity.eval(i / count) for i in range(count + 1)]


@dataclass
class Contour:
    segments: list[Segment] = field(default_factory=list)
    start: object | None = None
    current: object | None = None
    closed: bool = False


class Glyph:
    def __init__(self, name, character="", advance=700):
        self.name = name
        self.character = character
        self.advance = advance
        self.sketch = adjacent.Sketch()
        self.points = []
        self.contours = []
        self.constraints = []

    def point(self, x, y):
        point = adjacent.Point(float(x), float(y))
        self.points.append(point)
        self.sketch.add_entity(point)
        return point

    def add_line(self, contour, start, end):
        entity = adjacent.Line(start, end)
        segment = Segment("line", [start, end], entity)
        contour.segments.append(segment)
        self.sketch.add_entity(entity)
        contour.current = end
        return segment

    def add_cubic(self, contour, start, c1, c2, end):
        entity = adjacent.CubicBezier(start, c1, c2, end)
        segment = Segment("cubic", [start, c1, c2, end], entity)
        contour.segments.append(segment)
        self.sketch.add_entity(entity)
        contour.current = end
        return segment

    def new_contour(self, point):
        contour = Contour(start=point, current=point)
        self.contours.append(contour)
        return contour

    def all_segments(self):
        return [segment for contour in self.contours for segment in contour.segments]

    def solve(self):
        return self.sketch.update()

    def bounds(self):
        positions = [point.eval() for point in self.points]
        if not positions:
            return 0, 0, self.advance, 700
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        return min(xs), min(ys), max(xs), max(ys)

    def path_data(self):
        commands = []
        for contour in self.contours:
            if not contour.segments:
                continue
            x, y = contour.segments[0].start.eval()
            commands.append(f"M{x:.3f},{y:.3f}")
            for segment in contour.segments:
                if segment.kind == "line":
                    x, y = segment.end.eval()
                    commands.append(f"L{x:.3f},{y:.3f}")
                else:
                    c1, c2, end = [p.eval() for p in segment.points[1:]]
                    commands.append(
                        f"C{c1[0]:.3f},{c1[1]:.3f} {c2[0]:.3f},{c2[1]:.3f} "
                        f"{end[0]:.3f},{end[1]:.3f}"
                    )
            if contour.closed:
                commands.append("Z")
        return " ".join(commands)


class FontDocument:
    def __init__(self):
        self.family = "Adjacent Sans"
        self.units_per_em = 1000
        self.ascent = 800
        self.descent = -200
        self.glyphs = [Glyph("A", "A", 700)]


class FontEditor:
    def __init__(self, root):
        self.root = root
        root.title("Adjacent Outline — SVG / Font Editor")
        root.geometry("1280x820")
        self.document = FontDocument()
        self.glyph_index = 0
        self.active_contour = None
        self.tool = "select"
        self.selected_points = []
        self.selected_segments = []
        self.dragging = None
        self.pending = []
        self.scale = 0.72
        self.origin_x = 145.0
        self.origin_y = 650.0
        self.pan_anchor = None
        self.snap = tk.BooleanVar(value=True)
        self.show_handles = tk.BooleanVar(value=True)
        self.preserve_contours = tk.BooleanVar(value=True)
        self.drag_group_ids = set()

        self.build_menu()
        self.build_ui()
        self.refresh_glyph_list()
        self.set_tool("select")

    @property
    def glyph(self):
        return self.document.glyphs[self.glyph_index]

    def build_menu(self):
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New project", command=self.new_project, accelerator="Ctrl+N")
        file_menu.add_command(label="Open project…", command=self.open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="Save project…", command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Import SVG path…", command=self.import_svg)
        file_menu.add_command(label="Export current glyph as SVG…", command=self.export_svg)
        file_menu.add_command(label="Export font as TTF…", command=self.export_ttf)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        glyph_menu = tk.Menu(menu, tearoff=False)
        glyph_menu.add_command(label="Font info…", command=self.edit_font_info)
        glyph_menu.add_separator()
        glyph_menu.add_command(label="New glyph…", command=self.add_glyph)
        glyph_menu.add_command(label="Glyph metrics…", command=self.edit_metrics)
        glyph_menu.add_command(label="New contour", command=self.new_contour)
        glyph_menu.add_command(label="Close contour", command=self.close_contour)
        menu.add_cascade(label="Glyph", menu=glyph_menu)
        self.root.config(menu=menu)
        self.root.bind("<Control-s>", lambda _e: self.save_project())
        self.root.bind("<Control-o>", lambda _e: self.open_project())
        self.root.bind("<Control-n>", lambda _e: self.new_project())
        self.root.bind("<Escape>", lambda _e: self.cancel())
        self.root.bind("<Delete>", lambda _e: self.delete_selected())

    def build_ui(self):
        left = tk.Frame(self.root, bg="#e2e8f0", padx=5, pady=5)
        left.pack(side=tk.LEFT, fill=tk.Y)
        self.tool_button(left, "Select / nodes (V)", "select")
        self.tool_button(left, "Pen / lines (P)", "pen")
        self.tool_button(left, "Cubic curve (B)", "cubic")
        tk.Frame(left, height=2, bg="#94a3b8").pack(fill=tk.X, pady=7)
        tk.Label(left, text="Constraints", bg="#e2e8f0",
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        for label, command in [
            ("Fix point", self.constrain_fixed), ("Horizontal", self.constrain_horizontal),
            ("Vertical", self.constrain_vertical), ("Parallel lines", self.constrain_parallel),
            ("Coincident points", self.constrain_coincident),
            ("Point distance…", self.constrain_distance),
            ("Smooth: 3 points", self.constrain_smooth),
        ]:
            tk.Button(left, text=label, width=18, anchor="w", command=command).pack(fill=tk.X, pady=1)
        tk.Frame(left, height=2, bg="#94a3b8").pack(fill=tk.X, pady=7)
        tk.Button(left, text="New contour", command=self.new_contour).pack(fill=tk.X, pady=1)
        tk.Button(left, text="Close contour", command=self.close_contour).pack(fill=tk.X, pady=1)
        tk.Checkbutton(left, text="Snap to 10 units", variable=self.snap, bg="#e2e8f0").pack(anchor="w")
        tk.Checkbutton(left, text="Show handles", variable=self.show_handles,
                       bg="#e2e8f0", command=self.redraw).pack(anchor="w")
        tk.Checkbutton(left, text="Keep other contours still", variable=self.preserve_contours,
                       bg="#e2e8f0").pack(anchor="w")

        right = tk.Frame(self.root, width=235, padx=6, pady=5)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(right, text="Glyphs", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.glyph_list = tk.Listbox(right, width=28, height=16, exportselection=False)
        self.glyph_list.pack(fill=tk.X)
        self.glyph_list.bind("<<ListboxSelect>>", self.select_glyph)
        tk.Button(right, text="Add glyph…", command=self.add_glyph).pack(fill=tk.X, pady=3)
        tk.Label(right, text="Constraints", font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w", pady=(12, 2))
        self.constraint_list = tk.Listbox(right, width=28, height=19)
        self.constraint_list.pack(fill=tk.BOTH, expand=True)

        center = tk.Frame(self.root)
        center.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(center, bg="#f8fafc", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status = tk.StringVar()
        tk.Label(center, textvariable=self.status, anchor="w", padx=8, pady=5).pack(fill=tk.X)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonPress-2>", self.pan_start)
        self.canvas.bind("<B2-Motion>", self.pan_move)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<Button-4>", lambda event: self.zoom(event, 1))
        self.canvas.bind("<Button-5>", lambda event: self.zoom(event, -1))
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.root.bind("v", lambda _e: self.set_tool("select"))
        self.root.bind("p", lambda _e: self.set_tool("pen"))
        self.root.bind("b", lambda _e: self.set_tool("cubic"))

    def tool_button(self, parent, label, tool):
        tk.Button(parent, text=label, width=18, anchor="w",
                  command=lambda: self.set_tool(tool)).pack(fill=tk.X, pady=1)

    def set_tool(self, tool):
        self.tool = tool
        self.pending.clear()
        hints = {
            "select": "Drag nodes; click outlines to select lines; Shift-click selects several",
            "pen": "Click to start or append straight segments; click the first node to close",
            "cubic": "Click an endpoint to append a cubic segment; then adjust its blue handles",
        }
        self.status.set(hints[tool] + "  •  middle-drag pans, wheel zooms")
        self.redraw()

    def to_screen(self, point):
        return self.origin_x + point[0] * self.scale, self.origin_y - point[1] * self.scale

    def to_world(self, x, y):
        wx, wy = (x - self.origin_x) / self.scale, (self.origin_y - y) / self.scale
        if self.snap.get():
            wx, wy = round(wx / 10) * 10, round(wy / 10) * 10
        return wx, wy

    def pick_point(self, event):
        candidates = []
        for point in self.glyph.points:
            x, y = self.to_screen(point.eval())
            distance = (event.x - x) ** 2 + (event.y - y) ** 2
            candidates.append((distance, point))
        if not candidates:
            return None
        distance, point = min(candidates, key=lambda item: item[0])
        return point if distance <= 13 ** 2 else None

    @staticmethod
    def line_distance(point, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length2 = dx * dx + dy * dy
        t = 0 if not length2 else max(0, min(1, ((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length2))
        return math.hypot(point[0] - a[0] - t*dx, point[1] - a[1] - t*dy)

    def pick_segment(self, event):
        world = self.to_world(event.x, event.y)
        candidates = []
        for segment in self.glyph.all_segments():
            samples = segment.sample()
            distance = min(self.line_distance(world, samples[i], samples[i+1])
                           for i in range(len(samples)-1))
            candidates.append((distance, segment))
        if not candidates:
            return None
        distance, segment = min(candidates, key=lambda item: item[0])
        return segment if distance * self.scale <= 10 else None

    def on_press(self, event):
        if self.tool == "select":
            point = self.pick_point(event)
            if point:
                if event.state & 0x0001:
                    if point in self.selected_points:
                        self.selected_points.remove(point)
                    else:
                        self.selected_points.append(point)
                else:
                    self.selected_points = [point]
                self.selected_segments.clear()
                self.dragging = point
                self.drag_group_ids = self.contour_point_ids(point)
            else:
                segment = self.pick_segment(event)
                self.selected_points.clear()
                if event.state & 0x0001:
                    if segment in self.selected_segments:
                        self.selected_segments.remove(segment)
                    elif segment:
                        self.selected_segments.append(segment)
                else:
                    self.selected_segments = [segment] if segment else []
            self.redraw()
            return
        self.append_at(*self.to_world(event.x, event.y))

    def append_at(self, x, y):
        contour = self.active_contour
        if contour is None or contour.closed:
            start = self.pick_point_at(x, y) or self.glyph.point(x, y)
            self.active_contour = self.glyph.new_contour(start)
            self.glyph.solve(); self.redraw(); return
        near_start = math.dist((x, y), contour.start.eval()) * self.scale < 14
        end = contour.start if near_start else (self.pick_point_at(x, y) or self.glyph.point(x, y))
        if self.tool == "pen":
            self.glyph.add_line(contour, contour.current, end)
        else:
            sx, sy = contour.current.eval(); ex, ey = end.eval()
            dx, dy = ex-sx, ey-sy
            c1 = self.glyph.point(sx + dx/3 - dy*.12, sy + dy/3 + dx*.12)
            c2 = self.glyph.point(sx + 2*dx/3 - dy*.12, sy + 2*dy/3 + dx*.12)
            self.glyph.add_cubic(contour, contour.current, c1, c2, end)
        if near_start:
            contour.closed = True
            self.active_contour = None
        self.glyph.solve(); self.redraw()

    def pick_point_at(self, x, y):
        for point in self.glyph.points:
            if math.dist((x, y), point.eval()) * self.scale <= 12:
                return point
        return None

    def contour_point_ids(self, point):
        for contour in self.glyph.contours:
            contour_points = [candidate for segment in contour.segments for candidate in segment.points]
            if any(candidate is point for candidate in contour_points):
                return {id(candidate) for candidate in contour_points}
        return {id(point)}

    def on_motion(self, event):
        if not self.dragging:
            return
        target = self.to_world(event.x, event.y)
        if self.preserve_contours.get():
            stays = [point for point in self.glyph.points if id(point) not in self.drag_group_ids]
            result = self.glyph.sketch.drag_point_with_stays(self.dragging, *target, stays)
        else:
            result = self.glyph.sketch.drag_point(self.dragging, *target)
        self.status.set(f"{result.name}  •  DOF {self.glyph.sketch.degrees_of_freedom()}")
        self.redraw()

    def on_release(self, _event):
        self.dragging = None
        self.drag_group_ids.clear()

    def pan_start(self, event):
        self.pan_anchor = event.x, event.y, self.origin_x, self.origin_y

    def pan_move(self, event):
        if self.pan_anchor:
            x, y, ox, oy = self.pan_anchor
            self.origin_x, self.origin_y = ox + event.x-x, oy + event.y-y
            self.redraw()

    def zoom(self, event, direction=None):
        direction = direction or (1 if event.delta > 0 else -1)
        factor = 1.15 if direction > 0 else 1/1.15
        wx, wy = (event.x-self.origin_x)/self.scale, (self.origin_y-event.y)/self.scale
        self.scale = max(.08, min(5, self.scale*factor))
        self.origin_x = event.x - wx*self.scale
        self.origin_y = event.y + wy*self.scale
        self.redraw()

    def new_contour(self):
        self.active_contour = None
        self.set_tool("pen")

    def close_contour(self):
        contour = self.active_contour
        if contour and contour.current is not contour.start:
            self.glyph.add_line(contour, contour.current, contour.start)
            contour.closed = True
            self.active_contour = None
            self.glyph.solve(); self.redraw()

    def cancel(self):
        self.pending.clear(); self.dragging = None; self.set_tool("select")

    def add_constraint(self, constraint, label, record=None):
        self.glyph.sketch.add_constraint(constraint)
        result = self.glyph.sketch.update()
        if result != adjacent.SolveResult.OKAY:
            self.glyph.sketch.remove_constraint(constraint)
            self.glyph.sketch.update()
            messagebox.showerror("Constraint", "Constraint could not be satisfied")
            return
        self.glyph.constraints.append((constraint, label, record))
        self.constraint_list.insert(tk.END, label)
        self.redraw()

    def require_points(self, count):
        if len(self.selected_points) != count:
            messagebox.showinfo("Selection", f"Select exactly {count} point(s) first")
            return None
        return self.selected_points

    def constrain_fixed(self):
        points = self.require_points(1)
        if points:
            self.add_constraint(constraints.FixedPoint(points[0]), "Fixed point", ("fixed", points))

    def selected_lines(self, minimum=1):
        lines = [segment for segment in self.selected_segments if segment.kind == "line"]
        if len(lines) < minimum or len(lines) != len(self.selected_segments):
            messagebox.showinfo("Selection", f"Select at least {minimum} straight line segment(s)")
            return None
        return lines

    def constrain_horizontal(self):
        if self.selected_segments:
            lines = self.selected_lines()
            if not lines: return
            for segment in lines:
                points = [segment.start, segment.end]
                self.add_constraint(constraints.HV(segment.entity, constraints.HVOrientation.OX),
                                    "Horizontal line", ("horizontal", points))
            return
        points = self.require_points(2)
        if points:
            self.add_constraint(constraints.HV(points[0], points[1], constraints.HVOrientation.OX),
                                "Horizontal", ("horizontal", points))

    def constrain_vertical(self):
        if self.selected_segments:
            lines = self.selected_lines()
            if not lines: return
            for segment in lines:
                points = [segment.start, segment.end]
                self.add_constraint(constraints.HV(segment.entity, constraints.HVOrientation.OY),
                                    "Vertical line", ("vertical", points))
            return
        points = self.require_points(2)
        if points:
            self.add_constraint(constraints.HV(points[0], points[1], constraints.HVOrientation.OY),
                                "Vertical", ("vertical", points))

    def constrain_parallel(self):
        lines = self.selected_lines(2)
        if not lines: return
        reference = lines[0]
        for segment in lines[1:]:
            record_points = [reference.start, reference.end, segment.start, segment.end]
            self.add_constraint(constraints.Parallel(reference.entity, segment.entity),
                                "Parallel lines", ("parallel", record_points))

    def constrain_coincident(self):
        points = self.require_points(2)
        if points:
            self.add_constraint(constraints.Coincident(*points), "Coincident", ("coincident", points))

    def constrain_distance(self):
        points = self.require_points(2)
        if not points: return
        value = simpledialog.askfloat("Distance", "Distance in font units",
                                      initialvalue=math.dist(points[0].eval(), points[1].eval()))
        if value is not None:
            self.add_constraint(constraints.Distance(*points, value), f"Distance = {value:g}",
                                ("distance", points, value))

    def constrain_smooth(self):
        points = self.require_points(3)
        if not points: return
        # Select handle, anchor, handle. Parallel handle rays enforce a smooth join.
        first = adjacent.Line(points[0], points[1])
        second = adjacent.Line(points[1], points[2])
        self.glyph.sketch.add_entity(first); self.glyph.sketch.add_entity(second)
        self.add_constraint(constraints.Parallel(first, second), "Smooth / collinear",
                            ("smooth", points))

    def delete_selected(self):
        if self.selected_points:
            messagebox.showinfo("Delete", "Node deletion with topology repair is not implemented yet; "
                                "delete segments by selecting their outline.")
            return
        if not self.selected_segments:
            return
        segment = self.selected_segments[0]
        for contour in self.glyph.contours:
            if segment in contour.segments and segment is contour.segments[-1]:
                self.glyph.sketch.remove_entity(segment.entity)
                contour.segments.remove(segment)
                contour.current = contour.segments[-1].end if contour.segments else contour.start
                contour.closed = False
                self.active_contour = contour
                self.selected_segments.clear(); self.glyph.solve(); self.redraw(); return
        messagebox.showinfo("Delete", "Only the last segment of a contour can currently be deleted")

    def refresh_glyph_list(self):
        self.glyph_list.delete(0, tk.END)
        for glyph in self.document.glyphs:
            display = f"{glyph.character or '□'}  {glyph.name}   {glyph.advance}"
            self.glyph_list.insert(tk.END, display)
        self.glyph_list.selection_set(self.glyph_index)
        self.refresh_constraints()

    def refresh_constraints(self):
        self.constraint_list.delete(0, tk.END)
        for _constraint, label, _record in self.glyph.constraints:
            self.constraint_list.insert(tk.END, label)

    def select_glyph(self, _event=None):
        selection = self.glyph_list.curselection()
        if not selection: return
        self.glyph_index = selection[0]
        self.active_contour = None
        self.selected_points.clear(); self.selected_segments.clear()
        self.refresh_constraints(); self.fit_view(); self.redraw()

    def add_glyph(self):
        text = simpledialog.askstring("New glyph", "Character (one Unicode character)", parent=self.root)
        if not text: return
        character = text[0]
        default_name = f"uni{ord(character):04X}"
        name = simpledialog.askstring("Glyph name", "Glyph name", initialvalue=default_name,
                                      parent=self.root) or default_name
        self.document.glyphs.append(Glyph(name, character))
        self.glyph_index = len(self.document.glyphs)-1
        self.refresh_glyph_list(); self.fit_view(); self.redraw()

    def edit_font_info(self):
        family = simpledialog.askstring("Font info", "Family name", initialvalue=self.document.family,
                                        parent=self.root)
        if family is None: return
        upm = simpledialog.askinteger("Font info", "Units per em", initialvalue=self.document.units_per_em,
                                      minvalue=16, maxvalue=16384, parent=self.root)
        if upm is None: return
        ascent = simpledialog.askinteger("Font info", "Ascender", initialvalue=self.document.ascent,
                                         parent=self.root)
        if ascent is None: return
        descent = simpledialog.askinteger("Font info", "Descender", initialvalue=self.document.descent,
                                          parent=self.root)
        if descent is None: return
        self.document.family, self.document.units_per_em = family, upm
        self.document.ascent, self.document.descent = ascent, descent
        self.fit_view(); self.redraw()

    def edit_metrics(self):
        value = simpledialog.askinteger("Advance width", "Advance width", initialvalue=self.glyph.advance,
                                        minvalue=1, parent=self.root)
        if value:
            self.glyph.advance = value; self.refresh_glyph_list(); self.redraw()

    def fit_view(self):
        width = max(300, self.canvas.winfo_width())
        height = max(300, self.canvas.winfo_height())
        self.scale = min((width-100)/max(1, self.glyph.advance+200),
                         (height-80)/(self.document.ascent-self.document.descent+200))
        self.origin_x = 60 + 100*self.scale
        self.origin_y = 40 + (self.document.ascent+100)*self.scale

    def draw_grid(self):
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        step = 100
        x0 = math.floor(-self.origin_x/self.scale/step)*step
        x = x0
        while self.origin_x+x*self.scale < width:
            sx, _ = self.to_screen((x, 0))
            self.canvas.create_line(sx, 0, sx, height, fill="#edf2f7")
            x += step
        y0 = math.floor((self.origin_y-height)/self.scale/step)*step
        y = y0
        while self.origin_y-y*self.scale > 0:
            _, sy = self.to_screen((0, y))
            self.canvas.create_line(0, sy, width, sy, fill="#edf2f7")
            y += step
        for y, color, label in [(0, "#475569", "baseline"),
                                (self.document.ascent, "#94a3b8", "ascender"),
                                (self.document.descent, "#94a3b8", "descender")]:
            _, sy = self.to_screen((0, y))
            self.canvas.create_line(0, sy, width, sy, fill=color, width=2)
            self.canvas.create_text(5, sy-3, text=label, anchor="sw", fill=color)
        for x in (0, self.glyph.advance):
            sx, _ = self.to_screen((x, 0))
            self.canvas.create_line(sx, 0, sx, height, fill="#64748b", dash=(4, 4))

    def redraw(self):
        if not hasattr(self, "canvas"): return
        self.draw_grid()
        selected_segments = set(id(s) for s in self.selected_segments)
        for contour in self.glyph.contours:
            for segment in contour.segments:
                samples = [self.to_screen(point) for point in segment.sample()]
                coords = [coordinate for point in samples for coordinate in point]
                color = "#dc2626" if id(segment) in selected_segments else "#111827"
                self.canvas.create_line(*coords, fill=color, width=3, capstyle=tk.ROUND,
                                        joinstyle=tk.ROUND)
                if self.show_handles.get() and segment.kind == "cubic":
                    p0, c1, c2, p3 = [self.to_screen(p.eval()) for p in segment.points]
                    self.canvas.create_line(*p0, *c1, fill="#93c5fd", dash=(3, 3))
                    self.canvas.create_line(*c2, *p3, fill="#93c5fd", dash=(3, 3))
        endpoint_ids = {id(segment.start) for segment in self.glyph.all_segments()}
        endpoint_ids.update(id(segment.end) for segment in self.glyph.all_segments())
        for point in self.glyph.points:
            x, y = self.to_screen(point.eval())
            selected = point in self.selected_points
            endpoint = id(point) in endpoint_ids
            radius = 6 if endpoint else 5
            fill = "#ef4444" if selected else ("#f97316" if endpoint else "#3b82f6")
            shape = self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                            fill=fill, outline="white", width=1)
        caption = (f"{self.glyph.character}  {self.glyph.name}  "
                   f"U+{ord(self.glyph.character):04X}" if self.glyph.character
                   else self.glyph.name)
        self.canvas.create_text(10, 10, anchor="nw", fill="#64748b", text=caption)

    def glyph_to_dict(self, glyph):
        point_ids = {id(point): index for index, point in enumerate(glyph.points)}
        data = {"name": glyph.name, "character": glyph.character, "advance": glyph.advance,
                "points": [point.eval() for point in glyph.points], "contours": [],
                "constraints": []}
        for contour in glyph.contours:
            data["contours"].append({
                "closed": contour.closed,
                "segments": [{"kind": segment.kind,
                              "points": [point_ids[id(point)] for point in segment.points]}
                             for segment in contour.segments],
            })
        for _constraint, label, record in glyph.constraints:
            if not record:
                continue
            kind, record_points, *values = record
            data["constraints"].append({"kind": kind, "label": label,
                                        "points": [point_ids[id(point)] for point in record_points],
                                        "values": values})
        return data

    def glyph_from_dict(self, data):
        glyph = Glyph(data["name"], data.get("character", ""), data.get("advance", 700))
        points = [glyph.point(*position) for position in data.get("points", [])]
        for contour_data in data.get("contours", []):
            contour = Contour(closed=contour_data.get("closed", False))
            glyph.contours.append(contour)
            for segment_data in contour_data["segments"]:
                segment_points = [points[index] for index in segment_data["points"]]
                if segment_data["kind"] == "line":
                    glyph.add_line(contour, *segment_points)
                else:
                    glyph.add_cubic(contour, *segment_points)
            if contour.segments:
                contour.start = contour.segments[0].start
                contour.current = contour.segments[-1].end
        for item in data.get("constraints", []):
            selected = [points[index] for index in item["points"]]
            kind = item["kind"]
            if kind == "fixed": constraint = constraints.FixedPoint(selected[0])
            elif kind == "horizontal":
                constraint = constraints.HV(selected[0], selected[1], constraints.HVOrientation.OX)
            elif kind == "vertical":
                constraint = constraints.HV(selected[0], selected[1], constraints.HVOrientation.OY)
            elif kind == "coincident": constraint = constraints.Coincident(*selected)
            elif kind == "distance":
                constraint = constraints.Distance(selected[0], selected[1], item["values"][0])
            elif kind in ("smooth", "parallel"):
                if kind == "smooth":
                    first = adjacent.Line(selected[0], selected[1])
                    second = adjacent.Line(selected[1], selected[2])
                else:
                    first = adjacent.Line(selected[0], selected[1])
                    second = adjacent.Line(selected[2], selected[3])
                glyph.sketch.add_entity(first); glyph.sketch.add_entity(second)
                constraint = constraints.Parallel(first, second)
            else: continue
            glyph.sketch.add_constraint(constraint)
            glyph.constraints.append((constraint, item.get("label", kind.title()),
                                      (kind, selected, *item.get("values", []))))
        glyph.solve()
        return glyph

    def save_project(self):
        filename = filedialog.asksaveasfilename(defaultextension=".adjfont.json",
                                                filetypes=[("Adjacent Font", "*.adjfont.json")])
        if not filename: return
        data = {"family": self.document.family, "units_per_em": self.document.units_per_em,
                "ascent": self.document.ascent, "descent": self.document.descent,
                "glyphs": [self.glyph_to_dict(glyph) for glyph in self.document.glyphs]}
        Path(filename).write_text(json.dumps(data, indent=2), encoding="utf8")

    def open_project(self):
        filename = filedialog.askopenfilename(filetypes=[("Adjacent Font", "*.adjfont.json"),
                                                         ("JSON", "*.json")])
        if not filename: return
        try:
            data = json.loads(Path(filename).read_text(encoding="utf8"))
            document = FontDocument()
            document.family = data.get("family", "Adjacent Sans")
            document.units_per_em = data.get("units_per_em", 1000)
            document.ascent = data.get("ascent", 800); document.descent = data.get("descent", -200)
            document.glyphs = [self.glyph_from_dict(item) for item in data["glyphs"]]
            self.document = document; self.glyph_index = 0
            self.refresh_glyph_list(); self.fit_view(); self.redraw()
        except Exception as error:
            messagebox.showerror("Open project", str(error))

    def new_project(self):
        if messagebox.askyesno("New project", "Discard the current project?"):
            self.document = FontDocument(); self.glyph_index = 0; self.active_contour = None
            self.refresh_glyph_list(); self.fit_view(); self.redraw()

    def export_svg(self):
        filename = filedialog.asksaveasfilename(defaultextension=".svg",
                                                filetypes=[("SVG", "*.svg")])
        if not filename: return
        path = self.glyph.path_data()
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'viewBox="0 {-self.document.ascent} {self.glyph.advance} '
               f'{self.document.ascent-self.document.descent}">\n'
               f'  <g transform="scale(1,-1)"><path d="{path}" fill="black"/></g>\n</svg>\n')
        Path(filename).write_text(svg, encoding="utf8")

    def import_svg(self):
        filename = filedialog.askopenfilename(filetypes=[("SVG", "*.svg")])
        if not filename: return
        try:
            root = ElementTree.parse(filename).getroot()
            paths = [element.attrib.get("d", "") for element in root.iter()
                     if element.tag.rsplit("}", 1)[-1] == "path"]
            if not paths: raise ValueError("No <path> elements found")
            self.load_svg_paths(paths)
        except Exception as error:
            messagebox.showerror("Import SVG", str(error))

    def load_svg_paths(self, paths):
        glyph = self.glyph
        token_re = re.compile(r"[MmLlHhVvCcQqZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
        for path in paths:
            tokens = token_re.findall(path); i = 0; command = None
            current = (0.0, 0.0); contour = None
            while i < len(tokens):
                if tokens[i].isalpha(): command = tokens[i]; i += 1
                if command in "Zz":
                    if contour and contour.current is not contour.start:
                        glyph.add_line(contour, contour.current, contour.start)
                    if contour: contour.closed = True
                    contour = None; command = None; continue
                relative = command.islower(); upper = command.upper()
                counts = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Q": 4}
                count = counts.get(upper)
                if count is None or i+count > len(tokens): break
                values = list(map(float, tokens[i:i+count])); i += count
                def position(x, y):
                    px, py = (x+current[0], y+current[1]) if relative else (x, y)
                    return px, -py  # SVG is y-down; font coordinates are y-up.
                if upper == "H": end = position(values[0], current[1] if not relative else 0)
                elif upper == "V": end = position(current[0] if not relative else 0, values[0])
                else: end = position(values[-2], values[-1])
                if upper == "M":
                    point = glyph.point(*end); contour = glyph.new_contour(point)
                    current = (end[0], -end[1]); command = "l" if relative else "L"; continue
                if contour is None:
                    point = glyph.point(*current); contour = glyph.new_contour(point)
                endpoint = glyph.point(*end)
                if upper in ("L", "H", "V"):
                    glyph.add_line(contour, contour.current, endpoint)
                elif upper == "C":
                    c1 = glyph.point(*position(values[0], values[1]))
                    c2 = glyph.point(*position(values[2], values[3]))
                    glyph.add_cubic(contour, contour.current, c1, c2, endpoint)
                else:  # Quadratic converted exactly to cubic.
                    qx, qy = position(values[0], values[1]); sx, sy = contour.current.eval()
                    c1 = glyph.point(sx + 2*(qx-sx)/3, sy + 2*(qy-sy)/3)
                    c2 = glyph.point(end[0] + 2*(qx-end[0])/3, end[1] + 2*(qy-end[1])/3)
                    glyph.add_cubic(contour, contour.current, c1, c2, endpoint)
                current = (end[0], -end[1])
        glyph.solve(); self.fit_view(); self.redraw()

    def export_ttf(self):
        filename = filedialog.asksaveasfilename(defaultextension=".ttf",
                                                filetypes=[("TrueType font", "*.ttf")])
        if not filename: return
        try:
            from fontTools.fontBuilder import FontBuilder
            from fontTools.pens.cu2quPen import Cu2QuPen
            from fontTools.pens.ttGlyphPen import TTGlyphPen
            names = [".notdef"] + [g.name for g in self.document.glyphs if g.name != ".notdef"]
            builder = FontBuilder(self.document.units_per_em, isTTF=True)
            builder.setupGlyphOrder(names)
            glyphs = {".notdef": TTGlyphPen(None).glyph()}
            metrics = {".notdef": (self.document.units_per_em//2, 0)}
            cmap = {}
            for glyph in self.document.glyphs:
                if glyph.name == ".notdef": continue
                pen = TTGlyphPen(None)
                cubic_pen = Cu2QuPen(pen, max_err=1.0, reverse_direction=False)
                for contour in glyph.contours:
                    if not contour.segments: continue
                    cubic_pen.moveTo(tuple(contour.segments[0].start.eval()))
                    for segment in contour.segments:
                        if segment.kind == "line":
                            cubic_pen.lineTo(tuple(segment.end.eval()))
                        else:
                            cubic_pen.curveTo(*[tuple(point.eval()) for point in segment.points[1:]])
                    cubic_pen.closePath() if contour.closed else cubic_pen.endPath()
                glyphs[glyph.name] = pen.glyph()
                x_min = int(glyph.bounds()[0])
                metrics[glyph.name] = (glyph.advance, x_min)
                if glyph.character: cmap[ord(glyph.character)] = glyph.name
            builder.setupGlyf(glyphs)
            builder.setupHorizontalMetrics(metrics)
            builder.setupHorizontalHeader(ascent=self.document.ascent, descent=self.document.descent)
            builder.setupCharacterMap(cmap)
            builder.setupNameTable({"familyName": self.document.family,
                                    "styleName": "Regular", "uniqueFontIdentifier": self.document.family,
                                    "fullName": self.document.family, "psName": self.document.family.replace(" ", "-")})
            builder.setupOS2(sTypoAscender=self.document.ascent, sTypoDescender=self.document.descent,
                             usWinAscent=max(0, self.document.ascent), usWinDescent=max(0, -self.document.descent))
            builder.setupPost(); builder.setupMaxp(); builder.save(filename)
            messagebox.showinfo("Export font", f"Wrote {filename}")
        except Exception as error:
            messagebox.showerror("Export font", str(error))


def main():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise SystemExit(f"Could not open a GUI display: {error}") from error
    editor = FontEditor(root)
    root.after_idle(lambda: (editor.fit_view(), editor.redraw()))
    root.mainloop()


if __name__ == "__main__":
    main()
