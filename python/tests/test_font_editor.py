import tempfile
import unittest
from pathlib import Path

import adjacent
import adjacent.font_editor as editor_module
from adjacent.font_editor import FontDocument, FontEditor, Glyph
from fontTools.ttLib import TTFont


class FontEditorModelTests(unittest.TestCase):
    def triangle(self):
        glyph = Glyph("A", "A", 700)
        points = [glyph.point(100, 0), glyph.point(350, 700), glyph.point(600, 0)]
        contour = glyph.new_contour(points[0])
        glyph.add_line(contour, points[0], points[1])
        glyph.add_line(contour, points[1], points[2])
        glyph.add_line(contour, points[2], points[0])
        contour.closed = True
        self.assertEqual(glyph.solve(), adjacent.SolveResult.OKAY)
        return glyph

    def test_path_data(self):
        path = self.triangle().path_data()
        self.assertTrue(path.startswith("M100.000,0.000"))
        self.assertTrue(path.endswith("Z"))

    def test_svg_parser(self):
        instance = FontEditor.__new__(FontEditor)
        instance.document = FontDocument()
        instance.glyph_index = 0
        instance.fit_view = lambda: None
        instance.redraw = lambda: None
        instance.load_svg_paths(["M0 0 H100 V100 L0 100 Z M200 0 Q250 100 300 0"])
        self.assertEqual([len(c.segments) for c in instance.glyph.contours], [4, 1])
        self.assertEqual(instance.glyph.contours[1].segments[0].kind, "cubic")

    def test_parallel_constraint_roundtrip(self):
        glyph = Glyph("parallel")
        p0, p1 = glyph.point(0, 0), glyph.point(100, 10)
        p2, p3 = glyph.point(0, 100), glyph.point(100, 120)
        first = glyph.new_contour(p0)
        a = glyph.add_line(first, p0, p1)
        second = glyph.new_contour(p2)
        b = glyph.add_line(second, p2, p3)
        constraint = editor_module.constraints.Parallel(a.entity, b.entity)
        glyph.sketch.add_constraint(constraint)
        glyph.constraints.append((constraint, "Parallel lines",
                                  ("parallel", [p0, p1, p2, p3])))
        glyph.solve()
        instance = FontEditor.__new__(FontEditor)
        data = instance.glyph_to_dict(glyph)
        restored = instance.glyph_from_dict(data)
        self.assertEqual(restored.constraints[0][2][0], "parallel")
        q0, q1, q2, q3 = restored.points
        d1 = [q1.eval()[i] - q0.eval()[i] for i in range(2)]
        d2 = [q3.eval()[i] - q2.eval()[i] for i in range(2)]
        self.assertAlmostEqual(d1[0] * d2[1] - d1[1] * d2[0], 0.0, places=7)

    def test_ttf_export(self):
        document = FontDocument()
        document.glyphs = [self.triangle()]
        instance = FontEditor.__new__(FontEditor)
        instance.document = document
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test.ttf"
            old_dialog = editor_module.filedialog.asksaveasfilename
            old_info = editor_module.messagebox.showinfo
            old_error = editor_module.messagebox.showerror
            errors = []
            try:
                editor_module.filedialog.asksaveasfilename = lambda **_kwargs: str(output)
                editor_module.messagebox.showinfo = lambda *_args, **_kwargs: None
                editor_module.messagebox.showerror = lambda *args, **_kwargs: errors.append(args)
                instance.export_ttf()
            finally:
                editor_module.filedialog.asksaveasfilename = old_dialog
                editor_module.messagebox.showinfo = old_info
                editor_module.messagebox.showerror = old_error
            self.assertFalse(errors)
            font = TTFont(output)
            self.assertEqual(font.getBestCmap()[ord("A")], "A")


if __name__ == "__main__":
    unittest.main()
