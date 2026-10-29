// C-simulation testbench for the fixed-stack TMM spike.
// Compares the fixed-point kernel against a double-precision reference.
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstdlib>
#include <vector>

extern "C" void tmm_sweep_fixed(const float* wavelengths_nm, int n_wl,
                                 float* reflectance);

namespace {

constexpr double N_H = 3.477724;
constexpr double N_L = 1.444024;
constexpr double T_H = 1550.0 / (4.0 * N_H);
constexpr double T_L = 1550.0 / (4.0 * N_L);
constexpr double TWO_PI = 6.28318530717958647692;

double reference_reflectance(double lambda) {
    using cd = std::complex<double>;
    cd m00(1.0, 0.0), m01(0.0, 0.0), m10(0.0, 0.0), m11(1.0, 0.0);
    for (int layer = 0; layer < 4; ++layer) {
        const bool high = (layer % 2 == 0);
        const double n = high ? N_H : N_L;
        const double d = high ? T_H : T_L;
        const double delta = TWO_PI * n * d / lambda;
        const double c = std::cos(delta);
        const double s = std::sin(delta);
        const cd l00(c, 0.0);
        const cd l01(0.0, s / n);
        const cd l10(0.0, n * s);
        const cd l11(c, 0.0);
        const cd n00 = m00 * l00 + m01 * l10;
        const cd n01 = m00 * l01 + m01 * l11;
        const cd n10 = m10 * l00 + m11 * l10;
        const cd n11 = m10 * l01 + m11 * l11;
        m00 = n00; m01 = n01; m10 = n10; m11 = n11;
    }
    const cd num = (m00 + m01) - (m10 + m11);
    const cd den = (m00 + m01) + (m10 + m11);
    return std::norm(num / den);
}

}  // namespace

int main() {
    constexpr int N = 501;
    std::vector<float> wl(N), R(N);
    for (int i = 0; i < N; ++i) {
        wl[i] = 1400.0f + 300.0f * float(i) / float(N - 1);
    }

    tmm_sweep_fixed(wl.data(), N, R.data());

    double max_error = 0.0;
    double min_r = 1.0, max_r = 0.0;
    for (int i = 0; i < N; ++i) {
        const double expected = reference_reflectance(double(wl[i]));
        const double error = std::abs(double(R[i]) - expected);
        if (error > max_error) max_error = error;
        if (R[i] < min_r) min_r = R[i];
        if (R[i] > max_r) max_r = R[i];
    }

    std::printf("points=%d max_abs_error=%.3e min_R=%.6f max_R=%.6f\n",
                N, max_error, min_r, max_r);

    if (max_error > 1.0e-3) {
        std::printf("FAIL: fixed-point error exceeds 1e-3\n");
        return EXIT_FAILURE;
    }
    std::printf("PASS: fixed-point kernel within 1e-3 of double reference\n");
    return EXIT_SUCCESS;
}
