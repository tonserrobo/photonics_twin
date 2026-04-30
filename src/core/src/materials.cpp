#include "photonics/materials.hpp"
#include <cmath>
#include <utility>

namespace photonics {

Material::Material(std::string name, SellmeierCoeffs c)
    : name_(std::move(name)), c_(c) {}

real_t Material::n(real_t wavelength_nm) const {
    const real_t lambda_um = wavelength_nm / real_t{1000.0};
    const real_t l2 = lambda_um * lambda_um;
    const real_t s =
        c_.B1 * l2 / (l2 - c_.C1) +
        c_.B2 * l2 / (l2 - c_.C2) +
        c_.B3 * l2 / (l2 - c_.C3);
    return std::sqrt(real_t{1.0} + s);
}

}  // namespace photonics
