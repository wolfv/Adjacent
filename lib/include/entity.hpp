#include "expression.hpp"
#include "expression_vector.hpp"

#include <xtensor/xtensor.hpp>

#ifndef ADJACENT_ENTITY_HPP
#define ADJACENT_ENTITY_HPP

using ExpVectorPtr = std::shared_ptr<ExpVector>;

class Entity
{
public:
    virtual ~Entity() = default;
    // virtual std::shared_ptr<ExpVector> get_points() = 0;
    // virtual std::shared_ptr<ExpVector> get_segments() = 0;
    virtual std::string to_string() = 0;
    virtual ExpVectorPtr point_on(const ExprPtr& t) = 0;
    virtual ExpVectorPtr tangent_at(const ExprPtr& t) = 0;
    virtual ExprPtr length() = 0;
    virtual ExprPtr radius() = 0;

    virtual std::vector<ParamPtr> parameters() = 0;
    // virtual std::vector<ExprPtr> equations() = 0;
    // virtual ExpVectorPtr center() = 0;
};

class PointE : public Entity
{
public:
    ParamPtr x, y, z;
    std::shared_ptr<ExpVector> exp_;

    PointE()
        : PointE(0.0, 0.0)
    {
    }
    PointE(double x_value, double y_value)
        : x(param("x", x_value))
        , y(param("y", y_value))
        , z(param("z", 0.0))
    {
    }
    PointE(const ParamPtr& x, const ParamPtr& y, const ParamPtr& z)
        : x(x)
        , y(y)
        , z(z)
    {
    }

    // PointE& PointE(const PointE&) = default;

    std::string to_string()
    {
        return "Point(" + x->to_string() + ", " + y->to_string() + ", " + z->to_string() + ")";
    }

    ExpVector expr()
    {
        if (exp_ == nullptr)
        {
            exp_ = std::make_shared<ExpVector>(x->expr(), y->expr(), z->expr());
        }
        // TODO transform
        return *exp_;
    }

    bool is_changed()
    {
        return x->m_changed || y->m_changed || z->m_changed;
    }

    std::vector<ParamPtr> parameters()
    {
        if (is_3d())
        {
            return { x, y, z };
        }
        return { x, y };
    }

    // points()

    bool is_3d()
    {
        return false;
    }

    void on_drag(const xt::xtensor<double, 1>& delta)
    {
        x->set_value(x->value() + delta[0]);
        y->set_value(y->value() + delta[1]);
        if (is_3d())
        {
            z->set_value(z->value() + delta[2]);
        }
    }

    std::shared_ptr<ExpVector> tangent_at(const ExprPtr&)
    {
        return nullptr;
    }

    ExpVectorPtr point_on(const ExprPtr&)
    {
        return std::make_shared<ExpVector>(expr());
    }
    ExprPtr length()
    {
        return nullptr;
    }
    ExprPtr radius()
    {
        return nullptr;
    }
};

class CircleE : public Entity
{
public:
    PointE _center;
    ParamPtr _radius;

    CircleE(const PointE& center, const ParamPtr& radius)
        : _center(center)
        , _radius(radius)
    {
    }

    std::vector<ParamPtr> parameters()
    {
        std::vector<ParamPtr> res = _center.parameters();
        res.push_back(_radius);
        return res;
    }

    std::string to_string()
    {
        return "Circle(" + _center.to_string() + ", " + _radius->to_string() + ")";
    }

    ExpVectorPtr tangent_at(const ExprPtr& t)
    {
        auto angle = t * PI2_E;
        return std::make_shared<ExpVector>(-sin(angle), cos(angle), zero);
    }

    PointE& center()
    {
        return _center;
    }

    ExprPtr radius()
    {
        return abs(_radius->expr());
    }

    ExprPtr length()
    {
        return PI2_E * radius();
    }

    ExpVectorPtr point_on(const ExprPtr& t)
    {
        auto angle = t * PI2_E;
        return std::make_shared<ExpVector>(_center.expr()
                                           + ExpVector(cos(angle), sin(angle), zero) * radius());
    }
};

// Circular arc parameterized from t=0 (start angle) to t=1 (start+sweep).
class ArcE : public Entity
{
public:
    PointE _center;
    ParamPtr _radius, _start_angle, _sweep_angle;

    ArcE(const PointE& center, const ParamPtr& radius, const ParamPtr& start_angle,
         const ParamPtr& sweep_angle)
        : _center(center)
        , _radius(radius)
        , _start_angle(start_angle)
        , _sweep_angle(sweep_angle)
    {
    }

    std::vector<ParamPtr> parameters() override
    {
        auto result = _center.parameters();
        result.insert(result.end(), { _radius, _start_angle, _sweep_angle });
        return result;
    }
    std::string to_string() override
    {
        return "Arc(" + _center.to_string() + ", r=" + _radius->to_string() + ")";
    }
    PointE& center() { return _center; }
    ExprPtr radius() override { return abs(_radius->expr()); }
    ExprPtr length() override { return radius() * abs(_sweep_angle->expr()); }
    ExpVectorPtr point_on(const ExprPtr& t) override
    {
        auto angle = _start_angle->expr() + t * _sweep_angle->expr();
        return std::make_shared<ExpVector>(_center.expr()
                                           + ExpVector(cos(angle), sin(angle), zero) * radius());
    }
    ExpVectorPtr tangent_at(const ExprPtr& t) override
    {
        auto angle = _start_angle->expr() + t * _sweep_angle->expr();
        return std::make_shared<ExpVector>(-sin(angle) * _sweep_angle->expr(),
                                           cos(angle) * _sweep_angle->expr(), zero);
    }
};

class SegmentaryEntity
{
public:
    virtual ~SegmentaryEntity() = default;
    virtual PointE& source() = 0;
    virtual PointE& target() = 0;
};

class CubicBezierE
    : public Entity
    , public SegmentaryEntity
{
public:
    PointE p0, p1, p2, p3;

    CubicBezierE(const PointE& p0, const PointE& p1, const PointE& p2, const PointE& p3)
        : p0(p0), p1(p1), p2(p2), p3(p3)
    {
    }

    PointE& source() override { return p0; }
    PointE& target() override { return p3; }
    PointE& control_point(std::size_t index)
    {
        switch (index)
        {
            case 0: return p0;
            case 1: return p1;
            case 2: return p2;
            case 3: return p3;
            default: throw std::out_of_range("Bezier control point index must be 0..3");
        }
    }

    std::vector<ParamPtr> parameters() override
    {
        std::vector<ParamPtr> result;
        for (PointE* point : { &p0, &p1, &p2, &p3 })
        {
            auto point_parameters = point->parameters();
            result.insert(result.end(), point_parameters.begin(), point_parameters.end());
        }
        return result;
    }

    std::string to_string() override
    {
        return "CubicBezier(" + p0.to_string() + " -> " + p3.to_string() + ")";
    }

    ExpVectorPtr point_on(const ExprPtr& t) override
    {
        auto u = one - t;
        auto value = p0.expr() * (u * u * u)
                     + p1.expr() * (expr(3.0) * u * u * t)
                     + p2.expr() * (expr(3.0) * u * t * t)
                     + p3.expr() * (t * t * t);
        return std::make_shared<ExpVector>(value);
    }

    ExpVectorPtr tangent_at(const ExprPtr& t) override
    {
        auto u = one - t;
        auto value = (p1.expr() - p0.expr()) * (expr(3.0) * u * u)
                     + (p2.expr() - p1.expr()) * (expr(6.0) * u * t)
                     + (p3.expr() - p2.expr()) * (expr(3.0) * t * t);
        return std::make_shared<ExpVector>(value);
    }

    ExprPtr length() override
    {
        // Eight-point Gauss-Legendre quadrature on [0, 1]. This is accurate for
        // interactive CAD use and remains a symbolic, differentiable expression.
        static constexpr double nodes[] = {
            -0.9602898564975363, -0.7966664774136267, -0.5255324099163290,
            -0.1834346424956498,  0.1834346424956498,  0.5255324099163290,
             0.7966664774136267,  0.9602898564975363
        };
        static constexpr double weights[] = {
            0.1012285362903763, 0.2223810344533745, 0.3137066458778873,
            0.3626837833783620, 0.3626837833783620, 0.3137066458778873,
            0.2223810344533745, 0.1012285362903763
        };
        ExprPtr result = zero;
        for (std::size_t i = 0; i < 8; ++i)
        {
            auto t = expr(0.5 * (nodes[i] + 1.0));
            result = result + tangent_at(t)->magnitude() * expr(0.5 * weights[i]);
        }
        return result;
    }

    ExprPtr radius() override { return nullptr; }
};

class LineE
    : public Entity
    , public SegmentaryEntity
{
public:
    PointE p0, p1;

    LineE(const PointE& p0, const PointE& p1)
        : p0(p0)
        , p1(p1)
    {
    }

    std::vector<ParamPtr> parameters()
    {
        std::vector<ParamPtr> res = p0.parameters();
        std::vector<ParamPtr> p1_p = p1.parameters();

        copy(p1_p.begin(), p1_p.end(), back_inserter(res));
        return res;
    }

    bool is_changed()
    {
        return p0.is_changed() || p1.is_changed();
    }

    PointE& source()
    {
        return p0;
    }

    PointE& target()
    {
        return p1;
    }

    std::string to_string()
    {
        return std::string("Line(") + p0.to_string() + " -> " + p1.to_string() + ")";
    }

    ExpVectorPtr point_on(const ExprPtr& t)
    {
        return std::make_shared<ExpVector>(p0.expr() + (p1.expr() - p0.expr()) * t);
    }

    ExpVectorPtr tangent_at(const ExprPtr&)
    {
        return std::make_shared<ExpVector>(p1.expr() - p0.expr());
    }

    ExprPtr length()
    {
        return (p1.expr() - p0.expr()).magnitude();
    }

    ExprPtr radius()
    {
        return nullptr;
    }
};

#endif