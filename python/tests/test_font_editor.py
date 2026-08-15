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
