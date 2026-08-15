#include <cassert>
#include <cmath>
#include <iostream>

#include "constraint.hpp"
#include "gaussian_method.hpp"
#include "hyperbezier.hpp"

namespace
{
constexpr double tolerance = 1e-7;

std::shared_ptr<PointE> point(const std::string& name, double x, double y)
{
    return std::make_shared<PointE>(param(name + "_x", x), param(name + "_y", y),
                                    param(name + "_z", 0.0));
}

bool near(double a, double b) { return std::abs(a - b) < tolerance; }
}

int main()
{
    // Pivoting and back-substitution used to read one row past the matrix.
    xt::xtensor<double, 2> matrix = { { 0.0, 2.0 }, { 1.0, 1.0 } };
    xt::xtensor<double, 1> rhs = { 4.0, 3.0 };
    xt::xtensor<double, 1> solution;
    GaussianMethod::solve(matrix, rhs, solution);
    assert(near(solution(0), 1.0) && near(solution(1), 2.0));

    // A representative, fully constrained sketch.
    auto origin = point("origin", 0.0, 0.0);
    auto end = point("end", 2.0, 1.0);
    auto line = std::make_shared<LineE>(*origin, *end);
    Sketch sketch;
    sketch.add_entity(line);
    sketch.add_constraint(std::make_shared<FixedPointConstraint>(origin));
    sketch.add_constraint(std::make_shared<HVConstraint>(line, HVOrientation::OX));
    sketch.add_constraint(std::make_shared<LengthConstraint>(line, 5.0));
    assert(sketch.update() == SolveResult::OKAY);
    assert(near(origin->x->value(), 0.0));
    assert(near(origin->y->value(), 0.0));
    assert(near(end->y->value(), 0.0));
    assert(near(std::abs(end->x->value()), 5.0));
    assert(sketch.degrees_of_freedom() == 0);

    // Midpoint plus point-to-line distance constraints.
    auto middle = point("middle", 1.0, 3.0);
    sketch.add_entity(middle);
    auto midpoint = std::make_shared<MidpointConstraint>(middle, line);
    sketch.add_constraint(midpoint);
    assert(sketch.update() == SolveResult::OKAY);
    assert(near(middle->x->value(), end->x->value() / 2.0));
    assert(near(middle->y->value(), 0.0));
    assert(sketch.remove_constraint(midpoint));
    sketch.add_constraint(std::make_shared<PointLineDistanceConstraint>(middle, line, 2.0));
    assert(sketch.update() == SolveResult::OKAY);
    assert(near(std::abs(middle->y->value()), 2.0));

    // Temporary drag equations preserve hard constraints while moving free DOFs.
    auto drag_origin = point("drag_origin", 0.0, 0.0);
    auto drag_end = point("drag_end", 2.0, 0.0);
    auto drag_line = std::make_shared<LineE>(*drag_origin, *drag_end);
    Sketch drag_sketch;
    drag_sketch.add_entity(drag_line);
    drag_sketch.add_constraint(std::make_shared<FixedPointConstraint>(drag_origin));
    drag_sketch.add_constraint(std::make_shared<HVConstraint>(drag_line, HVOrientation::OX));
    assert(drag_sketch.update() == SolveResult::OKAY);
    assert(drag_sketch.drag_point(drag_end, 4.0, 2.0) == SolveResult::OKAY);
    assert(near(drag_end->x->value(), 4.0));
    assert(near(drag_end->y->value(), 0.0));

    // Stay goals keep unrelated contours stable during constrained dragging.
    auto outer0 = point("outer0", 0.0, 0.0);
    auto outer1 = point("outer1", 4.0, 0.0);
    auto inner0 = point("inner0", 0.0, 1.0);
    auto inner1 = point("inner1", 2.0, 1.0);
    auto outer_line = std::make_shared<LineE>(*outer0, *outer1);
    auto inner_line = std::make_shared<LineE>(*inner0, *inner1);
    Sketch stay_sketch;
    stay_sketch.add_entity(outer_line);
    stay_sketch.add_entity(inner_line);
    stay_sketch.add_constraint(std::make_shared<ParallelConstraint>(outer_line, inner_line));
    assert(stay_sketch.update() == SolveResult::OKAY);
    assert(stay_sketch.drag_point_with_stays(inner0, 0.0, 2.0, { outer0, outer1 })
           == SolveResult::OKAY);
    assert(near(outer0->x->value(), 0.0) && near(outer0->y->value(), 0.0));
    assert(near(outer1->x->value(), 4.0) && near(outer1->y->value(), 0.0));
    assert(near(inner0->y->value(), 2.0));

    // Directed angle and perpendicular constraints.
    auto a0 = point("a0", 0.0, 0.0);
    auto a1 = point("a1", 2.0, 0.0);
    auto b0 = point("b0", 0.0, 0.0);
    auto b1 = point("b1", 1.0, 1.0);
    auto base = std::make_shared<LineE>(*a0, *a1);
    auto rotated = std::make_shared<LineE>(*b0, *b1);
    Sketch angle_sketch;
    angle_sketch.add_entity(base);
    angle_sketch.add_entity(rotated);
    angle_sketch.add_constraint(std::make_shared<FixedPointConstraint>(a0));
    angle_sketch.add_constraint(std::make_shared<FixedPointConstraint>(a1));
    angle_sketch.add_constraint(std::make_shared<FixedPointConstraint>(b0));
    angle_sketch.add_constraint(std::make_shared<LengthConstraint>(rotated, 2.0));
    angle_sketch.add_constraint(std::make_shared<AngleConstraint>(base, rotated, M_PI_2));
    assert(angle_sketch.update() == SolveResult::OKAY);
    assert(near(b1->x->value(), 0.0));
    assert(near(b1->y->value(), 2.0));

    // Hyperbezier endpoint interpolation, tangent fitting, high tension, and global G2 joins.
    auto hyper = adjacent::HyperBezier::for_tangents(-0.4, 1.0, 0.3, 1.0);
    const auto hyper_start = hyper.point(0.0);
    const auto hyper_end = hyper.point(1.0);
    const auto hyper_measure = hyper.measure();
    assert(near(hyper_start[0], 0.0) && near(hyper_start[1], 0.0));
    assert(near(hyper_end[0], 1.0) && near(hyper_end[1], 0.0));
    assert(near(hyper_measure.theta0, -0.4));
    assert(near(hyper_measure.theta1, 0.3));
    auto tense = adjacent::HyperBezier::for_tangents(-1.1, 1.8, -0.8, 1.6);
    for (const auto& sample : tense.samples(20))
        assert(std::isfinite(sample[0]) && std::isfinite(sample[1]));

    adjacent::AutoHyperSpline auto_spline({ { 0.0, 0.0 }, { 1.0, 2.0 },
                                             { 3.0, 1.0 }, { 4.0, 3.0 } });
    const auto hyper_segments = auto_spline.segments();
    assert(hyper_segments.size() == 3);
    for (std::size_t i = 0; i + 1 < hyper_segments.size(); ++i)
        assert(near(hyper_segments[i].endpoint_curvatures()[1],
                    hyper_segments[i + 1].endpoint_curvatures()[0]));

    // Cubic Bezier evaluation, derivatives, symbolic quadrature, and parameter bounds.
    auto bezier_p0 = point("bezier_p0", 0.0, 0.0);
    auto bezier_p1 = point("bezier_p1", 1.0, 0.0);
    auto bezier_p2 = point("bezier_p2", 2.0, 0.0);
    auto bezier_p3 = point("bezier_p3", 3.0, 0.0);
    auto bezier = std::make_shared<CubicBezierE>(*bezier_p0, *bezier_p1, *bezier_p2,
                                                  *bezier_p3);
    assert(bezier->point_on(zero)->values_equals(bezier_p0->expr(), tolerance));
    assert(bezier->point_on(one)->values_equals(bezier_p3->expr(), tolerance));
    assert(near(bezier->point_on(expr(0.5))->x->eval(), 1.5));
    assert(near(bezier->tangent_at(zero)->x->eval(), 3.0));
    assert(near(bezier->length()->eval(), 3.0));
    auto bounded = param("bounded", 0.5);
    bounded->set_bounds(0.0, 1.0);
    bounded->set_value(2.0);
    assert(near(bounded->value(), 1.0));

    auto point_on_bezier = point("point_on_bezier", 1.5, 1.0);
    Sketch bezier_sketch;
    bezier_sketch.add_entity(bezier);
    bezier_sketch.add_entity(point_on_bezier);
    for (const auto& control : { bezier_p0, bezier_p1, bezier_p2, bezier_p3 })
        bezier_sketch.add_constraint(std::make_shared<FixedPointConstraint>(control));
    bezier_sketch.add_constraint(std::make_shared<PointOnConstraint>(point_on_bezier, bezier));
    assert(bezier_sketch.update() == SolveResult::OKAY);
    assert(near(point_on_bezier->y->value(), 0.0));
    assert(point_on_bezier->x->value() >= -tolerance
           && point_on_bezier->x->value() <= 3.0 + tolerance);

    // Circle dimensions and arc geometry.
    auto center = point("center", 10.0, 10.0);
    auto circle = std::make_shared<CircleE>(*center, param("radius", 1.0));
    sketch.add_entity(circle);
    EntityPtr circle_entity = circle;
    sketch.add_constraint(std::make_shared<FixedPointConstraint>(center));
    sketch.add_constraint(std::make_shared<DiameterConstraint>(circle_entity, 6.0));
    assert(sketch.update() == SolveResult::OKAY);
    assert(near(circle->_radius->value(), 3.0));

    ArcE arc(*center, param("arc_radius", 2.0), param("arc_start", 0.0),
             param("arc_sweep", M_PI_2));
    assert(near(arc.length()->eval(), M_PI));
    assert(near(arc.point_on(one)->x->eval(), 10.0));
    assert(near(arc.point_on(one)->y->eval(), 12.0));

    std::cout << "All adjacent solver tests passed\n";
    return 0;
}
