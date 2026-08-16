#include <emscripten/bind.h>

#include <hyperbezier.hpp>
#include <constraint.hpp>

#include <algorithm>
#include <vector>

using adjacent::AutoHyperSpline;
using adjacent::HyperBezier;
using adjacent::HyperPoint;
using adjacent::HyperSegment;
using emscripten::val;

namespace
{
class WebCircleLineTangentConstraint : public Constraint
{
public:
    WebCircleLineTangentConstraint(const std::shared_ptr<CircleE>& circle,
                                   const std::shared_ptr<LineE>& line)
        : Constraint(CONSTRAINT_TYPE::Tangent), m_circle(circle), m_line(line)
    {
        const double dx = line->target().x->value() - line->source().x->value();
        const double dy = line->target().y->value() - line->source().y->value();
        const double qx = circle->center().x->value() - line->source().x->value();
        const double qy = circle->center().y->value() - line->source().y->value();
        m_side = dx * qy - dy * qx < 0.0 ? -1.0 : 1.0;
        entities = { circle.get(), line.get() };
    }
    std::vector<ParamPtr> parameters() override { return {}; }
    std::vector<ExprPtr> equations() override
    {
        const auto d = m_line->target().expr() - m_line->source().expr();
        const auto q = m_circle->center().expr() - m_line->source().expr();
        const auto area = d.x * q.y - d.y * q.x;
        return { area - expr(m_side) * m_circle->radius()
                            * sqrt(sqr(d.x) + sqr(d.y)) };
    }
private:
    std::shared_ptr<CircleE> m_circle;
    std::shared_ptr<LineE> m_line;
    double m_side = 1.0;
};

class WebConstraintSketch
{
public:
    unsigned add_point(double x, double y)
    {
        auto p = std::make_shared<PointE>(x, y);
        points.push_back(p);
        sketch.add_entity(p);
        return points.size() - 1;
    }

    unsigned add_line(unsigned a, unsigned b)
    {
        auto entity = std::make_shared<LineE>(*point(a), *point(b));
        lines.push_back(entity);
        sketch.add_entity(entity);
        return lines.size() - 1;
    }

    unsigned add_circle(unsigned center, double radius)
    {
        auto entity = std::make_shared<CircleE>(*point(center),
                                                param("web_radius", radius));
        circles.push_back(entity);
        sketch.add_entity(entity);
        return circles.size() - 1;
    }

    int solve() { return static_cast<int>(sketch.update()); }

    int drag_point(unsigned id, double x, double y)
    {
        std::vector<std::shared_ptr<PointE>> stays;
        for (unsigned i = 0; i < points.size(); ++i)
            if (i != id)
                stays.push_back(points[i]);
        return static_cast<int>(sketch.drag_point_with_stays(point(id), x, y, stays));
    }

    val geometry()
    {
        val result = val::object();
        val js_points = val::array();
        for (unsigned i = 0; i < points.size(); ++i)
        {
            js_points.set(i * 2, points[i]->x->value());
            js_points.set(i * 2 + 1, points[i]->y->value());
        }
        val radii = val::array();
        for (unsigned i = 0; i < circles.size(); ++i)
            radii.set(i, circles[i]->radius()->eval());
        result.set("points", js_points);
        result.set("radii", radii);
        result.set("dof", sketch.degrees_of_freedom());
        return result;
    }

    int fixed(unsigned p) { return add(std::make_shared<FixedPointConstraint>(point(p))); }
    int coincident(unsigned a, unsigned b)
    {
        auto pa = point(a), pb = point(b);
        return add(std::make_shared<PointsCoincidentConstraint>(pa, pb));
    }
    int horizontal(unsigned l)
    {
        return add(std::make_shared<HVConstraint>(line(l), HVOrientation::OX));
    }
    int vertical(unsigned l)
    {
        return add(std::make_shared<HVConstraint>(line(l), HVOrientation::OY));
    }
    int distance(unsigned a, unsigned b, double value)
    {
        auto pa = point(a), pb = point(b);
        return add(std::make_shared<PointsDistanceConstraint>(pa, pb, value));
    }
    int length(unsigned l, double value)
    {
        return add(std::make_shared<LengthConstraint>(line(l), value));
    }
    int parallel(unsigned a, unsigned b)
    {
        auto la = line(a), lb = line(b);
        return add(std::make_shared<ParallelConstraint>(la, lb));
    }
    int perpendicular(unsigned a, unsigned b)
    {
        return add(std::make_shared<PerpendicularConstraint>(line(a), line(b)));
    }
    int equal_length(unsigned a, unsigned b)
    {
        return add(std::make_shared<EqualLengthConstraint>(line(a), line(b)));
    }
    int midpoint(unsigned p, unsigned l)
    {
        return add(std::make_shared<MidpointConstraint>(point(p), line(l)));
    }
    int point_on_line(unsigned p, unsigned l)
    {
        return add(std::make_shared<PointOnConstraint>(point(p), line(l)));
    }
    int point_line_distance(unsigned p, unsigned l, double value)
    {
        return add(std::make_shared<PointLineDistanceConstraint>(point(p), line(l), value));
    }
    int diameter(unsigned c, double value)
    {
        EntityPtr entity = circle(c);
        return add(std::make_shared<DiameterConstraint>(entity, value));
    }
    int equal_radius(unsigned a, unsigned b)
    {
        EntityPtr ca = circle(a), cb = circle(b);
        return add(std::make_shared<EqualRadiusConstraint>(ca, cb));
    }
    int concentric(unsigned a, unsigned b)
    {
        EntityPtr ca = circle(a), cb = circle(b);
        return add(std::make_shared<ConcentricConstraint>(ca, cb));
    }
    int tangent(unsigned c, unsigned l)
    {
        return add(std::make_shared<WebCircleLineTangentConstraint>(circle(c), line(l)));
    }
    int angle(unsigned a, unsigned b, double radians)
    {
        auto la = line(a), lb = line(b);
        return add(std::make_shared<AngleConstraint>(la, lb, radians));
    }
    int remove_last_constraint()
    {
        if (constraints.empty())
            return solve();
        sketch.remove_constraint(constraints.back());
        constraints.pop_back();
        return solve();
    }

private:
    Sketch sketch;
    std::vector<std::shared_ptr<PointE>> points;
    std::vector<std::shared_ptr<LineE>> lines;
    std::vector<std::shared_ptr<CircleE>> circles;
    std::vector<ConstraintPtr> constraints;

    std::shared_ptr<PointE> point(unsigned id) const { return points.at(id); }
    std::shared_ptr<LineE> line(unsigned id) const { return lines.at(id); }
    std::shared_ptr<CircleE> circle(unsigned id) const { return circles.at(id); }
    int add(const ConstraintPtr& constraint)
    {
        constraints.push_back(constraint);
        sketch.add_constraint(constraint);
        return solve();
    }
};

class WebHyperSpline
{
public:
    void set_points(const val& coordinates, const val& smooth)
    {
        const auto count = coordinates["length"].as<unsigned>() / 2;
        points.clear();
        smooth_points.clear();
        points.reserve(count);
        smooth_points.reserve(count);
        for (unsigned i = 0; i < count; ++i)
        {
            points.push_back({ coordinates[i * 2].as<double>(), coordinates[i * 2 + 1].as<double>() });
            smooth_points.push_back(i < smooth["length"].as<unsigned>()
                                        ? smooth[i].as<bool>() : true);
        }
        manual.resize(count > 0 ? count - 1 : 0);
    }

    void set_manual_handle(unsigned segment, unsigned side, double x, double y)
    {
        if (segment >= manual.size() || side > 1)
            return;
        if (!manual[segment].active)
        {
            const auto solved = solved_segments();
            if (segment < solved.size())
            {
                const auto handles = solved[segment].auto_handles();
                manual[segment].handles = handles;
            }
        }
        manual[segment].active = true;
        manual[segment].handles[side] = { x, y };
    }

    void reset_handle(unsigned segment)
    {
        if (segment < manual.size())
            manual[segment].active = false;
    }

    val solve(unsigned sample_count) const
    {
        sample_count = std::clamp(sample_count, 4u, 256u);
        const auto segments = solved_segments();
        val result = val::object();
        val paths = val::array();
        val handles = val::array();
        val curvatures = val::array();
        for (unsigned i = 0; i < segments.size(); ++i)
        {
            const auto samples = segments[i].samples(sample_count);
            val path = val::array();
            for (unsigned j = 0; j < samples.size(); ++j)
            {
                path.set(j * 2, samples[j][0]);
                path.set(j * 2 + 1, samples[j][1]);
            }
            paths.set(i, path);
            const auto hs = manual[i].active ? manual[i].handles : segments[i].auto_handles();
            val handle = val::array();
            handle.set(0, hs[0][0]); handle.set(1, hs[0][1]);
            handle.set(2, hs[1][0]); handle.set(3, hs[1][1]);
            handle.set(4, manual[i].active);
            handles.set(i, handle);
            const auto ks = segments[i].endpoint_curvatures();
            val curvature = val::array();
            curvature.set(0, ks[0]); curvature.set(1, ks[1]);
            curvatures.set(i, curvature);
        }
        result.set("paths", paths);
        result.set("handles", handles);
        result.set("curvatures", curvatures);
        return result;
    }

private:
    struct ManualSegment
    {
        bool active = false;
        std::array<HyperPoint, 2> handles{};
    };

    std::vector<HyperPoint> points;
    std::vector<bool> smooth_points;
    std::vector<ManualSegment> manual;

    static HyperPoint unit_point(const HyperPoint& point, const HyperPoint& start,
                                 const HyperPoint& end)
    {
        const double dx = end[0] - start[0];
        const double dy = end[1] - start[1];
        const double rx = point[0] - start[0];
        const double ry = point[1] - start[1];
        const double denominator = std::max(1e-12, dx * dx + dy * dy);
        return { (rx * dx + ry * dy) / denominator,
                 (-rx * dy + ry * dx) / denominator };
    }

    std::vector<HyperSegment> solved_segments() const
    {
        std::vector<HyperSegment> result;
        if (points.size() < 2)
            return result;
        std::vector<unsigned> breaks{ 0 };
        for (unsigned i = 1; i + 1 < points.size(); ++i)
            if (!smooth_points[i])
                breaks.push_back(i);
        breaks.push_back(points.size() - 1);
        for (unsigned run = 0; run + 1 < breaks.size(); ++run)
        {
            const unsigned first = breaks[run];
            const unsigned last = breaks[run + 1];
            std::vector<HyperPoint> run_points(points.begin() + first, points.begin() + last + 1);
            const auto run_segments = AutoHyperSpline(run_points).segments();
            result.insert(result.end(), run_segments.begin(), run_segments.end());
        }
        for (unsigned i = 0; i < result.size() && i < manual.size(); ++i)
        {
            if (!manual[i].active)
                continue;
            const auto p1 = unit_point(manual[i].handles[0], result[i].start, result[i].end);
            const auto p2 = unit_point(manual[i].handles[1], result[i].start, result[i].end);
            result[i].curve = HyperBezier::from_control_points(p1, p2);
            const auto first = HyperBezier::parameters_for_arm(p1);
            const auto second = HyperBezier::parameters_for_arm({ 1.0 - p2[0], -p2[1] });
            result[i].theta0 = first[0];
            result[i].theta1 = -second[0];
        }
        return result;
    }
};
} // namespace

EMSCRIPTEN_BINDINGS(adjacent_web)
{
    emscripten::class_<WebConstraintSketch>("ConstraintSketch")
        .constructor<>()
        .function("addPoint", &WebConstraintSketch::add_point)
        .function("addLine", &WebConstraintSketch::add_line)
        .function("addCircle", &WebConstraintSketch::add_circle)
        .function("solve", &WebConstraintSketch::solve)
        .function("dragPoint", &WebConstraintSketch::drag_point)
        .function("geometry", &WebConstraintSketch::geometry)
        .function("fixed", &WebConstraintSketch::fixed)
        .function("coincident", &WebConstraintSketch::coincident)
        .function("horizontal", &WebConstraintSketch::horizontal)
        .function("vertical", &WebConstraintSketch::vertical)
        .function("distance", &WebConstraintSketch::distance)
        .function("length", &WebConstraintSketch::length)
        .function("parallel", &WebConstraintSketch::parallel)
        .function("perpendicular", &WebConstraintSketch::perpendicular)
        .function("equalLength", &WebConstraintSketch::equal_length)
        .function("midpoint", &WebConstraintSketch::midpoint)
        .function("pointOnLine", &WebConstraintSketch::point_on_line)
        .function("pointLineDistance", &WebConstraintSketch::point_line_distance)
        .function("diameter", &WebConstraintSketch::diameter)
        .function("equalRadius", &WebConstraintSketch::equal_radius)
        .function("concentric", &WebConstraintSketch::concentric)
        .function("tangent", &WebConstraintSketch::tangent)
        .function("angle", &WebConstraintSketch::angle)
        .function("removeLastConstraint", &WebConstraintSketch::remove_last_constraint);

    emscripten::class_<WebHyperSpline>("HyperSpline")
        .constructor<>()
        .function("setPoints", &WebHyperSpline::set_points)
        .function("setManualHandle", &WebHyperSpline::set_manual_handle)
        .function("resetHandle", &WebHyperSpline::reset_handle)
        .function("solve", &WebHyperSpline::solve);
}
