// src/core/include/photonics/common.hpp
#pragma once

#include <complex>
#include <cstddef>

namespace photonics {

#ifdef PHOTONICS_HLS_BUILD
    #include <ap_fixed.h>
    using real_t    = ap_fixed<32, 8>;
    using complex_t = std::complex<real_t>;
#else
    using real_t    = double;
    using complex_t = std::complex<double>;
#endif

inline constexpr std::size_t MAX_LAYERS = 32;

}  // namespace photonics
