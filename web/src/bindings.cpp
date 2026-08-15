#include <emscripten/bind.h>

#include <hyperbezier.hpp>

#include <algorithm>
#include <vector>

using adjacent::AutoHyperSpline;
using adjacent::HyperBezier;
using adjacent::HyperPoint;
using adjacent::HyperSegment;
using emscripten::val;

namespace
{
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
    emscripten::class_<WebHyperSpline>("HyperSpline")
        .constructor<>()
        .function("setPoints", &WebHyperSpline::set_points)
        .function("setManualHandle", &WebHyperSpline::set_manual_handle)
        .function("resetHandle", &WebHyperSpline::reset_handle)
        .function("solve", &WebHyperSpline::solve);
}
