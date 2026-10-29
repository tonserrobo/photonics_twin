// Sequential-layer variant: same fixed stack, no full layer unroll.
//
// Scope: 2 Si/SiO2 periods, fixed indices and thicknesses at 1550 nm, normal
// incidence, vacuum ambient/substrate. The phase trig is evaluated in float;
// the matrix chain and reflectance are ap_fixed. This is a numerical and
// synthesis spike, not the production kernel.
#include "ap_fixed.h"
#include "hls_math.h"
#include <cstddef>

namespace hls_tmm {

using real_t = ap_fixed<32, 8, AP_RND, AP_SAT>;
using wide_t = ap_fixed<48, 16, AP_RND, AP_SAT>;

struct complex_t {
    real_t re;
    real_t im;
};

struct mat2 {
    complex_t a, b, c, d;
};

inline complex_t cadd(const complex_t& x, const complex_t& y) {
    return {real_t(x.re + y.re), real_t(x.im + y.im)};
}

inline complex_t csub(const complex_t& x, const complex_t& y) {
    return {real_t(x.re - y.re), real_t(x.im - y.im)};
}

inline complex_t cmul(const complex_t& x, const complex_t& y) {
    wide_t re = wide_t(x.re) * y.re - wide_t(x.im) * y.im;
    wide_t im = wide_t(x.re) * y.im + wide_t(x.im) * y.re;
    return {real_t(re), real_t(im)};
}

inline complex_t cdiv(const complex_t& x, const complex_t& y) {
    wide_t den = wide_t(y.re) * y.re + wide_t(y.im) * y.im;
    wide_t re = wide_t(x.re) * y.re + wide_t(x.im) * y.im;
    wide_t im = wide_t(x.im) * y.re - wide_t(x.re) * y.im;
    return {real_t(re / den), real_t(im / den)};
}

inline mat2 mmul(const mat2& x, const mat2& y) {
    return {
        cadd(cmul(x.a, y.a), cmul(x.b, y.c)),
        cadd(cmul(x.a, y.b), cmul(x.b, y.d)),
        cadd(cmul(x.c, y.a), cmul(x.d, y.c)),
        cadd(cmul(x.c, y.b), cmul(x.d, y.d)),
    };
}

}  // namespace hls_tmm

extern "C" void tmm_sweep_fixed(const float* wavelengths_nm, int n_wl,
                                 float* reflectance) {
#pragma HLS INTERFACE m_axi port=wavelengths_nm offset=slave bundle=gmem0
#pragma HLS INTERFACE m_axi port=reflectance offset=slave bundle=gmem1
#pragma HLS INTERFACE s_axilite port=wavelengths_nm bundle=control
#pragma HLS INTERFACE s_axilite port=reflectance bundle=control
#pragma HLS INTERFACE s_axilite port=n_wl bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    using namespace hls_tmm;

    const float n_h = 3.477724f;
    const float n_l = 1.444024f;
    const float t_h = 1550.0f / (4.0f * n_h);
    const float t_l = 1550.0f / (4.0f * n_l);
    const float two_pi = 6.283185307179586f;

    for (int k = 0; k < n_wl; ++k) {
#pragma HLS PIPELINE II=4
        const float lambda = wavelengths_nm[k];
        mat2 m = {{real_t(1.0), real_t(0.0)}, {real_t(0.0), real_t(0.0)},
                  {real_t(0.0), real_t(0.0)}, {real_t(1.0), real_t(0.0)}};

        for (int layer = 0; layer < 4; ++layer) {
#pragma HLS UNROLL off
            const bool high = (layer % 2 == 0);
            const float n = high ? n_h : n_l;
            const float d = high ? t_h : t_l;
            const float delta = two_pi * n * d / lambda;
            const real_t cos_d = real_t(hls::cos(delta));
            const real_t sin_d = real_t(hls::sin(delta));
            const real_t n_r = real_t(n);
            const real_t sin_over_n = real_t(wide_t(sin_d) / wide_t(n_r));
            const real_t n_sin = real_t(wide_t(n_r) * wide_t(sin_d));
            const mat2 l = {
                {cos_d, real_t(0.0)},
                {real_t(0.0), sin_over_n},
                {real_t(0.0), n_sin},
                {cos_d, real_t(0.0)},
            };
            m = mmul(m, l);
        }

        const complex_t num = csub(cadd(m.a, m.b), cadd(m.c, m.d));
        const complex_t den = cadd(cadd(m.a, m.b), cadd(m.c, m.d));
        const complex_t r = cdiv(num, den);
        const wide_t power = wide_t(r.re) * r.re + wide_t(r.im) * r.im;
        reflectance[k] = float(power);
    }
}
