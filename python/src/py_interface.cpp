#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <adjacent/expression.hpp>
#include <adjacent/entity.hpp>
#include <adjacent/constraint.hpp>


namespace py = pybind11;

PYBIND11_MODULE(_adjacent, m)
{
    py::enum_<SolveResult>(m, "SolveResult")
        .value("OKAY", SolveResult::OKAY)
        .value("DIDNT_CONVERGE", SolveResult::DIDNT_CONVERGE)
        .value("REDUNDANT", SolveResult::REDUNDANT)
        .value("POSTPONE", SolveResult::POSTPONE);

    py::class_<Sketch>(m, "Sketch")
        .def(py::init<>())
        .def("add_entity", &Sketch::add_entity)
        .def("add_constraint", &Sketch::add_constraint)
        .def("remove_entity", &Sketch::remove_entity)
        .def("remove_constraint", &Sketch::remove_constraint)
        .def("drag_point", &Sketch::drag_point)
        .def("degrees_of_freedom", &Sketch::degrees_of_freedom)
        .def("update", &Sketch::update);

    using Prm = Param<double>;
    py::class_<Prm, std::shared_ptr<Prm>>(m, "Param")
        .def(py::init<std::string, double>())
        .def("set_value", &Prm::set_value)
        .def("set_bounds", &Prm::set_bounds)
        .def("value", &Prm::value)
        .def("name", [](Prm& self) { return self.m_name; })
        .def("__repr__", &Prm::to_string);

    py::class_<Entity, std::shared_ptr<Entity>>(m, "Entity");

    py::class_<PointE, Entity, std::shared_ptr<PointE>>(m, "Point")
        .def(py::init<double, double>())
        .def(py::init<ParamPtr, ParamPtr, ParamPtr>())
        .def("expr", &PointE::expr)
        .def_property_readonly("x", [](PointE& p) { return p.x; })
        .def_property_readonly("y", [](PointE& p) { return p.y; })
        .def("eval",
             [](PointE& p) {
                 return std::vector<double>({ p.x->value(), p.y->value() });
             })
        .def("__repr__", &PointE::to_string);

    py::class_<LineE, Entity, std::shared_ptr<LineE>>(m, "Line")
        .def(py::init<PointE, PointE>())
        .def("source", &LineE::source)
        .def("target", &LineE::target)
        // .def("expr", &LineE::expr)
        .def("__repr__", &LineE::to_string);

    py::class_<CubicBezierE, Entity, std::shared_ptr<CubicBezierE>>(m, "CubicBezier")
        .def(py::init<PointE, PointE, PointE, PointE>())
        .def("source", &CubicBezierE::source, py::return_value_policy::reference_internal)
        .def("target", &CubicBezierE::target, py::return_value_policy::reference_internal)
        .def("control_point", &CubicBezierE::control_point,
             py::return_value_policy::reference_internal)
        .def("eval", [](CubicBezierE& curve, double t) {
            auto point = curve.point_on(expr(t));
            return std::vector<double> { point->x->eval(), point->y->eval() };
        })
        .def("tangent", [](CubicBezierE& curve, double t) {
            auto tangent = curve.tangent_at(expr(t));
            return std::vector<double> { tangent->x->eval(), tangent->y->eval() };
        })
        .def("length", [](CubicBezierE& curve) { return curve.length()->eval(); })
        .def("__repr__", &CubicBezierE::to_string);

    py::class_<CircleE, Entity, std::shared_ptr<CircleE>>(m, "Circle")
        .def(py::init<PointE, ParamPtr>())
        .def("center", &CircleE::center, py::return_value_policy::reference_internal)
        .def("radius", &CircleE::radius)
        .def("__repr__", &CircleE::to_string);

    py::class_<ArcE, Entity, std::shared_ptr<ArcE>>(m, "Arc")
        .def(py::init<PointE, ParamPtr, ParamPtr, ParamPtr>())
        .def("center", &ArcE::center, py::return_value_policy::reference_internal)
        .def("radius", &ArcE::radius)
        .def("__repr__", &ArcE::to_string);

    py::module sub = m.def_submodule("constraints");

    py::class_<Constraint, std::shared_ptr<Constraint>>(sub, "Constraint");

    py::class_<ValueConstraint, Constraint, std::shared_ptr<ValueConstraint>>(sub, "ValueConstraint")
        .def("set_value", &ValueConstraint::set_value)
        .def("set_reference", &ValueConstraint::set_reference);

    py::class_<PointOnConstraint, ValueConstraint, std::shared_ptr<PointOnConstraint>>(
        sub, "PointOn")
        .def(py::init<std::shared_ptr<PointE>, EntityPtr>());

    py::class_<LengthConstraint, ValueConstraint, std::shared_ptr<LengthConstraint>>(
        sub, "Length")
        .def(py::init<EntityPtr, double>());

    py::class_<PointsCoincidentConstraint, Constraint, std::shared_ptr<PointsCoincidentConstraint>>(
        sub, "Coincident")
        .def(py::init<std::shared_ptr<PointE>&, std::shared_ptr<PointE>&>());

    py::class_<PointsDistanceConstraint,
               ValueConstraint,
               std::shared_ptr<PointsDistanceConstraint>>(sub, "Distance")
        .def(py::init<std::shared_ptr<PointE>&, std::shared_ptr<PointE>&, double>())
        .def(py::init<std::shared_ptr<LineE>&, double>());

    py::class_<AngleConstraint, ValueConstraint, std::shared_ptr<AngleConstraint>>(
        sub, "Angle")
        .def(py::init<std::shared_ptr<LineE>&, std::shared_ptr<LineE>&, double>());

    py::class_<DiameterConstraint,
               ValueConstraint,
               std::shared_ptr<DiameterConstraint>>(sub, "Diameter")
        .def(py::init<std::shared_ptr<Entity>&, double>());

    py::enum_<HVOrientation>(sub, "HVOrientation")
        .value("OX", HVOrientation::OX)
        .value("OY", HVOrientation::OY);

    py::class_<HVConstraint, Constraint, std::shared_ptr<HVConstraint>>(sub, "HV")
        .def(py::init<std::shared_ptr<PointE>, std::shared_ptr<PointE>, HVOrientation>())
        .def(py::init<std::shared_ptr<LineE>, HVOrientation>());

    py::class_<ParallelConstraint, Constraint, std::shared_ptr<ParallelConstraint>>(sub, "Parallel")
        .def(py::init<std::shared_ptr<LineE>&, std::shared_ptr<LineE>&>());

    py::class_<TangentConstraint, Constraint, std::shared_ptr<TangentConstraint>>(sub, "Tangent")
        .def(py::init<const EntityPtr&, const EntityPtr&>());

    py::class_<PerpendicularConstraint, Constraint, std::shared_ptr<PerpendicularConstraint>>(
        sub, "Perpendicular")
        .def(py::init<const std::shared_ptr<LineE>&, const std::shared_ptr<LineE>&>());
    py::class_<EqualLengthConstraint, Constraint, std::shared_ptr<EqualLengthConstraint>>(
        sub, "EqualLength")
        .def(py::init<const EntityPtr&, const EntityPtr&>());
    py::class_<EqualRadiusConstraint, Constraint, std::shared_ptr<EqualRadiusConstraint>>(
        sub, "EqualRadius")
        .def(py::init<const EntityPtr&, const EntityPtr&>());
    py::class_<FixedPointConstraint, Constraint, std::shared_ptr<FixedPointConstraint>>(
        sub, "FixedPoint")
        .def(py::init<const std::shared_ptr<PointE>&>())
        .def(py::init<const std::shared_ptr<PointE>&, double, double>());
    py::class_<MidpointConstraint, Constraint, std::shared_ptr<MidpointConstraint>>(sub, "Midpoint")
        .def(py::init<const std::shared_ptr<PointE>&, const std::shared_ptr<LineE>&>());
    py::class_<ConcentricConstraint, Constraint, std::shared_ptr<ConcentricConstraint>>(
        sub, "Concentric")
        .def(py::init<const EntityPtr&, const EntityPtr&>());
    py::class_<PointLineDistanceConstraint,
               ValueConstraint,
               std::shared_ptr<PointLineDistanceConstraint>>(sub, "PointLineDistance")
        .def(py::init<const std::shared_ptr<PointE>&, const std::shared_ptr<LineE>&, double>());

    py::class_<Expr, std::shared_ptr<Expr>>(m, "Expr")
        .def(py::init<double>())
        .def("eval", &Expr::eval)
        .def("__str__", &Expr::to_string)
        .def("__repr__", &Expr::to_string);

    py::class_<ExpVector, std::shared_ptr<ExpVector>>(m, "ExprVector")
        .def("__repr__", [](ExpVector& self) -> std::string {
            std::string res = "{\n";
            res += self.x->to_string() + "\n";
            res += self.y->to_string() + "\n";
            res += self.z->to_string() + "\n";
            res += "}";
            return res;
        });

    // py::implicitly_convertible<LineE, Entity>();
    // py::implicitly_convertible<PointE, Entity>();
}