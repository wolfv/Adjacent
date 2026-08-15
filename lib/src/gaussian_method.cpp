#include "gaussian_method.hpp"

#include <xtensor/xtensor.hpp>
#include <xtensor/xio.hpp>

// copy A so it doesn't get overwritten
// note: could use xt::linalg::rank
int GaussianMethod::rank(xt::xtensor<double, 2> A)
{
    const std::size_t rows = A.shape(0);
    const std::size_t cols = A.shape(1);
    std::size_t pivot_row = 0;

    for (std::size_t col = 0; col < cols && pivot_row < rows; ++col)
    {
        std::size_t pivot = pivot_row;
        for (std::size_t row = pivot_row + 1; row < rows; ++row)
            if (std::abs(A(row, col)) > std::abs(A(pivot, col)))
                pivot = row;
        if (std::abs(A(pivot, col)) <= rank_epsilon)
            continue;

        if (pivot != pivot_row)
            for (std::size_t c = col; c < cols; ++c)
                std::swap(A(pivot_row, c), A(pivot, c));

        for (std::size_t row = pivot_row + 1; row < rows; ++row)
        {
            const double factor = A(row, col) / A(pivot_row, col);
            for (std::size_t c = col; c < cols; ++c)
                A(row, c) -= factor * A(pivot_row, c);
        }
        ++pivot_row;
    }
    return static_cast<int>(pivot_row);
}

// copy A & B so they don't get overwritten
void GaussianMethod::solve(xt::xtensor<double, 2> A, xt::xtensor<double, 1> B,
                           xt::xtensor<double, 1>& X)
{
    const std::size_t rows = A.shape(0);
    const std::size_t cols = A.shape(1);
    X.resize({ cols });
    std::fill(X.begin(), X.end(), 0.0);

    const std::size_t pivots = std::min(rows, cols);
    for (std::size_t r = 0; r < pivots; ++r)
    {
        std::size_t pivot = r;
        for (std::size_t rr = r + 1; rr < rows; ++rr)
            if (std::abs(A(rr, r)) > std::abs(A(pivot, r)))
                pivot = rr;

        if (std::abs(A(pivot, r)) < epsilon)
            continue;
        if (pivot != r)
        {
            for (std::size_t c = 0; c < cols; ++c)
                std::swap(A(r, c), A(pivot, c));
            std::swap(B(r), B(pivot));
        }

        for (std::size_t rr = r + 1; rr < rows; ++rr)
        {
            const double factor = A(rr, r) / A(r, r);
            if (factor == 0.0)
                continue;
            A(rr, r) = 0.0;
            for (std::size_t c = r + 1; c < cols; ++c)
                A(rr, c) -= factor * A(r, c);
            B(rr) -= factor * B(r);
        }
    }

    for (std::size_t ri = pivots; ri-- > 0;)
    {
        if (std::abs(A(ri, ri)) < epsilon)
            continue;
        double value = B(ri);
        for (std::size_t c = ri + 1; c < cols; ++c)
            value -= A(ri, c) * X(c);
        X(ri) = value / A(ri, ri);
    }
}
