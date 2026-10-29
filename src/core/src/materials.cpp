#include "photonics/materials.hpp"
#include <cmath>
#include <utility>

namespace photonics {

Material::Material(std::string name, SellmeierCoeffs c)
    : Material(std::move(name), c, ThermalCoeffs{}) {}

Material::Material(std::string name, SellmeierCoeffs c, ThermalCoeffs t)
    : name_(std::move(name)), c_(c), t_(t) {}

real_t Material::n(real_t wavelength_nm) const {
    return n(wavelength_nm, T_REF_C);
}

real_t Material::n(real_t wavelength_nm, real_t temperature_c) const {
    const real_t lambda_um = wavelength_nm / real_t{1000.0};
    const real_t l2 = lambda_um * lambda_um;
    const real_t s =
        c_.B1 * l2 / (l2 - c_.C1) +
        c_.B2 * l2 / (l2 - c_.C2) +
        c_.B3 * l2 / (l2 - c_.C3);
    return std::sqrt(real_t{1.0} + s) + t_.dn_dT_per_K * (temperature_c - T_REF_C);
}

}  // namespace photonics
