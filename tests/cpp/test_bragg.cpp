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
photonics::Material make_si_thermal() {
    return photonics::Material("Si", {10.6684293, 0.003043475, 1.54133408,
                                      0.090912191, 1.287460152, 1218816.0},
                               {1.86e-4, 2.6e-6});
}
photonics::Material make_sio2_thermal() {
    return photonics::Material("SiO2", {0.6961663, 0.4079426, 0.8974794,
                                        0.00467914826, 0.01351206307, 97.9340025},
                               {1.0e-5, 0.55e-6});
}

double low_stop_band_edge(const std::vector<double>& wl,
                          const std::vector<double>& R) {
    for (std::size_t i = 1; i < R.size(); ++i) {
        if (R[i - 1] < 0.5 && R[i] >= 0.5) {
            return wl[i - 1] + (0.5 - R[i - 1]) * (wl[i] - wl[i - 1]) /
                               (R[i] - R[i - 1]);
        }
    }
    return -1.0;
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

TEST(BraggGrating, TemperatureRedshiftsStopBand) {
    photonics::BraggGrating g(make_si_thermal(), make_sio2_thermal(), 1550.0, 15);

    constexpr std::size_t N = 1501;
    std::vector<double> wl(N), R20(N), R80(N);
    const double start = 1150.0, stop = 1300.0;
    for (std::size_t i = 0; i < N; ++i) {
        wl[i] = start + (stop - start) * static_cast<double>(i) / (N - 1);
    }

    g.reflectance(wl.data(), N, R20.data());
    const double edge20 = low_stop_band_edge(wl, R20);

    g.set_temperature_c(80.0);
    g.reflectance(wl.data(), N, R80.data());
    const double edge80 = low_stop_band_edge(wl, R80);

    ASSERT_GT(edge20, 0.0);
    ASSERT_GT(edge80, 0.0);
    EXPECT_GT(edge80, edge20 + 1.0);   // red shift of a few nm over 60 K
    EXPECT_LT(edge80, edge20 + 10.0);
}

TEST(BraggGrating, TemperatureExpandsLayers) {
    photonics::BraggGrating g(make_si_thermal(), make_sio2_thermal(), 1550.0, 2);
    const double t20 = static_cast<double>(g.stack().at(0).thickness_nm);
    g.set_temperature_c(80.0);
    const double t80 = static_cast<double>(g.stack().at(0).thickness_nm);
    EXPECT_GT(t80, t20);
    EXPECT_NEAR((t80 - t20) / t20, 2.6e-6 * 60.0, 1e-9);
}

TEST(BraggGrating, StrainExpandsLayers) {
    photonics::BraggGrating g(make_si_thermal(), make_sio2_thermal(), 1550.0, 2);
    const double t0 = static_cast<double>(g.stack().at(0).thickness_nm);
    g.set_strain_microstrain(1000.0);
    const double t1 = static_cast<double>(g.stack().at(0).thickness_nm);
    EXPECT_GT(t1, t0);
    EXPECT_NEAR((t1 - t0) / t0, 1.0e-3, 1e-9);
}

TEST(BraggGrating, StrainRedshiftsStopBand) {
    photonics::BraggGrating g(make_si_thermal(), make_sio2_thermal(), 1550.0, 15);

    constexpr std::size_t N = 1501;
    std::vector<double> wl(N), R0(N), R1000(N);
    const double start = 1150.0, stop = 1300.0;
    for (std::size_t i = 0; i < N; ++i) {
        wl[i] = start + (stop - start) * static_cast<double>(i) / (N - 1);
    }

    g.reflectance(wl.data(), N, R0.data());
    const double edge0 = low_stop_band_edge(wl, R0);

    g.set_strain_microstrain(1000.0);
    g.reflectance(wl.data(), N, R1000.data());
    const double edge1000 = low_stop_band_edge(wl, R1000);

    ASSERT_GT(edge0, 0.0);
    ASSERT_GT(edge1000, 0.0);
    EXPECT_GT(edge1000, edge0 + 0.5);
    EXPECT_LT(edge1000, edge0 + 3.0);
}