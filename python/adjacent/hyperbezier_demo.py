"""Interactive experimental G2 hyperbezier pen-tool demo."""

import tkinter as tk

from .hyperbezier import AutoHyperSpline


class HyperBezierView:
    def __init__(self, root):
        root.title("Adjacent — experimental hyperbezier auto-spline")
        root.geometry("1000x720")
        self.canvas = tk.Canvas(root, bg="#fafafa", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status = tk.StringVar()
        tk.Label(root, textvariable=self.status, anchor="w", padx=10, pady=6).pack(fill=tk.X)
        self.points = [(100.0, 480.0), (235.0, 210.0), (390.0, 390.0),
                       (555.0, 170.0), (710.0, 360.0), (875.0, 190.0)]
        self.smooth = [False, True, True, True, True, False]
        self.selected = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.redraw()

    def pick(self, event):
        distances = [(x - event.x) ** 2 + (y - event.y) ** 2 for x, y in self.points]
        index = min(range(len(distances)), key=distances.__getitem__)
        return index if distances[index] <= 18**2 else None

    def on_press(self, event):
        self.selected = self.pick(event)
        if self.selected is not None:
            self.canvas.configure(cursor="fleur")

    def on_motion(self, event):
        if self.selected is None:
            return
        self.points[self.selected] = (float(event.x), float(event.y))
        self.redraw()

    def on_release(self, _event):
        self.selected = None
        self.canvas.configure(cursor="")

    def on_double_click(self, event):
        index = self.pick(event)
        if index is not None and index not in (0, len(self.points) - 1):
            self.smooth[index] = not self.smooth[index]
            self.redraw()

    def splines(self):
        """Split at corners; each smooth run receives its own global G2 solve."""
        starts = [0]
        starts.extend(i for i in range(1, len(self.points) - 1) if not self.smooth[i])
        starts.append(len(self.points) - 1)
        return [AutoHyperSpline(self.points[a:b + 1]) for a, b in zip(starts, starts[1:])]

    @staticmethod
    def flatten(points):
        return [value for point in points for value in point]

    def redraw(self):
        c = self.canvas
        c.delete("all")
        c.create_text(24, 22, anchor="nw", fill="#0f172a",
                      font=("TkDefaultFont", 16, "bold"),
                      text="HYPERBEZIER / G² AUTO-POINTS")
        c.create_text(24, 52, anchor="nw", fill="#475569",
                      text="Drag on-curve points. Double-click an interior point to toggle smooth/corner.")

        maximum_error = 0.0
        segment_count = 0
        for spline in self.splines():
            segments = spline.segments()
            segment_count += len(segments)
            for left, right in zip(segments, segments[1:]):
                maximum_error = max(maximum_error, abs(
                    left.endpoint_curvatures()[1] - right.endpoint_curvatures()[0]))
            for segment in segments:
                h1, h2 = segment.auto_handles()
                c.create_line(segment.start[0], segment.start[1], h1[0], h1[1],
                              fill="#94a3b8", dash=(4, 4))
                c.create_line(segment.end[0], segment.end[1], h2[0], h2[1],
                              fill="#94a3b8", dash=(4, 4))
                for x, y in (h1, h2):
                    c.create_line(x - 5, y - 5, x + 5, y + 5, fill="#f97316", width=2)
                    c.create_line(x - 5, y + 5, x + 5, y - 5, fill="#f97316", width=2)
                samples = segment.samples(48)
                c.create_line(*self.flatten(samples), fill="#2563eb", width=4,
                              capstyle=tk.ROUND, joinstyle=tk.ROUND)

        for index, (x, y) in enumerate(self.points):
            smooth = self.smooth[index]
            selected = index == self.selected
            if smooth:
                c.create_oval(x - 8, y - 8, x + 8, y + 8, fill="#0ea5e9",
                              outline="#ef4444" if selected else "white", width=3)
            else:
                c.create_rectangle(x - 8, y - 8, x + 8, y + 8, fill="#22c55e",
                                   outline="#ef4444" if selected else "white", width=3)

        self.status.set(
            f"{segment_count} hyperbezier segments  |  blue circles: smooth  |  "
            f"green squares: corners  |  maximum G² join error {maximum_error:.2e}"
        )


def main():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise SystemExit(f"Could not open a GUI display: {error}") from error
    HyperBezierView(root)
    root.mainloop()


if __name__ == "__main__":
    main()
