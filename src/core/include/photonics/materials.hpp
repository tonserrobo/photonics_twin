#pragma once
#include <string>
#include "photonics/common.hpp"

namespace photonics {

struct SellmeierCoeffs {
    real_t B1, B2, B3;
    real_t C1, C2, C3;   // squared coefficients in μm²
};

class Material {
public:
    Material(std::string name, SellmeierCoeffs c);

    // Refractive index at given wavelength (nm). Internally converts to μm
    // because Sellmeier coefficients are conventionally expressed for λ in μm.
    real_t n(real_t wavelength_nm) const;

    const std::string& name() const { return name_; }

private:
    std::string name_;
    SellmeierCoeffs c_;
};

}  // namespace photonics
