#include <gtest/gtest.h>
#include "photonics/materials.hpp"

TEST(Materials, SellmeierSiO2_at_633nm) {
    photonics::SellmeierCoeffs sio2{
        0.6961663, 0.4079426, 0.8974794,
        0.00467914826, 0.01351206307, 97.9340025
    };
    photonics::Material m("SiO2", sio2);
    EXPECT_NEAR(static_cast<double>(m.n(633.0)), 1.4570, 1e-4);
}

TEST(Materials, SellmeierSi_at_1550nm) {
    photonics::SellmeierCoeffs si{
        10.6684293, 0.003043475, 1.54133408,
        0.090912191, 1.287460152, 1218816.0
    };
    photonics::Material m("Si", si);
    EXPECT_NEAR(static_cast<double>(m.n(1550.0)), 3.4778, 1e-3);
}

TEST(Materials, ThermalCoeffsShiftIndexFromReference) {
    photonics::SellmeierCoeffs si{
        10.6684293, 0.003043475, 1.54133408,
        0.090912191, 1.287460152, 1218816.0
    };
    photonics::ThermalCoeffs thermal{1.86e-4, 2.6e-6};
    photonics::Material m("Si", si, thermal);

    const double n20 = static_cast<double>(m.n(1550.0, 20.0));
    const double n_ref = static_cast<double>(m.n(1550.0));
    const double n60 = static_cast<double>(m.n(1550.0, 60.0));
    EXPECT_NEAR(n20, n_ref, 1e-12);
    EXPECT_GT(n60, n20);
    EXPECT_NEAR(static_cast<double>(m.dn_dT()), 1.86e-4, 1e-12);
    EXPECT_NEAR(static_cast<double>(m.cte()), 2.6e-6, 1e-12);
}
