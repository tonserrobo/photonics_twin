#pragma once
#include <string>
#include "photonics/common.hpp"

namespace photonics {

struct SellmeierCoeffs {
    real_t B1, B2, B3;
    real_t C1, C2, C3;   // squared coefficients in um^2
};

struct ThermalCoeffs {
    real_t dn_dT_per_K = 0.0;
    real_t cte_per_K = 0.0;
};

class Material {
public:
    Material(std::string name, SellmeierCoeffs c);
    Material(std::string name, SellmeierCoeffs c, ThermalCoeffs t);

    // Refractive index at given wavelength (nm). Internally converts to um
    // because Sellmeier coefficients are conventionally expressed for lambda in um.
    real_t n(real_t wavelength_nm) const;

    // Linear thermo-optic model around T_REF_C. Thickness changes are handled
    // by BraggGrating using cte(); this only shifts the refractive index.
    real_t n(real_t wavelength_nm, real_t temperature_c) const;

    real_t dn_dT() const { return t_.dn_dT_per_K; }
    real_t cte() const { return t_.cte_per_K; }

    const std::string& name() const { return name_; }

private:
    std::string name_;
    SellmeierCoeffs c_;
    ThermalCoeffs t_{};
};

}  // namespace photonics
