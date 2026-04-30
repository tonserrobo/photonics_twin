#include <gtest/gtest.h>
#include <complex>
#include "photonics/tmm.hpp"
#include "photonics/materials.hpp"

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

TEST(LayerStack, AddLayerAndAccess) {
    auto si = make_si();
    auto sio2 = make_sio2();
    photonics::LayerStack stack;
    stack.add_layer(110.7, si);
    stack.add_layer(267.2, sio2);

    EXPECT_EQ(stack.size(), 2u);
    EXPECT_NEAR(static_cast<double>(stack.at(0).thickness_nm), 110.7, 1e-9);
    EXPECT_EQ(stack.at(0).material->name(), "Si");
    EXPECT_EQ(stack.at(1).material->name(), "SiO2");
}

TEST(TMMSweep, EmptyStackGivesZeroReflectance) {
    photonics::LayerStack stack;
    const double wl[3] = {1400.0, 1550.0, 1700.0};
    photonics::complex_t r[3], t[3];
    photonics::tmm_sweep(stack, wl, 3, r, t);

    for (int i = 0; i < 3; ++i) {
        EXPECT_NEAR(std::abs(r[i]), 0.0, 1e-12);
        EXPECT_NEAR(std::abs(t[i]), 1.0, 1e-12);
    }
}

TEST(TMMSweep, SingleQuarterWaveAirSubstrate) {
    // Approximately constant n=2.0 over the test range:
    // From n^2 - 1 = B*λ² / (λ² - C), pick B = 3, C very large so the term
    // approaches B*λ²/-C → small; better: pick B = 3, C = 0 → n² - 1 = 3 → n = 2.
    photonics::SellmeierCoeffs flat{3.0, 0.0, 0.0, 0.0, 1.0, 1.0};
    photonics::Material m("flat", flat);
    // Sanity: n(any λ) ≈ 2.0
    ASSERT_NEAR(static_cast<double>(m.n(1550.0)), 2.0, 1e-9);

    const double n_L = 2.0;
    const double lambda0 = 1550.0;
    const double thickness = lambda0 / (4.0 * n_L);  // 193.75 nm

    photonics::LayerStack stack;
    stack.add_layer(thickness, m);

    const double wl[1] = {lambda0};
    photonics::complex_t r[1], t[1];
    photonics::tmm_sweep(stack, wl, 1, r, t);

    const double R_expected = ((n_L*n_L - 1.0) / (n_L*n_L + 1.0))
                            * ((n_L*n_L - 1.0) / (n_L*n_L + 1.0));
    EXPECT_NEAR(std::norm(r[0]), R_expected, 1e-6);
}
