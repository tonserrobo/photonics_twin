#include <gtest/gtest.h>
#include <algorithm>
#include <cmath>
#include <vector>
#include "photonics/bragg.hpp"

namespace {
photonics::Material make_si() {
    return photonics::Material("Si", {10.6684293, 0.003043475, 1.54133408,
                                       0.090912191, 1.287460152, 1218816.0});
}
photonics::Material make_sio2() {
    return photonics::Material("SiO2", {0.6961663, 0.4079426, 0.8974794,
                                         0.00467914826, 0.01351206307, 97.9340025});
}
}

TEST(BraggGrating, StackHasCorrectLayerCount) {
    photonics::BraggGrating g(make_si(), make_sio2(), 1550.0, 15);
    EXPECT_EQ(g.stack().size(), 30u);
}

TEST(BraggGrating, QuarterWaveThicknessesAtCentre) {
    auto si = make_si();
    auto sio2 = make_sio2();
    photonics::BraggGrating g(si, sio2, 1550.0, 2);
    const double n_si  = static_cast<double>(si.n(1550.0));
    const double n_sio = static_cast<double>(sio2.n(1550.0));

    EXPECT_NEAR(static_cast<double>(g.stack().at(0).thickness_nm),
                1550.0 / (4.0 * n_si), 1e-6);
    EXPECT_NEAR(static_cast<double>(g.stack().at(1).thickness_nm),
                1550.0 / (4.0 * n_sio), 1e-6);
    EXPECT_EQ(g.stack().at(0).material->name(), "Si");
    EXPECT_EQ(g.stack().at(1).material->name(), "SiO2");
}

TEST(BraggGrating, ReflectanceHighAtCentreWavelength) {
    // For a 15-period Si/SiO2 quarter-wave grating designed at 1550 nm,
    // the entire 1400-1700 nm range falls inside the stop band, where
    // reflectance is uniformly >0.99. We verify two physically meaningful
    // claims: the centre-wavelength reflectance is essentially 1, and
    // every point in the sweep is high-reflectance.
    photonics::BraggGrating g(make_si(), make_sio2(), 1550.0, 15);

    constexpr std::size_t N = 501;
    std::vector<double> wl(N), R(N);
    const double start = 1400.0, stop = 1700.0;
    for (std::size_t i = 0; i < N; ++i) {
        wl[i] = start + (stop - start) * static_cast<double>(i) / (N - 1);
    }
    g.reflectance(wl.data(), N, R.data());

    // Index of the design wavelength in the sweep (1550 lands exactly on a sample).
    const std::size_t idx_1550 = static_cast<std::size_t>(
        std::round((1550.0 - start) / (stop - start) * (N - 1)));
    ASSERT_LT(std::abs(wl[idx_1550] - 1550.0), 1e-6);  // sanity: 1550 is on grid

    EXPECT_NEAR(R[idx_1550], 1.0, 1e-3);            // peak ~1 at design wavelength
    const double R_min = *std::min_element(R.begin(), R.end());
    EXPECT_GT(R_min, 0.99);                          // entire sweep inside stop band
}
