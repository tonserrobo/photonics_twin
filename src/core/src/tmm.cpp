// src/core/src/tmm.cpp
#include "photonics/tmm.hpp"
#include <cmath>

namespace photonics {

void LayerStack::add_layer(real_t thickness_nm, const Material& m) {
    layers_.push_back(Layer{thickness_nm, &m});
}

namespace {
constexpr real_t PI = real_t{3.14159265358979323846};

// 2x2 complex matrix.
struct Mat2 {
    complex_t a, b, c, d;
};

inline Mat2 mat_mul(const Mat2& X, const Mat2& Y) {
    return Mat2{
        X.a*Y.a + X.b*Y.c, X.a*Y.b + X.b*Y.d,
        X.c*Y.a + X.d*Y.c, X.c*Y.b + X.d*Y.d
    };
}
}  // namespace

void tmm_sweep(const LayerStack& stack,
               const real_t* wavelengths_nm, std::size_t n_wl,
               complex_t* r_out, complex_t* t_out) {
    constexpr complex_t I{0.0, 1.0};
    const complex_t n_in{1.0, 0.0};   // vacuum incident medium
    const complex_t n_sub{1.0, 0.0};  // vacuum substrate (no extra interface)

    for (std::size_t k = 0; k < n_wl; ++k) {
        const real_t lambda = wavelengths_nm[k];

        // Identity matrix.
        Mat2 M{ {1.0,0.0}, {0.0,0.0}, {0.0,0.0}, {1.0,0.0} };

        for (std::size_t li = 0; li < stack.size(); ++li) {
            const auto& layer = stack.at(li);
            const complex_t n{static_cast<double>(layer.material->n(lambda)), 0.0};
            const real_t delta = real_t{2.0} * PI * static_cast<double>(n.real())
                                 * layer.thickness_nm / lambda;
            const complex_t cos_d{std::cos(static_cast<double>(delta)), 0.0};
            const complex_t sin_d{std::sin(static_cast<double>(delta)), 0.0};
            // Characteristic matrix for normal incidence.
            Mat2 L{
                cos_d,           I * sin_d / n,
                I * n * sin_d,   cos_d
            };
            M = mat_mul(M, L);
        }

        // r = (m11*n_in + m12*n_in*n_sub - m21 - m22*n_sub)
        //   / (m11*n_in + m12*n_in*n_sub + m21 + m22*n_sub)
        const complex_t num = M.a*n_in + M.b*n_in*n_sub - M.c - M.d*n_sub;
        const complex_t den = M.a*n_in + M.b*n_in*n_sub + M.c + M.d*n_sub;
        r_out[k] = num / den;
        // t = 2*n_in / den
        t_out[k] = (complex_t{2.0,0.0} * n_in) / den;
    }
}

}  // namespace photonics
