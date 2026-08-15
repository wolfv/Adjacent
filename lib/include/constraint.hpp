#include <set>

#include "entity.hpp"
#include "expression.hpp"
#include "equation_system.hpp"

#ifndef ADJACENT_CONSTRAINT_HPP
#define ADJACENT_CONSTRAINT_HPP

enum CONSTRAINT_TYPE
{
    INVALID,
    PointOn,
    PointsCoincident,
    Parallel,
    Length,
    PointsDistance,
    HV,
    Angle,
    Diameter,
    Tangent,
    Perpendicular,
    EqualLength,
    EqualRadius,
    FixedPoint,
    Midpoint,
    Concentric,
    PointLineDistance
};

class Constraint;

using ConstraintPtr = std::shared_ptr<Constraint>;
using EntityPtr = std::shared_ptr<Entity>;

class Constraint
{
public:
    CONSTRAINT_TYPE type;
    std::vector<Entity*> entities;

    Constraint(CONSTRAINT_TYPE type)
        : type(type)
    {
    }
    virtual ~Constraint() = default;

    virtual std::vector<ParamPtr> parameters() = 0;
    virtual std::vector<ExprPtr> equations() = 0;
};

class ValueConstraint : public Constraint
{
public:
    ParamPtr value = param("c_value", 0);

    bool reference = false;

    ValueConstraint(CONSTRAINT_TYPE type)
        : Constraint(type)
    {
    }

    ValueConstraint(CONSTRAINT_TYPE type, double v)
        : Constraint(type)
    {
        value->set_value(v);
    }

    void set_reference(bool value)
    {
        reference = value;
        // mark dirty
    }

    virtual bool on_satisfy()
    {
        // protected virtual bool OnSatisfy() {
        EquationSystem sys;
        sys.revert_when_not_converged = false;
        sys.add_parameter(value);
        sys.add_equations(equations());
        return sys.solve() == SolveResult::OKAY;
    }

    bool satisfy()
    {
        bool result = on_satisfy();
        if (!result)
        {
            std::cout << "satisfy failed!";  // << GetType() +;
        }
        return result;
    }

    std::vector<ParamPtr> parameters()
    {
        if (!reference)
            return {};
        else
        {
            return { value };
        }
    }

    void set_value(double v)
    {
        // label to value for helix not implemented ...
        value->set_value(v);
    }
};

class PointOnConstraint : public ValueConstraint
{
public:
    std::shared_ptr<Entity> point;
    std::shared_ptr<Entity> on;

    PointOnConstraint(std::shared_ptr<PointE> point, std::shared_ptr<Entity> on)
        : ValueConstraint::ValueConstraint(PointOn)
        , point(point)
        , on(on)
    {
        // TODO Add runtime check that point is point, and on is some other entity!
        reference = true;
        entities.push_back(point.get());
        entities.push_back(on.get());
        value->set_bounds(0.0, 1.0);
        set_value(0.5);
    }

    bool on_satisfy()
    {
        EquationSystem sys;
        auto params = parameters();
        sys.add_parameters(params);
        auto exprs = equations();
        sys.add_equations(exprs);

        double bestI = 0.0;
        double min = -1.0;
        for (double i = 0.0; i <= 1.0; i += 0.25 / 2.0)
        {
            value->set_value(i);
            sys.solve();
            double cur_value = 0;
            for (const auto& e : exprs)
            {
                cur_value += abs(e->eval());
            }
            if (min >= 0.0 && min < cur_value)
                continue;
            bestI = value->value();
            min = cur_value;
        }
        value->set_value(bestI);
        return true;
    }

    std::vector<ExprPtr> equations()
    {
        std::vector<ExprPtr> res;
        // var eq = on.PointOnInPlane(value, sketch.plane) - p;
        ExpVector equation = *on->point_on(value->expr()) - ((PointE*) point.get())->expr();
        res.push_back(equation.x);
        res.push_back(equation.y);
        // if(sketch.is3d) yield return eq.z;
        return res;
    }
};

ExprPtr angle2d(const ExpVector& d0, const ExpVector& d1, bool angle360 = false)
{
    auto nu = d1.x * d0.x + d1.y * d0.y;
    auto nv = d0.x * d1.y - d0.y * d1.x;
    if (angle360)
        return PI_E - atan2(nv, -nu);
    return atan2(nv, nu);
}

class ParallelConstraint : public Constraint
{
public:
    enum Option
    {
        Codirected,
        Antidirected
    };

    Option option_ = Option::Codirected;

    ExprPtr angle;
    std::shared_ptr<Entity> l0, l1;

    ParallelConstraint(const std::shared_ptr<LineE>& l0, const std::shared_ptr<LineE>& l1)
        : Constraint(CONSTRAINT_TYPE::Parallel)
        , l0(l0)
        , l1(l1)
    {
        entities.push_back(l0.get());
        entities.push_back(l1.get());
    }

    std::vector<ExprPtr> equations()
    {
        // ExpVector d0 = l0.GetPointAtInPlane(0, sketch.plane) - l0.GetPointAtInPlane(1,
        // sketch.plane); ExpVector d1 = l1.GetPointAtInPlane(0, sketch.plane) -
        // l1.GetPointAtInPlane(1, sketch.plane);
        ExpVector d0 = *l0->point_on(zero) - *l0->point_on(one);
        ExpVector d1 = *l1->point_on(zero) - *l1->point_on(one);
        // ExprPtr angle = sketch.is3d ? ConstraintExp.angle3d(d0, d1) : ConstraintExp.angle2d(d0,
        // d1);
        // Collinearity is direction independent and avoids the discontinuity of
        // atan2/abs at +/-pi.
        return { d0.x * d1.y - d0.y * d1.x };
    }

    std::vector<ParamPtr> parameters()
    {
        return {};
    }
};

class LengthConstraint : public ValueConstraint
{
public:
    std::shared_ptr<Entity> entity;

    LengthConstraint(std::shared_ptr<Entity> e, double l)
        : ValueConstraint(CONSTRAINT_TYPE::Length, l)
        , entity(e)
    {
        entities.push_back(e.get());
        value->set_value(l);
    }

    std::vector<ExprPtr> equations()
    {
        return { entity->length() - value->expr() };
    }
};

class PointsCoincidentConstraint : public Constraint
{
public:
    std::shared_ptr<PointE> p0, p1;

    PointsCoincidentConstraint(const std::shared_ptr<PointE>& p0, const std::shared_ptr<PointE>& p1)
        : Constraint(CONSTRAINT_TYPE::PointsCoincident)
        , p0(p0)
        , p1(p1)
    {
        entities.push_back(p0.get());
        entities.push_back(p1.get());
    }

    std::vector<ExprPtr> equations()
    {
        // var pe0 = p0.GetPointAtInPlane(0, sketch.plane);
        // var pe1 = p1.GetPointAtInPlane(0, sketch.plane);

        return std::vector<ExprPtr>(
            { p0->x->expr() - p1->x->expr(), p0->y->expr() - p1->y->expr() });
        // if 3d
        // if(sketch.is3d) yield return pe0.z - pe1.z;
    }

    std::vector<ParamPtr> parameters()
    {
        return {};
    }

    std::shared_ptr<PointE>& get_other_point(const std::shared_ptr<PointE>& p)
    {
        if (p0 == p)
            return p1;
        return p0;
    }
};

class PointsDistanceConstraint : public ValueConstraint
{
public:
    EntityPtr p0, p1;

    PointsDistanceConstraint(const std::shared_ptr<PointE>& p0, const std::shared_ptr<PointE>& p1,
                             double d)
        : ValueConstraint(CONSTRAINT_TYPE::PointsDistance, d)
        , p0(p0)
        , p1(p1)
    {
        entities.push_back(p0.get());
        entities.push_back(p1.get());
    }

    PointsDistanceConstraint(const std::shared_ptr<LineE>& line, double d)
        : ValueConstraint(CONSTRAINT_TYPE::PointsDistance, d)
        , p0(line)
        , p1(nullptr)
    {
        entities.push_back(line.get());
    }

    std::vector<ExprPtr> equations()
    {
        return std::vector<ExprPtr>({ // TODO caching
                                      (get_point(1) - get_point(0)).magnitude() - value->expr() });
    }

    ExpVector get_point(double i)
    {
        if (p1 == nullptr)
        {
            return i ? dynamic_cast<LineE*>(p0.get())->source().expr()
                     : dynamic_cast<LineE*>(p0.get())->target().expr();
        }
        else
        {
            return i ? dynamic_cast<PointE*>(p0.get())->expr()
                     : dynamic_cast<PointE*>(p1.get())->expr();
        }
    }
};

enum HVOrientation
{
    OX,
    OY,
    // OZ
};

class HVConstraint : public Constraint
{
public:
    PointE* p0;
    PointE* p1;

    HVOrientation orientation = HVOrientation::OX;

    HVConstraint(std::shared_ptr<PointE> p0, std::shared_ptr<PointE> p1, HVOrientation o)
        : Constraint(CONSTRAINT_TYPE::HV)
        , p0(p0.get())
        , p1(p1.get())
        , orientation(o)
    {
        entities.push_back(p0.get());
        entities.push_back(p1.get());
    }

    HVConstraint(std::shared_ptr<LineE> line, HVOrientation o)
        : Constraint(CONSTRAINT_TYPE::HV)
        , p0(&(line.get())->source())
        , p1(&(line.get())->target())
        , orientation(o)
    {
        entities.push_back(line.get());
    }

    std::vector<ExprPtr> equations()
    {
        ExprPtr exp;
        switch (orientation)
        {
            case HVOrientation::OX: // segment parallel to the x axis
                exp = p0->y->expr() - p1->y->expr();
                break;
            case HVOrientation::OY: // segment parallel to the y axis
                exp = p0->x->expr() - p1->x->expr();
                break;
                // case HVOrientation::OZ: exp = p0->z->expr() - p1->z->expr(); break;
        }

        return std::vector<ExprPtr>({ exp });
    }

    std::vector<ParamPtr> parameters()
    {
        return {};
    }
};

template <class T>
T sgn(const T& x)
{
    return (x < T(0)) ? T(-1) : T(+1);
}

class AngleConstraint : public ValueConstraint
{
public:
    bool supplementary = false; // retained for source compatibility
    // AngleConstraint(PointE)

    // AngleConstraint(Arc);

    AngleConstraint(const std::shared_ptr<LineE>& l0, const std::shared_ptr<LineE>& l1, double angle)
        : ValueConstraint(CONSTRAINT_TYPE::Angle, angle)
    {
        entities.push_back(l0.get());
        entities.push_back(l1.get());
        // satisfy();
        value->set_value(angle);
    }

    std::vector<ExprPtr> equations()
    {
        auto pts = get_points();
        auto d0 = pts[1] - pts[0];
        auto d1 = pts[3] - pts[2];
        return { angle2d(d0, d1) - value->expr() };
    }

    std::array<ExpVector, 4> get_points()
    {
        auto* l0 = dynamic_cast<LineE*>(entities[0]);
        auto* l1 = dynamic_cast<LineE*>(entities[1]);
        return { *l0->point_on(zero), *l0->point_on(one), *l1->point_on(zero),
                 *l1->point_on(one) };
    }
};

class DiameterConstraint : public ValueConstraint
{
public:
    // bool showAsRadius = false;
    EntityPtr e;

    DiameterConstraint(const EntityPtr& entity, double diameter)
        : ValueConstraint(CONSTRAINT_TYPE::Diameter, diameter)
        , e(entity)
    {
        // showAsRadius = (c.type == IEntityType.Arc);
        entities.push_back(entity.get());
        // satisfy();
        value->set_value(diameter);
    }

    std::vector<ExprPtr> equations()
    {
        return { e->radius() * two - value->expr() };
    }
};

class PerpendicularConstraint : public Constraint
{
public:
    std::shared_ptr<LineE> l0, l1;
    PerpendicularConstraint(const std::shared_ptr<LineE>& a, const std::shared_ptr<LineE>& b)
        : Constraint(CONSTRAINT_TYPE::Perpendicular), l0(a), l1(b)
    {
        entities = { a.get(), b.get() };
    }
    std::vector<ParamPtr> parameters() override { return {}; }
    std::vector<ExprPtr> equations() override
    {
        auto a = l0->target().expr() - l0->source().expr();
        auto b = l1->target().expr() - l1->source().expr();
        return { dot(a, b) };
    }
};

class EqualLengthConstraint : public Constraint
{
public:
    EntityPtr a, b;
    EqualLengthConstraint(const EntityPtr& a, const EntityPtr& b)
        : Constraint(CONSTRAINT_TYPE::EqualLength), a(a), b(b)
    {
        entities = { a.get(), b.get() };
    }
    std::vector<ParamPtr> parameters() override { return {}; }
    std::vector<ExprPtr> equations() override { return { a->length() - b->length() }; }
};

class EqualRadiusConstraint : public Constraint
{
public:
    EntityPtr a, b;
    EqualRadiusConstraint(const EntityPtr& a, const EntityPtr& b)
        : Constraint(CONSTRAINT_TYPE::EqualRadius), a(a), b(b)
    {
        entities = { a.get(), b.get() };
    }
    std::vector<ParamPtr> parameters() override { return {}; }
    std::vector<ExprPtr> equations() override { return { a->radius() - b->radius() }; }
};

class FixedPointConstraint : public Constraint
{
public:
    std::shared_ptr<PointE> point;
    double fixed_x, fixed_y;
    explicit FixedPointConstraint(const std::shared_ptr<PointE>& point)
        : Constraint(CONSTRAINT_TYPE::FixedPoint), point(point), fixed_x(point->x->value()),
          fixed_y(point->y->value())
    {
        entities = { point.get() };
    }
    FixedPointConstraint(const std::shared_ptr<PointE>& point, double x, double y)
        : Constraint(CONSTRAINT_TYPE::FixedPoint), point(point), fixed_x(x), fixed_y(y)
    {
        entities = { point.get() };
    }
    std::vector<ParamPtr> parameters() override { return {}; }
    std::vector<ExprPtr> equations() override
    {
        return { point->x->expr() - expr(fixed_x), point->y->expr() - expr(fixed_y) };
    }
};

class MidpointConstraint : public Constraint
{
public:
    std::shared_ptr<PointE> point;
    std::shared_ptr<LineE> line;
    MidpointConstraint(const std::shared_ptr<PointE>& point, const std::shared_ptr<LineE>& line)
        : Constraint(CONSTRAINT_TYPE::Midpoint), point(point), line(line)
    {
        entities = { point.get(), line.get() };
    }
    std::vector<ParamPtr> parameters() override { return {}; }
    std::vector<ExprPtr> equations() override
    {
        auto delta = point->expr() - *line->point_on(expr(0.5));
        return { delta.x, delta.y };
    }
};

class ConcentricConstraint : public Constraint
{
public:
    EntityPtr a, b;
    ConcentricConstraint(const EntityPtr& a, const EntityPtr& b)
        : Constraint(CONSTRAINT_TYPE::Concentric), a(a), b(b)
    {
        entities = { a.get(), b.get() };
    }
    std::vector<ParamPtr> parameters() override { return {}; }
    std::vector<ExprPtr> equations() override
    {
        auto center_of = [](const EntityPtr& e) -> PointE& {
            if (auto circle = dynamic_cast<CircleE*>(e.get())) return circle->center();
            if (auto arc = dynamic_cast<ArcE*>(e.get())) return arc->center();
            throw std::invalid_argument("Concentric requires circles or arcs");
        };
        auto delta = center_of(a).expr() - center_of(b).expr();
        return { delta.x, delta.y };
    }
};

class PointLineDistanceConstraint : public ValueConstraint
{
public:
    std::shared_ptr<PointE> point;
    std::shared_ptr<LineE> line;
    double side;
    PointLineDistanceConstraint(const std::shared_ptr<PointE>& point,
                                const std::shared_ptr<LineE>& line, double distance)
        : ValueConstraint(CONSTRAINT_TYPE::PointLineDistance, distance), point(point), line(line),
          side(1.0)
    {
        if (distance < 0.0) throw std::invalid_argument("Distance must be non-negative");
        const double dx = line->target().x->value() - line->source().x->value();
        const double dy = line->target().y->value() - line->source().y->value();
        const double qx = point->x->value() - line->source().x->value();
        const double qy = point->y->value() - line->source().y->value();
        if (dx * qy - dy * qx < 0.0) side = -1.0;
        entities = { point.get(), line.get() };
    }
    std::vector<ExprPtr> equations() override
    {
        auto d = line->target().expr() - line->source().expr();
        auto q = point->expr() - line->source().expr();
        auto area = d.x * q.y - d.y * q.x;
        return { area - expr(side) * value->expr() * sqrt(sqr(d.x) + sqr(d.y)) };
    }
};

class TangentConstraint : public Constraint
{
public:
    ParamPtr t0 = param("tangent_circle_t", 0.0);
    ParamPtr t1 = param("tangent_line_t", 0.5);

    TangentConstraint(const EntityPtr& first, const EntityPtr& second)
        : Constraint(CONSTRAINT_TYPE::Tangent)
    {
        if (!first->tangent_at(zero) || !second->tangent_at(zero))
            throw std::invalid_argument("Tangent requires two curve entities");
        entities = { first.get(), second.get() };
        t0->set_bounds(0.0, 1.0);
        t1->set_bounds(0.0, 1.0);
    }

    std::vector<ParamPtr> parameters() override { return { t0, t1 }; }

    std::vector<ExprPtr> equations() override
    {
        auto* circle = entities[0];
        auto* line = entities[1];
        auto circle_tangent = circle->tangent_at(t0->expr());
        auto line_tangent = line->tangent_at(t1->expr());
        auto coincidence = *line->point_on(t1->expr()) - *circle->point_on(t0->expr());
        return { circle_tangent->x * line_tangent->y
                     - circle_tangent->y * line_tangent->x,
                 coincidence.x, coincidence.y };
    }
};

class Sketch
{
public:
    bool constraintsTopologyChanged = true;
    bool constraintsChanged = true;
    bool entitiesChanged = true;
    bool loopsChanged = true;
    bool topologyChanged = true;
    bool supressSolve = false;
    EquationSystem sys;

    std::set<EntityPtr> entities;
    std::set<ConstraintPtr> constraints;

    void add_entity(const EntityPtr& e)
    {
        if (entities.find(e) != entities.end())
            return;
        entities.insert(e);
        mark_dirty(/*topo*/ true, /*constraints*/ false, /*entities*/ true, /*loops*/ false);
    }

    void mark_dirty(bool topo, bool constraints, bool entities, bool loops)
    {
        topologyChanged = topologyChanged || topo;
        constraintsChanged = constraintsChanged || constraints;
        constraintsTopologyChanged = constraintsTopologyChanged || constraints;
        entitiesChanged = entitiesChanged || entities;
        loopsChanged = loopsChanged || loops;
    }

    void add_constraint(const ConstraintPtr& c)
    {
        if (constraints.find(c) != constraints.end())
            return;
        constraints.insert(c);
        mark_dirty(/*topo*/ c->type == PointsCoincident,
                   /*constraints*/ true,
                   /*entities*/ false,
                   /*loops*/ false);
        constraintsTopologyChanged = true;
    }

    bool is_dirty() const
    {
        return constraintsTopologyChanged || constraintsChanged || entitiesChanged || loopsChanged
               || topologyChanged;
    }

    bool is_entities_changed() const
    {
        return entitiesChanged;
    }

    bool is_constraints_changed() const
    {
        return constraintsChanged;
    }
    bool is_topology_changed() const
    {
        return topologyChanged;
    }

    bool remove_entity(const EntityPtr& e)
    {
        if (entities.erase(e) == 0) return false;
        mark_dirty(true, false, true, true);
        return true;
    }

    bool remove_constraint(const ConstraintPtr& c)
    {
        if (constraints.erase(c) == 0) return false;
        mark_dirty(c->type == PointsCoincident, true, false, false);
        constraintsTopologyChanged = true;
        return true;
    }

    SolveResult update()
    {
        const bool rebuild = constraintsTopologyChanged || constraintsChanged || entitiesChanged
                             || topologyChanged;
        if (rebuild)
        {
            supressSolve = false;
            sys.clear();
            generate_equations(sys);
        }
        const auto result = (!supressSolve || sys.has_dragged()) ? sys.solve() : DIDNT_CONVERGE;
        supressSolve = result == DIDNT_CONVERGE;
        constraintsTopologyChanged = constraintsChanged = entitiesChanged = loopsChanged
            = topologyChanged = false;
        return result;
    }

    SolveResult drag_point(const std::shared_ptr<PointE>& point, double x, double y)
    {
        // Ensure the persistent system is current before adding temporary soft
        // equations. Drag equations influence the first Newton iterations and are
        // then dropped so hard constraints always win.
        if (is_dirty())
            update();
        auto drag_x = point->x->expr()->drag(expr(x));
        auto drag_y = point->y->expr()->drag(expr(y));
        sys.add_equation(drag_x);
        sys.add_equation(drag_y);
        const auto result = sys.solve();
        sys.remove_equation(drag_x);
        sys.remove_equation(drag_y);
        return result;
    }

    int degrees_of_freedom()
    {
        int dof = 0;
        sys.update_dirty();
        sys.test_rank(dof);
        return dof;
    }

    void generate_equations(EquationSystem& system)
    {
        for (const auto& en : entities)
        {
            system.add_parameters(en->parameters());
            // system.add_equations(en->equations());
        }
        for (const auto& c : constraints)
        {
            system.add_parameters(c->parameters());
            system.add_equations(c->equations());
        }
    }
};

#endif