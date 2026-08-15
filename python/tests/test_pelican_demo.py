import unittest

from adjacent.pelican_demo import PelicanBicycleModel


class PelicanBicycleTests(unittest.TestCase):
    def test_model_solves_and_drags(self):
        model = PelicanBicycleModel()
        self.assertEqual(model.last_result.name, "OKAY")
        self.assertGreaterEqual(len(model.constraint_names), 18)
        self.assertGreaterEqual(len(model.points), 40)

        point = model.points[0]
        x, y = point.eval()
        result = model.sketch.drag_point_with_stays(point, x + 0.1, y, model.points[1:])
        self.assertEqual(result.name, "OKAY")
        self.assertGreater(point.eval()[0], x)


if __name__ == "__main__":
    unittest.main()
